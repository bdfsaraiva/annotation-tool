"""
Database CRUD operations and business-logic helpers for the LACE platform.

Functions are grouped by domain:
- User / Project / ChatRoom / ChatMessage — standard create/read/update/delete.
- Annotation (disentanglement) — per-annotator and admin-level fetch + import.
- AdjacencyPair — per-annotator and admin-level fetch.
- ChatRoomCompletion / MessageReadStatus — annotator progress tracking.
- IAA analysis — one-to-one accuracy (disentanglement) and LinkF1×TypeAcc
  (adjacency pairs) computed with the Hungarian algorithm.
- Export — full chat-room data dump.
"""
from sqlalchemy.orm import Session, Query
from typing import List, Optional, Tuple
from . import models, schemas
from fastapi import HTTPException
import numpy as np
from scipy.optimize import linear_sum_assignment
from itertools import combinations
from datetime import datetime
import secrets


# ---------------------------------------------------------------------------
# User CRUD
# ---------------------------------------------------------------------------

def get_user(db: Session, user_id: int) -> Optional[models.User]:
    """
    Retrieve a user by primary key.

    Args:
        db: Active database session.
        user_id: The user's integer primary key.

    Returns:
        The matching ``User`` object, or ``None`` if not found.
    """
    return db.query(models.User).filter(models.User.id == user_id).first()


def get_user_by_username(db: Session, username: str) -> Optional[models.User]:
    """
    Retrieve a user by their unique username.

    Args:
        db: Active database session.
        username: The exact username to look up.

    Returns:
        The matching ``User`` object, or ``None`` if not found.
    """
    return db.query(models.User).filter(models.User.username == username).first()


def get_users(db: Session, skip: int = 0, limit: int = 100) -> List[models.User]:
    """
    Return a paginated list of all users.

    Args:
        db: Active database session.
        skip: Number of rows to skip (offset).
        limit: Maximum number of rows to return.

    Returns:
        List of ``User`` objects.
    """
    return db.query(models.User).offset(skip).limit(limit).all()


def create_user(db: Session, user: schemas.UserCreate, hashed_password: str) -> models.User:
    """
    Persist a new user account.

    Args:
        db: Active database session.
        user: Validated creation payload (username, is_admin).
        hashed_password: Pre-hashed password string (caller is responsible for
            hashing before calling this function).

    Returns:
        The newly created ``User`` ORM object.
    """
    db_user = models.User(
        username=user.username,
        hashed_password=hashed_password,
        is_admin=user.is_admin
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def delete_user(db: Session, user: models.User) -> None:
    """
    Delete a user from the database.

    All related records (annotations, assignments, etc.) are removed via
    SQLAlchemy cascade rules.

    Args:
        db: Active database session.
        user: The ``User`` ORM object to delete.
    """
    db.delete(user)
    db.commit()


def update_user(
    db: Session,
    user: models.User,
    updates: schemas.UserUpdate,
    hashed_password: Optional[str] = None
) -> models.User:
    """
    Apply partial updates to an existing user.

    Only non-``None`` fields in ``updates`` are applied to avoid accidentally
    clearing unchanged fields.

    Args:
        db: Active database session.
        user: The ``User`` ORM object to update.
        updates: Partial update payload.
        hashed_password: New bcrypt hash if the password is being changed,
            ``None`` otherwise.

    Returns:
        The refreshed ``User`` object.
    """
    if updates.username is not None:
        user.username = updates.username
    if updates.is_admin is not None:
        user.is_admin = updates.is_admin
    if hashed_password is not None:
        user.hashed_password = hashed_password
    db.commit()
    db.refresh(user)
    return user


# ---------------------------------------------------------------------------
# Project CRUD
# ---------------------------------------------------------------------------

def get_project(db: Session, project_id: int) -> Optional[models.Project]:
    """
    Retrieve a project by primary key.

    Args:
        db: Active database session.
        project_id: The project's integer primary key.

    Returns:
        The matching ``Project`` object, or ``None`` if not found.
    """
    return db.query(models.Project).filter(models.Project.id == project_id).first()


def get_projects(db: Session, skip: int = 0, limit: int = 100) -> List[models.Project]:
    """
    Return a paginated list of all projects.

    Args:
        db: Active database session.
        skip: Number of rows to skip (offset).
        limit: Maximum number of rows to return.

    Returns:
        List of ``Project`` objects.
    """
    return db.query(models.Project).offset(skip).limit(limit).all()


def create_project(db: Session, project: schemas.ProjectCreate) -> models.Project:
    """
    Persist a new annotation project.

    Args:
        db: Active database session.
        project: Validated creation payload.

    Returns:
        The newly created ``Project`` ORM object.
    """
    db_project = models.Project(
        name=project.name,
        description=project.description,
        annotation_type=project.annotation_type,
        relation_types=project.relation_types,
        iaa_alpha=project.iaa_alpha,
    )
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    return db_project


def update_project(
    db: Session,
    project: models.Project,
    updates: schemas.ProjectUpdate
) -> models.Project:
    """
    Apply partial updates to an existing project.

    Args:
        db: Active database session.
        project: The ``Project`` ORM object to update.
        updates: Partial update payload; ``None`` fields are ignored.

    Returns:
        The refreshed ``Project`` object.
    """
    if updates.name is not None:
        project.name = updates.name
    if updates.description is not None:
        project.description = updates.description
    if updates.annotation_type is not None:
        project.annotation_type = updates.annotation_type
    if updates.relation_types is not None:
        project.relation_types = updates.relation_types
    if updates.iaa_alpha is not None:
        project.iaa_alpha = updates.iaa_alpha
    db.commit()
    db.refresh(project)
    return project


def delete_project(db: Session, project: models.Project) -> None:
    """
    Delete a project from the database.

    Args:
        db: Active database session.
        project: The ``Project`` ORM object to delete.
    """
    db.delete(project)
    db.commit()


# ---------------------------------------------------------------------------
# ChatRoom CRUD
# ---------------------------------------------------------------------------

def get_chat_room(db: Session, chat_room_id: int) -> Optional[models.ChatRoom]:
    """
    Retrieve a chat room by primary key.

    Args:
        db: Active database session.
        chat_room_id: The chat room's integer primary key.

    Returns:
        The matching ``ChatRoom`` object, or ``None`` if not found.
    """
    return db.query(models.ChatRoom).filter(models.ChatRoom.id == chat_room_id).first()


def get_chat_rooms_by_project(
    db: Session, project_id: int, skip: int = 0, limit: int = 100
) -> List[models.ChatRoom]:
    """
    Return all chat rooms belonging to a given project.

    Args:
        db: Active database session.
        project_id: Filter rooms by this project.
        skip: Offset for pagination.
        limit: Maximum rows to return.

    Returns:
        List of ``ChatRoom`` objects.
    """
    return (
        db.query(models.ChatRoom)
        .filter(models.ChatRoom.project_id == project_id)
        .offset(skip)
        .limit(limit)
        .all()
    )


def create_chat_room(db: Session, chat_room: schemas.ChatRoomCreate) -> models.ChatRoom:
    """
    Persist a new chat room inside a project.

    Args:
        db: Active database session.
        chat_room: Validated creation payload.

    Returns:
        The newly created ``ChatRoom`` ORM object.
    """
    db_chat_room = models.ChatRoom(
        name=chat_room.name,
        description=chat_room.description,
        project_id=chat_room.project_id
    )
    db.add(db_chat_room)
    db.commit()
    db.refresh(db_chat_room)
    return db_chat_room


def update_chat_room(
    db: Session,
    chat_room: models.ChatRoom,
    updates: schemas.ChatRoomUpdate
) -> models.ChatRoom:
    """
    Apply partial updates to an existing chat room.

    Args:
        db: Active database session.
        chat_room: The ``ChatRoom`` ORM object to update.
        updates: Partial update payload.

    Returns:
        The refreshed ``ChatRoom`` object.
    """
    if updates.name is not None:
        chat_room.name = updates.name
    if updates.description is not None:
        chat_room.description = updates.description
    db.commit()
    db.refresh(chat_room)
    return chat_room


def delete_chat_room(db: Session, chat_room: models.ChatRoom) -> None:
    """
    Delete a chat room from the database.

    Args:
        db: Active database session.
        chat_room: The ``ChatRoom`` ORM object to delete.
    """
    db.delete(chat_room)
    db.commit()


def get_annotations_for_chat_room(
    db: Session, chat_room_id: int
) -> List[Tuple[models.Annotation, str]]:
    """
    Fetch all annotations for a given chat room, paired with annotator username.

    Args:
        db: Active database session.
        chat_room_id: ID of the target chat room.

    Returns:
        A list of ``(Annotation, username)`` tuples.
    """
    return (
        db.query(models.Annotation, models.User.username)
        .join(models.ChatMessage, models.Annotation.message_id == models.ChatMessage.id)
        .join(models.User, models.Annotation.annotator_id == models.User.id)
        .filter(models.ChatMessage.chat_room_id == chat_room_id)
        .all()
    )


# ---------------------------------------------------------------------------
# Annotation isolation helpers (Phase 1)
# ---------------------------------------------------------------------------

def get_annotations_for_chat_room_by_annotator(
    db: Session, chat_room_id: int, annotator_id: int
) -> List[Tuple[models.Annotation, str]]:
    """
    Fetch annotations for a chat room filtered to a specific annotator.

    Ensures annotators can only access their own work (Pillar 1 of the
    annotation isolation policy).

    Args:
        db: Active database session.
        chat_room_id: ID of the target chat room.
        annotator_id: ID of the annotator whose annotations should be returned.

    Returns:
        A list of ``(Annotation, username)`` tuples for the given annotator.
    """
    return (
        db.query(models.Annotation, models.User.username)
        .join(models.ChatMessage, models.Annotation.message_id == models.ChatMessage.id)
        .join(models.User, models.Annotation.annotator_id == models.User.id)
        .filter(
            models.ChatMessage.chat_room_id == chat_room_id,
            models.Annotation.annotator_id == annotator_id
        )
        .all()
    )


def get_all_annotations_for_chat_room_admin(
    db: Session, chat_room_id: int
) -> List[Tuple[models.Annotation, str]]:
    """
    Fetch ALL annotations for a given chat room (admin-only function).

    Allows administrators to see annotations from all users (Pillar 1).

    Args:
        db: Active database session.
        chat_room_id: ID of the target chat room.

    Returns:
        A list of ``(Annotation, username)`` tuples across all annotators.
    """
    return (
        db.query(models.Annotation, models.User.username)
        .join(models.ChatMessage, models.Annotation.message_id == models.ChatMessage.id)
        .join(models.User, models.Annotation.annotator_id == models.User.id)
        .filter(models.ChatMessage.chat_room_id == chat_room_id)
        .all()
    )


# ---------------------------------------------------------------------------
# ChatMessage CRUD
# ---------------------------------------------------------------------------

def get_chat_message(db: Session, message_id: int) -> Optional[models.ChatMessage]:
    """
    Retrieve a chat message by primary key.

    Args:
        db: Active database session.
        message_id: The message's integer primary key.

    Returns:
        The matching ``ChatMessage`` object, or ``None`` if not found.
    """
    return db.query(models.ChatMessage).filter(models.ChatMessage.id == message_id).first()


def get_chat_messages_by_room(
    db: Session, chat_room_id: int, skip: int = 0, limit: int = 100
) -> List[models.ChatMessage]:
    """
    Return messages from a chat room, ordered by database insertion order.

    Args:
        db: Active database session.
        chat_room_id: Filter messages by this room.
        skip: Offset for pagination.
        limit: Maximum rows to return.

    Returns:
        List of ``ChatMessage`` objects.
    """
    return (
        db.query(models.ChatMessage)
        .filter(models.ChatMessage.chat_room_id == chat_room_id)
        .order_by(models.ChatMessage.id)
        .offset(skip)
        .limit(limit)
        .all()
    )


def create_chat_message(
    db: Session, message: schemas.ChatMessageCreate, chat_room_id: int
) -> models.ChatMessage:
    """
    Insert a single chat message into the database within an open transaction.

    Uses ``db.flush()`` so the generated primary key is available immediately
    without committing the surrounding transaction (allows bulk inserts in one
    transaction).

    Args:
        db: Active database session.
        message: Validated message creation payload.
        chat_room_id: The chat room this message belongs to.

    Returns:
        The newly created ``ChatMessage`` ORM object (with ``id`` populated).
    """
    db_message = models.ChatMessage(
        turn_id=message.turn_id,
        user_id=message.user_id,
        turn_text=message.turn_text,
        reply_to_turn=message.reply_to_turn,
        chat_room_id=chat_room_id
    )
    db.add(db_message)
    db.flush()
    db.refresh(db_message)
    return db_message


def get_chat_message_by_turn_id(
    db: Session, chat_room_id: int, turn_id: str
) -> Optional[models.ChatMessage]:
    """
    Get a chat message by its ``turn_id`` within a specific chat room.

    Used during CSV import and annotation import to resolve turn identifiers
    to database primary keys.

    Args:
        db: Active database session.
        chat_room_id: Scope the lookup to this chat room.
        turn_id: The original turn identifier from the source CSV.

    Returns:
        The matching ``ChatMessage`` object, or ``None`` if not found.
    """
    return db.query(models.ChatMessage).filter(
        models.ChatMessage.chat_room_id == chat_room_id,
        models.ChatMessage.turn_id == turn_id
    ).first()


# ---------------------------------------------------------------------------
# Annotation CRUD (disentanglement)
# ---------------------------------------------------------------------------

def get_annotation(db: Session, annotation_id: int) -> Optional[models.Annotation]:
    """
    Retrieve a disentanglement annotation by primary key.

    Args:
        db: Active database session.
        annotation_id: The annotation's integer primary key.

    Returns:
        The matching ``Annotation`` object, or ``None`` if not found.
    """
    return db.query(models.Annotation).filter(models.Annotation.id == annotation_id).first()


def get_annotations_by_message(db: Session, message_id: int) -> List[models.Annotation]:
    """
    Return all annotations for a single message (all annotators).

    Args:
        db: Active database session.
        message_id: The message's integer primary key.

    Returns:
        List of ``Annotation`` objects.
    """
    return db.query(models.Annotation).filter(models.Annotation.message_id == message_id).all()


def get_annotations_by_annotator(db: Session, annotator_id: int) -> List[models.Annotation]:
    """
    Return all annotations made by a specific annotator across all projects.

    Args:
        db: Active database session.
        annotator_id: The annotator's user ID.

    Returns:
        List of ``Annotation`` objects.
    """
    return db.query(models.Annotation).filter(models.Annotation.annotator_id == annotator_id).all()


def create_annotation(
    db: Session,
    annotation: schemas.AnnotationCreate,
    annotator_id: Optional[int] = None,
    project_id: Optional[int] = None
) -> models.Annotation:
    """
    Persist a new disentanglement annotation.

    ``annotator_id`` and ``project_id`` can be supplied either as explicit
    parameters or embedded in the ``annotation`` schema object.  The explicit
    parameters take precedence when both are provided.

    Args:
        db: Active database session.
        annotation: Validated annotation payload (``message_id``, ``thread_id``).
        annotator_id: Override for the annotator's user ID.
        project_id: Override for the project ID.

    Returns:
        The newly created ``Annotation`` ORM object.

    Raises:
        HTTPException: 400 if neither the explicit parameters nor the schema
            object supply ``annotator_id`` or ``project_id``.
    """
    resolved_annotator_id = annotator_id or getattr(annotation, "annotator_id", None)
    resolved_project_id = project_id or getattr(annotation, "project_id", None)
    if resolved_annotator_id is None or resolved_project_id is None:
        raise HTTPException(status_code=400, detail="Missing annotator_id or project_id")
    db_annotation = models.Annotation(
        message_id=annotation.message_id,
        annotator_id=resolved_annotator_id,
        project_id=resolved_project_id,
        thread_id=annotation.thread_id
    )
    db.add(db_annotation)
    db.commit()
    db.refresh(db_annotation)
    return db_annotation


# ---------------------------------------------------------------------------
# AdjacencyPair CRUD
# ---------------------------------------------------------------------------

def get_adjacency_pair(db: Session, pair_id: int) -> Optional[models.AdjacencyPair]:
    """
    Retrieve an adjacency-pair annotation by primary key.

    Args:
        db: Active database session.
        pair_id: The pair's integer primary key.

    Returns:
        The matching ``AdjacencyPair`` object, or ``None`` if not found.
    """
    return db.query(models.AdjacencyPair).filter(models.AdjacencyPair.id == pair_id).first()


def get_adjacency_pairs_for_chat_room_by_annotator(
    db: Session, chat_room_id: int, annotator_id: int
) -> List[Tuple[models.AdjacencyPair, str]]:
    """
    Fetch adjacency pairs for a chat room scoped to a single annotator.

    Joins via ``from_message_id`` to confirm the pair belongs to the given room.

    Args:
        db: Active database session.
        chat_room_id: ID of the target chat room.
        annotator_id: ID of the annotator whose pairs should be returned.

    Returns:
        A list of ``(AdjacencyPair, annotator_username)`` tuples.
    """
    return (
        db.query(models.AdjacencyPair, models.User.username)
        .join(models.ChatMessage, models.AdjacencyPair.from_message_id == models.ChatMessage.id)
        .join(models.User, models.AdjacencyPair.annotator_id == models.User.id)
        .filter(
            models.ChatMessage.chat_room_id == chat_room_id,
            models.AdjacencyPair.annotator_id == annotator_id
        )
        .all()
    )


def get_all_adjacency_pairs_for_chat_room_admin(
    db: Session, chat_room_id: int
) -> List[Tuple[models.AdjacencyPair, str]]:
    """
    Fetch ALL adjacency pairs for a chat room across all annotators (admin).

    Args:
        db: Active database session.
        chat_room_id: ID of the target chat room.

    Returns:
        A list of ``(AdjacencyPair, annotator_username)`` tuples.
    """
    return (
        db.query(models.AdjacencyPair, models.User.username)
        .join(models.ChatMessage, models.AdjacencyPair.from_message_id == models.ChatMessage.id)
        .join(models.User, models.AdjacencyPair.annotator_id == models.User.id)
        .filter(models.ChatMessage.chat_room_id == chat_room_id)
        .all()
    )


# ---------------------------------------------------------------------------
# ChatRoomCompletion CRUD
# ---------------------------------------------------------------------------

def get_chat_room_completion(
    db: Session, chat_room_id: int, annotator_id: int
) -> Optional[models.ChatRoomCompletion]:
    """
    Return the completion record for a single (room, annotator) pair.

    Args:
        db: Active database session.
        chat_room_id: ID of the chat room.
        annotator_id: ID of the annotator.

    Returns:
        The ``ChatRoomCompletion`` object, or ``None`` if none exists yet.
    """
    return db.query(models.ChatRoomCompletion).filter(
        models.ChatRoomCompletion.chat_room_id == chat_room_id,
        models.ChatRoomCompletion.annotator_id == annotator_id
    ).first()


def upsert_chat_room_completion(
    db: Session,
    chat_room_id: int,
    project_id: int,
    annotator_id: int,
    is_completed: bool
) -> models.ChatRoomCompletion:
    """
    Create or update the completion flag for a (room, annotator) pair.

    If a record already exists it is updated in place; otherwise a new
    one is created.  This pattern avoids unique-constraint errors.

    Args:
        db: Active database session.
        chat_room_id: ID of the chat room.
        project_id: ID of the parent project (only used on creation).
        annotator_id: ID of the annotator.
        is_completed: New completion flag value.

    Returns:
        The updated or newly created ``ChatRoomCompletion`` object.
    """
    completion = get_chat_room_completion(db, chat_room_id, annotator_id)
    if completion:
        completion.is_completed = is_completed
        completion.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(completion)
        return completion

    completion = models.ChatRoomCompletion(
        chat_room_id=chat_room_id,
        annotator_id=annotator_id,
        project_id=project_id,
        is_completed=is_completed,
        created_at=datetime.utcnow()
    )
    db.add(completion)
    db.commit()
    db.refresh(completion)
    return completion


# ---------------------------------------------------------------------------
# MessageReadStatus CRUD
# ---------------------------------------------------------------------------

def batch_upsert_read_status(
    db: Session,
    room_id: int,
    project_id: int,
    annotator_id: int,
    statuses: list,  # list of {"message_id": int, "is_read": bool}
) -> None:
    """
    Batch-update the read/unread flag for a list of messages.

    For each item in ``statuses``, updates the flag if a record already
    exists or creates a new one.  All changes are committed in a single
    transaction.

    Args:
        db: Active database session.
        room_id: ID of the chat room (used only for reference; not stored
            directly on ``MessageReadStatus``).
        project_id: ID of the parent project.
        annotator_id: ID of the annotator.
        statuses: List of dicts with ``message_id`` and ``is_read`` keys.
    """
    now = datetime.utcnow()
    for item in statuses:
        existing = db.query(models.MessageReadStatus).filter(
            models.MessageReadStatus.message_id == item["message_id"],
            models.MessageReadStatus.annotator_id == annotator_id,
        ).first()
        if existing:
            existing.is_read = item["is_read"]
            existing.updated_at = now
        else:
            db.add(models.MessageReadStatus(
                message_id=item["message_id"],
                annotator_id=annotator_id,
                project_id=project_id,
                is_read=item["is_read"],
                updated_at=now,
            ))
    db.commit()


def get_read_status_for_room(
    db: Session, room_id: int, annotator_id: int
) -> dict:
    """
    Return a mapping of ``{message_id: is_read}`` for one annotator in a room.

    Messages that have no ``MessageReadStatus`` record are absent from the
    returned dict (callers should treat a missing key as ``is_read=False``).

    Args:
        db: Active database session.
        room_id: ID of the chat room.
        annotator_id: ID of the annotator.

    Returns:
        Dict mapping ``int`` message IDs to ``bool`` read flags.
    """
    message_ids = [
        row[0] for row in
        db.query(models.ChatMessage.id).filter(models.ChatMessage.chat_room_id == room_id).all()
    ]
    if not message_ids:
        return {}
    rows = db.query(models.MessageReadStatus).filter(
        models.MessageReadStatus.message_id.in_(message_ids),
        models.MessageReadStatus.annotator_id == annotator_id,
    ).all()
    return {r.message_id: r.is_read for r in rows}


def get_read_status_summary_for_room(
    db: Session, room_id: int
) -> schemas.RoomReadStatusSummary:
    """
    Return per-message, per-annotator read status for a room (admin view).

    Joins ``MessageReadStatus`` with ``User`` to include annotator usernames.

    Args:
        db: Active database session.
        room_id: ID of the chat room.

    Returns:
        A ``RoomReadStatusSummary`` schema with all entries for the room.
    """
    message_ids = [
        row[0] for row in
        db.query(models.ChatMessage.id).filter(models.ChatMessage.chat_room_id == room_id).all()
    ]
    if not message_ids:
        return schemas.RoomReadStatusSummary(chat_room_id=room_id, entries=[])
    rows = (
        db.query(
            models.MessageReadStatus.message_id,
            models.MessageReadStatus.annotator_id,
            models.User.username,
            models.MessageReadStatus.is_read,
        )
        .join(models.User, models.MessageReadStatus.annotator_id == models.User.id)
        .filter(models.MessageReadStatus.message_id.in_(message_ids))
        .all()
    )
    entries = [
        schemas.ReadStatusEntry(
            message_id=r.message_id,
            annotator_id=r.annotator_id,
            annotator_username=r.username,
            is_read=r.is_read,
        )
        for r in rows
    ]
    return schemas.RoomReadStatusSummary(chat_room_id=room_id, entries=entries)


def get_chat_room_completion_summary(
    db: Session, chat_room_id: int
) -> schemas.ChatRoomCompletionSummary:
    """
    Return how many assigned annotators have completed a chat room.

    Queries project assignments to determine the total annotator count and
    cross-references with ``ChatRoomCompletion`` records to find completions.

    Args:
        db: Active database session.
        chat_room_id: ID of the target chat room.

    Returns:
        A ``ChatRoomCompletionSummary`` with counts and a list of completed
        annotators.

    Raises:
        HTTPException: 404 if the chat room does not exist.
    """
    chat_room = get_chat_room(db, chat_room_id)
    if not chat_room:
        raise HTTPException(status_code=404, detail="Chat room not found")

    assigned_users = (
        db.query(models.User)
        .join(models.ProjectAssignment, models.User.id == models.ProjectAssignment.user_id)
        .filter(models.ProjectAssignment.project_id == chat_room.project_id)
        .all()
    )
    total_assigned = len(assigned_users)

    # Find users who have an active completion record for this room
    completed_users = (
        db.query(models.User)
        .join(models.ProjectAssignment, models.User.id == models.ProjectAssignment.user_id)
        .join(
            models.ChatRoomCompletion,
            (models.ChatRoomCompletion.annotator_id == models.User.id) &
            (models.ChatRoomCompletion.chat_room_id == chat_room_id)
        )
        .filter(
            models.ProjectAssignment.project_id == chat_room.project_id,
            models.ChatRoomCompletion.is_completed == True
        )
        .all()
    )

    completed_annotators = [
        schemas.AnnotatorInfo(id=user.id, username=user.username)
        for user in completed_users
    ]

    return schemas.ChatRoomCompletionSummary(
        chat_room_id=chat_room_id,
        total_assigned=total_assigned,
        completed_count=len(completed_annotators),
        completed_annotators=completed_annotators
    )


def get_adjacency_pairs_status(
    db: Session, chat_room_id: int
) -> schemas.AdjacencyPairsStatus:
    """
    Return a high-level status summary for an adjacency-pairs chat room.

    Status values:
    - ``"Completed"`` — all assigned annotators have marked the room done.
    - ``"Started"``   — at least one relation exists but not all are done.
    - ``"NotStarted"``— no relations exist.

    Args:
        db: Active database session.
        chat_room_id: ID of the target chat room.

    Returns:
        An ``AdjacencyPairsStatus`` schema.

    Raises:
        HTTPException: 404 if the chat room does not exist.
    """
    chat_room = get_chat_room(db, chat_room_id)
    if not chat_room:
        raise HTTPException(status_code=404, detail="Chat room not found")

    summary = get_chat_room_completion_summary(db, chat_room_id)
    # Check whether at least one AdjacencyPair exists for this room
    has_relations = (
        db.query(models.AdjacencyPair.id)
        .join(models.ChatMessage, models.AdjacencyPair.from_message_id == models.ChatMessage.id)
        .filter(models.ChatMessage.chat_room_id == chat_room_id)
        .first()
        is not None
    )

    if summary.total_assigned > 0 and summary.completed_count == summary.total_assigned:
        status = "Completed"
    elif has_relations:
        status = "Started"
    else:
        status = "NotStarted"

    return schemas.AdjacencyPairsStatus(
        chat_room_id=chat_room_id,
        status=status,
        total_assigned=summary.total_assigned,
        completed_count=summary.completed_count,
        has_relations=has_relations
    )


# ---------------------------------------------------------------------------
# ProjectAssignment helpers
# ---------------------------------------------------------------------------

def get_project_assignment(
    db: Session, assignment_id: int
) -> Optional[models.ProjectAssignment]:
    """
    Retrieve a project assignment by primary key.

    Args:
        db: Active database session.
        assignment_id: The assignment's integer primary key.

    Returns:
        The matching ``ProjectAssignment`` object, or ``None`` if not found.
    """
    return (
        db.query(models.ProjectAssignment)
        .filter(models.ProjectAssignment.id == assignment_id)
        .first()
    )


def get_project_assignments_by_user(
    db: Session, user_id: int
) -> List[models.ProjectAssignment]:
    """
    Return all project assignments for a user.

    Args:
        db: Active database session.
        user_id: The user's ID.

    Returns:
        List of ``ProjectAssignment`` objects.
    """
    return (
        db.query(models.ProjectAssignment)
        .filter(models.ProjectAssignment.user_id == user_id)
        .all()
    )


def get_project_assignments_by_project(
    db: Session, project_id: int
) -> List[models.ProjectAssignment]:
    """
    Return all assignments for a project (i.e. which users can see it).

    Args:
        db: Active database session.
        project_id: The project's ID.

    Returns:
        List of ``ProjectAssignment`` objects.
    """
    return (
        db.query(models.ProjectAssignment)
        .filter(models.ProjectAssignment.project_id == project_id)
        .all()
    )


# Assignment creation is handled directly in the admin endpoint.


# ---------------------------------------------------------------------------
# Annotation import (Phase 2)
# ---------------------------------------------------------------------------

def import_annotations_for_chat_room(
    db: Session,
    chat_room_id: int,
    annotator_id: int,
    project_id: int,
    annotations_data: List[dict]
) -> Tuple[int, int, List[str]]:
    """
    Import annotations for a chat room and assign them to a specific annotator.

    Resolves each ``turn_id`` in ``annotations_data`` to its database
    ``message_id``.  If a disentanglement annotation already exists for the
    (message, annotator) pair it is updated; otherwise a new one is created.

    Args:
        db: Active database session.
        chat_room_id: ID of the chat room whose messages are being annotated.
        annotator_id: ID of the user the annotations are attributed to.
        project_id: ID of the parent project.
        annotations_data: List of dicts, each with ``"turn_id"`` and
            ``"thread_id"`` keys.

    Returns:
        A tuple of ``(imported_count, skipped_count, errors)`` where
        ``errors`` is a list of human-readable error strings for rows that
        could not be processed.
    """
    imported_count = 0
    skipped_count = 0
    errors = []

    for annotation_data in annotations_data:
        try:
            turn_id = annotation_data.get('turn_id')
            thread_id = annotation_data.get('thread_id')

            if not turn_id or not thread_id:
                errors.append(f"Missing turn_id or thread_id in annotation data: {annotation_data}")
                skipped_count += 1
                continue

            # Resolve the source-CSV turn identifier to the DB primary key
            message = get_chat_message_by_turn_id(db, chat_room_id, turn_id)
            if not message:
                errors.append(f"Message with turn_id '{turn_id}' not found in chat room {chat_room_id}")
                skipped_count += 1
                continue

            # Upsert: update thread_id if the annotation already exists
            existing_annotation = db.query(models.Annotation).filter(
                models.Annotation.message_id == message.id,
                models.Annotation.annotator_id == annotator_id
            ).first()

            if existing_annotation:
                existing_annotation.thread_id = thread_id
                imported_count += 1
            else:
                new_annotation = models.Annotation(
                    message_id=message.id,
                    annotator_id=annotator_id,
                    project_id=project_id,
                    thread_id=thread_id
                )
                db.add(new_annotation)
                imported_count += 1

        except Exception as e:
            errors.append(f"Error processing annotation for turn_id '{annotation_data.get('turn_id')}': {str(e)}")
            skipped_count += 1

    db.commit()
    return imported_count, skipped_count, errors


# ---------------------------------------------------------------------------
# Aggregated annotation analysis (Phase 3)
# ---------------------------------------------------------------------------

def get_aggregated_annotations_for_chat_room(
    db: Session, chat_room_id: int
) -> List[dict]:
    """
    Get aggregated annotations for a chat room, organised by message.

    Used by administrators to analyse concordance between annotators.
    Uses a LEFT OUTER JOIN so messages without any annotation still appear
    in the result.

    Args:
        db: Active database session.
        chat_room_id: ID of the target chat room.

    Returns:
        A list of dicts, one per message, each with the structure::

            {
                "message_id": int,
                "message_text": str,
                "turn_id": str,
                "user_id": str,
                "annotations": [
                    {"annotator_id": int, "annotator_username": str, "thread_id": str},
                    ...
                ]
            }

        The list is sorted by ascending ``message_id``.
    """
    # Outer join ensures messages with no annotations are still included
    results = (
        db.query(
            models.ChatMessage.id.label('message_id'),
            models.ChatMessage.turn_text.label('message_text'),
            models.ChatMessage.turn_id,
            models.ChatMessage.user_id,
            models.Annotation.id.label('annotation_id'),
            models.Annotation.annotator_id,
            models.Annotation.thread_id,
            models.User.username.label('annotator_username')
        )
        .outerjoin(models.Annotation, models.ChatMessage.id == models.Annotation.message_id)
        .outerjoin(models.User, models.Annotation.annotator_id == models.User.id)
        .filter(models.ChatMessage.chat_room_id == chat_room_id)
        .order_by(models.ChatMessage.id)
        .all()
    )

    # Group results by message using an ordered dict keyed on message_id
    messages_dict = {}
    for result in results:
        message_id = result.message_id

        if message_id not in messages_dict:
            messages_dict[message_id] = {
                "message_id": message_id,
                "message_text": result.message_text,
                "turn_id": result.turn_id,
                "user_id": result.user_id,
                "annotations": []
            }

        # Only append an annotation if the outer join produced one
        if result.annotation_id:
            messages_dict[message_id]["annotations"].append({
                "annotator_id": result.annotator_id,
                "annotator_username": result.annotator_username,
                "thread_id": result.thread_id
            })

    aggregated_data = list(messages_dict.values())
    aggregated_data.sort(key=lambda x: x["message_id"])

    return aggregated_data


# ---------------------------------------------------------------------------
# Batch annotation import (Phase 4)
# ---------------------------------------------------------------------------

def import_batch_annotations_for_chat_room(
    db: Session,
    chat_room_id: int,
    project_id: int,
    batch_data: schemas.BatchAnnotationImport
) -> schemas.BatchAnnotationImportResponse:
    """
    Import batch annotations from multiple annotators for a chat room.

    Processes a structured batch import containing multiple annotators and
    their annotations.  For each annotator the function:

    1. Looks up the user by username; if not found, creates a new account
       with a random temporary password and adds a warning to the result.
    2. Delegates to ``import_annotations_for_chat_room`` for the actual
       annotation upsert.
    3. Accumulates per-annotator statistics and any errors.
    4. Returns a consolidated response even when individual annotators fail,
       so a partial import is never lost.

    Args:
        db: Active database session.
        chat_room_id: ID of the target chat room.
        project_id: ID of the parent project.
        batch_data: Validated batch import payload.

    Returns:
        A ``BatchAnnotationImportResponse`` with per-annotator statistics.
    """
    global_errors = []
    results = []
    total_annotations_processed = 0
    total_imported = 0
    total_skipped = 0

    # Verify chat room exists and belongs to the stated project
    chat_room = get_chat_room(db, chat_room_id)
    if not chat_room:
        global_errors.append(f"Chat room {chat_room_id} not found")
        return schemas.BatchAnnotationImportResponse(
            message="Import failed: Chat room not found",
            chat_room_id=chat_room_id,
            total_annotators=0,
            total_annotations_processed=0,
            total_imported=0,
            total_skipped=0,
            results=[],
            global_errors=global_errors
        )

    if chat_room.project_id != project_id:
        global_errors.append(f"Chat room {chat_room_id} does not belong to project {project_id}")
        return schemas.BatchAnnotationImportResponse(
            message="Import failed: Chat room project mismatch",
            chat_room_id=chat_room_id,
            total_annotators=0,
            total_annotations_processed=0,
            total_imported=0,
            total_skipped=0,
            results=[],
            global_errors=global_errors
        )

    # Process each annotator entry in the batch
    for annotator_data in batch_data.annotators:
        user = None
        annotator_errors = []
        imported_count = 0
        skipped_count = 0

        try:
            user = get_user_by_username(db, annotator_data.annotator_username)
            if not user:
                # Auto-create the user with a random password; they must reset it later
                from app.auth import get_password_hash
                temporary_password = secrets.token_urlsafe(16)
                hashed_password = get_password_hash(temporary_password)
                user_create = schemas.UserCreate(
                    username=annotator_data.annotator_username,
                    password=temporary_password,
                    is_admin=False
                )
                user = create_user(db, user_create, hashed_password)
                annotator_errors.append(
                    f"User '{annotator_data.annotator_username}' created with a temporary password; reset required."
                )

            annotations_data = [
                {
                    'turn_id': ann.turn_id,
                    'thread_id': ann.thread_id
                }
                for ann in annotator_data.annotations
            ]

            total_annotations_processed += len(annotations_data)

            imported, skipped, errors = import_annotations_for_chat_room(
                db=db,
                chat_room_id=chat_room_id,
                annotator_id=user.id,
                project_id=project_id,
                annotations_data=annotations_data
            )

            imported_count = imported
            skipped_count = skipped
            annotator_errors.extend(errors)

            total_imported += imported_count
            total_skipped += skipped_count

        except Exception as e:
            error_msg = f"Failed to process annotator {annotator_data.annotator_username}: {str(e)}"
            annotator_errors.append(error_msg)
            global_errors.append(error_msg)
            skipped_count = len(annotator_data.annotations)
            total_skipped += skipped_count

        results.append(schemas.BatchAnnotationResult(
            annotator_username=annotator_data.annotator_username,
            annotator_name=annotator_data.annotator_name,
            # Use -1 as a sentinel when user creation failed entirely
            user_id=user.id if user else -1,
            imported_count=imported_count,
            skipped_count=skipped_count,
            errors=annotator_errors
        ))

    # Build a human-readable summary message
    if global_errors:
        if total_imported > 0:
            message = f"Import completed with {len(global_errors)} error(s). {total_imported} annotations imported successfully."
        else:
            message = f"Import failed with {len(global_errors)} error(s). No annotations were imported."
    else:
        message = f"Batch import completed successfully. {total_imported} annotations imported from {len(batch_data.annotators)} annotators."

    return schemas.BatchAnnotationImportResponse(
        message=message,
        chat_room_id=chat_room_id,
        total_annotators=len(batch_data.annotators),
        total_annotations_processed=total_annotations_processed,
        total_imported=total_imported,
        total_skipped=total_skipped,
        results=results,
        global_errors=global_errors
    )


# ---------------------------------------------------------------------------
# IAA computation helpers (Phase 5)
# ---------------------------------------------------------------------------

def _calculate_adj_pairs_iaa(
    pairs_a: List[Tuple[int, int, str]],
    pairs_b: List[Tuple[int, int, str]],
    alpha: float,
) -> dict:
    """
    Calculate the adjacency-pairs IAA between two annotators.

    Formula: ``combined_iaa = link_f1 × (α + (1 − α) × type_accuracy)``

    - **Link F1** measures how much the sets of directed links (ignoring
      relation type) overlap.  It is the harmonic mean of precision and
      recall, which simplifies to ``2 × |agreed| / (|A| + |B|)``.
    - **Type accuracy** is the fraction of agreed links where both annotators
      chose the same relation type.
    - **alpha** weights the contribution of type accuracy (α=1 means only
      links matter; α=0 means type accuracy is the only factor).

    Each pair is a ``(from_message_id, to_message_id, relation_type)`` tuple.

    Args:
        pairs_a: Annotations from the first annotator.
        pairs_b: Annotations from the second annotator.
        alpha: Weighting parameter for the combined score (0–1).

    Returns:
        A dict with keys ``link_f1``, ``type_accuracy``, ``agreed_links_count``,
        and ``combined_iaa``.
    """
    links_a = {(p[0], p[1]) for p in pairs_a}
    links_b = {(p[0], p[1]) for p in pairs_b}
    agreed_links = links_a & links_b
    agreed_count = len(agreed_links)

    denom = len(links_a) + len(links_b)
    link_f1 = 2 * agreed_count / denom if denom > 0 else 0.0

    if agreed_count == 0:
        type_acc = 0.0
    else:
        type_a = {(p[0], p[1]): p[2] for p in pairs_a}
        type_b = {(p[0], p[1]): p[2] for p in pairs_b}
        matching = sum(1 for link in agreed_links if type_a[link] == type_b[link])
        type_acc = matching / agreed_count

    combined_iaa = link_f1 * (alpha + (1 - alpha) * type_acc)

    return {
        "link_f1": link_f1,
        "type_accuracy": type_acc,
        "agreed_links_count": agreed_count,
        "combined_iaa": combined_iaa,
    }


def _calculate_one_to_one_accuracy(annot1: List[str], annot2: List[str]) -> float:
    """
    Compute the one-to-one accuracy metric for two lists of thread labels.

    This metric finds the optimal bijective mapping between the thread labels
    used by each annotator (using the Hungarian algorithm) and returns the
    fraction of messages whose labels align under that mapping, expressed as
    a percentage.

    Because thread label names are arbitrary, two annotators can use different
    labels for the same thread and still achieve 100% agreement — only the
    grouping structure matters.

    Parameters:
        annot1: Thread label per message from the first annotator.
        annot2: Thread label per message from the second annotator.
            Must have the same length as ``annot1``.

    Returns:
        A float in [0, 100] representing the percentage of messages whose
        thread assignments are consistent under the optimal label mapping.
    """
    assert len(annot1) == len(annot2), "Annotation lists must have the same length."

    if len(annot1) == 0:
        return 0.0

    # Build a contingency matrix counting co-occurrences of each label pair
    unique_labels1 = sorted(list(set(annot1)))
    unique_labels2 = sorted(list(set(annot2)))

    label_map1 = {label: i for i, label in enumerate(unique_labels1)}
    label_map2 = {label: i for i, label in enumerate(unique_labels2)}

    overlap_matrix = np.zeros((len(unique_labels1), len(unique_labels2)), dtype=int)

    for i in range(len(annot1)):
        idx1 = label_map1[annot1[i]]
        idx2 = label_map2[annot2[i]]
        overlap_matrix[idx1, idx2] += 1

    # Negate the matrix because linear_sum_assignment minimises cost;
    # we want to maximise the total overlap.
    row_ind, col_ind = linear_sum_assignment(-overlap_matrix)

    total_overlap = overlap_matrix[row_ind, col_ind].sum()

    accuracy = (total_overlap / len(annot1)) * 100 if len(annot1) > 0 else 0

    return accuracy


def get_chat_room_iaa_analysis(
    db: Session,
    chat_room_id: int,
    alpha_override: Optional[float] = None,
) -> schemas.ChatRoomIAA:
    """
    Calculate and return the IAA analysis for a chat room.

    Dispatches to the appropriate calculation depending on the project's
    ``annotation_type``:

    - ``"disentanglement"`` — pairwise one-to-one accuracy via the Hungarian
      algorithm.
    - ``"adjacency_pairs"`` — pairwise ``link_f1 × (α + (1-α) × type_acc)``.

    For disentanglement, an annotator is considered "completed" when they have
    annotated every message in the room.  For adjacency pairs, completion is
    determined by the explicit ``ChatRoomCompletion`` record.

    The ``analysis_status`` field is:
    - ``"Complete"``      — all assigned annotators are done.
    - ``"Partial"``       — at least 2 are done but not all.
    - ``"NotEnoughData"`` — fewer than 2 annotators have completed.

    Args:
        db: Active database session.
        chat_room_id: ID of the chat room to analyse.
        alpha_override: If provided, use this α value instead of the project's
            stored ``iaa_alpha``.  Useful for ad-hoc "what-if" previews.

    Returns:
        A ``ChatRoomIAA`` schema with full analysis results.

    Raises:
        HTTPException: 404 if the chat room or project is not found.
        HTTPException: 400 if the chat room has no messages.
    """
    chat_room = get_chat_room(db, chat_room_id)
    if not chat_room:
        raise HTTPException(status_code=404, detail="Chat room not found")

    project = get_project(db, chat_room.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    messages = get_chat_messages_by_room(db, chat_room_id, skip=0, limit=10000)
    message_count = len(messages)

    if message_count == 0:
        raise HTTPException(status_code=400, detail="Chat room has no messages")

    assigned_users = (
        db.query(models.User)
        .join(models.ProjectAssignment, models.User.id == models.ProjectAssignment.user_id)
        .filter(models.ProjectAssignment.project_id == chat_room.project_id)
        .all()
    )
    total_assigned = len(assigned_users)

    if project.annotation_type == "adjacency_pairs":
        return _get_adj_pairs_iaa(
            db=db,
            chat_room_id=chat_room_id,
            chat_room=chat_room,
            project=project,
            assigned_users=assigned_users,
            message_count=message_count,
            alpha_override=alpha_override,
        )

    # ── Disentanglement mode ─────────────────────────────────────────────────
    annotations_query = (
        db.query(models.Annotation, models.User.username)
        .join(models.ChatMessage, models.Annotation.message_id == models.ChatMessage.id)
        .join(models.User, models.Annotation.annotator_id == models.User.id)
        .filter(models.ChatMessage.chat_room_id == chat_room_id)
        .order_by(models.ChatMessage.id, models.Annotation.annotator_id)
        .all()
    )

    # Build a per-annotator dict: {annotator_id: {"username": ..., "annotations": {message_id: thread_id}}}
    annotator_data: dict = {}
    for annotation, username in annotations_query:
        annotator_id = annotation.annotator_id
        if annotator_id not in annotator_data:
            annotator_data[annotator_id] = {"username": username, "annotations": {}}
        annotator_data[annotator_id]["annotations"][annotation.message_id] = annotation.thread_id

    # An annotator is "completed" if they annotated every message in the room
    completed_annotators = []
    pending_annotators = []
    for user in assigned_users:
        if user.id in annotator_data and len(annotator_data[user.id]["annotations"]) == message_count:
            completed_annotators.append(schemas.AnnotatorInfo(id=user.id, username=user.username))
        else:
            pending_annotators.append(schemas.AnnotatorInfo(id=user.id, username=user.username))

    completed_count = len(completed_annotators)

    if completed_count < 2:
        return schemas.ChatRoomIAA(
            chat_room_id=chat_room_id,
            chat_room_name=chat_room.name,
            message_count=message_count,
            annotation_type="disentanglement",
            analysis_status="NotEnoughData",
            total_annotators_assigned=total_assigned,
            completed_annotators=completed_annotators,
            pending_annotators=pending_annotators,
            pairwise_accuracies=[],
        )

    analysis_status = "Complete" if completed_count == total_assigned else "Partial"
    message_ids = [msg.id for msg in messages]

    # Build ordered annotation lists for pairwise comparison
    completed_annotator_lists = {
        a.id: {
            "username": a.username,
            "annotations": [annotator_data[a.id]["annotations"][msg_id] for msg_id in message_ids],
        }
        for a in completed_annotators
    }

    pairwise_accuracies = []
    for id1, id2 in combinations(list(completed_annotator_lists.keys()), 2):
        accuracy = _calculate_one_to_one_accuracy(
            completed_annotator_lists[id1]["annotations"],
            completed_annotator_lists[id2]["annotations"],
        )
        pairwise_accuracies.append(schemas.PairwiseAccuracy(
            annotator_1_id=id1,
            annotator_2_id=id2,
            annotator_1_username=completed_annotator_lists[id1]["username"],
            annotator_2_username=completed_annotator_lists[id2]["username"],
            accuracy=accuracy,
        ))

    return schemas.ChatRoomIAA(
        chat_room_id=chat_room_id,
        chat_room_name=chat_room.name,
        message_count=message_count,
        annotation_type="disentanglement",
        analysis_status=analysis_status,
        total_annotators_assigned=total_assigned,
        completed_annotators=completed_annotators,
        pending_annotators=pending_annotators,
        pairwise_accuracies=pairwise_accuracies,
    )


def _get_adj_pairs_iaa(
    db: Session,
    chat_room_id: int,
    chat_room,
    project,
    assigned_users: list,
    message_count: int,
    alpha_override: Optional[float],
) -> schemas.ChatRoomIAA:
    """
    IAA calculation for adjacency_pairs projects.

    Completion is determined by ``ChatRoomCompletion`` records (explicit
    annotator sign-off) rather than annotation coverage.  This is the
    appropriate policy for adjacency-pair tasks where annotators may
    legitimately leave some pairs unannotated.

    Args:
        db: Active database session.
        chat_room_id: ID of the target chat room.
        chat_room: The ``ChatRoom`` ORM object.
        project: The parent ``Project`` ORM object.
        assigned_users: List of users assigned to the project.
        message_count: Number of messages in the room.
        alpha_override: If provided, overrides the project's stored
            ``iaa_alpha`` for this computation only.

    Returns:
        A ``ChatRoomIAA`` schema with adjacency-pair IAA results.
    """
    alpha = alpha_override if alpha_override is not None else project.iaa_alpha
    total_assigned = len(assigned_users)

    # Only annotators with an explicit "completed" record are included
    completed_user_ids = {
        row.annotator_id
        for row in db.query(models.ChatRoomCompletion.annotator_id)
        .filter(
            models.ChatRoomCompletion.chat_room_id == chat_room_id,
            models.ChatRoomCompletion.is_completed == True,
        )
        .all()
    }

    assigned_user_map = {u.id: u.username for u in assigned_users}
    completed_annotators = [
        schemas.AnnotatorInfo(id=uid, username=assigned_user_map[uid])
        for uid in completed_user_ids
        if uid in assigned_user_map
    ]
    pending_annotators = [
        schemas.AnnotatorInfo(id=u.id, username=u.username)
        for u in assigned_users
        if u.id not in completed_user_ids
    ]
    completed_count = len(completed_annotators)

    not_enough = schemas.ChatRoomIAA(
        chat_room_id=chat_room_id,
        chat_room_name=chat_room.name,
        message_count=message_count,
        annotation_type="adjacency_pairs",
        analysis_status="NotEnoughData",
        total_annotators_assigned=total_assigned,
        completed_annotators=completed_annotators,
        pending_annotators=pending_annotators,
        iaa_alpha=alpha,
        pairwise_adj_iaa=[],
    )

    if completed_count < 2:
        return not_enough

    # Load all pairs for this room belonging to completed annotators
    pairs_query = (
        db.query(
            models.AdjacencyPair.annotator_id,
            models.User.username,
            models.AdjacencyPair.from_message_id,
            models.AdjacencyPair.to_message_id,
            models.AdjacencyPair.relation_type,
        )
        .join(models.ChatMessage, models.AdjacencyPair.from_message_id == models.ChatMessage.id)
        .join(models.User, models.AdjacencyPair.annotator_id == models.User.id)
        .filter(
            models.ChatMessage.chat_room_id == chat_room_id,
            models.AdjacencyPair.annotator_id.in_(completed_user_ids),
        )
        .all()
    )

    # Group pairs by annotator id into lists of (from_id, to_id, relation_type) tuples
    annotator_pairs: dict = {}
    annotator_username: dict = {}
    for ann_id, username, from_id, to_id, rel_type in pairs_query:
        annotator_pairs.setdefault(ann_id, []).append((from_id, to_id, rel_type))
        annotator_username[ann_id] = username

    # Ensure every completed annotator appears, even if they have 0 pairs
    for a in completed_annotators:
        annotator_pairs.setdefault(a.id, [])
        annotator_username.setdefault(a.id, a.username)

    analysis_status = "Complete" if completed_count == total_assigned else "Partial"
    pairwise_adj_iaa = []

    for id1, id2 in combinations([a.id for a in completed_annotators], 2):
        result = _calculate_adj_pairs_iaa(
            annotator_pairs[id1], annotator_pairs[id2], alpha
        )
        pairwise_adj_iaa.append(schemas.PairwiseAdjIAA(
            annotator_1_id=id1,
            annotator_2_id=id2,
            annotator_1_username=annotator_username[id1],
            annotator_2_username=annotator_username[id2],
            link_f1=result["link_f1"],
            type_accuracy=result["type_accuracy"],
            agreed_links_count=result["agreed_links_count"],
            combined_iaa=result["combined_iaa"],
            iaa_alpha=alpha,
        ))

    return schemas.ChatRoomIAA(
        chat_room_id=chat_room_id,
        chat_room_name=chat_room.name,
        message_count=message_count,
        annotation_type="adjacency_pairs",
        analysis_status=analysis_status,
        total_annotators_assigned=total_assigned,
        completed_annotators=completed_annotators,
        pending_annotators=pending_annotators,
        iaa_alpha=alpha,
        pairwise_adj_iaa=pairwise_adj_iaa,
    )


# ---------------------------------------------------------------------------
# Export functionality
# ---------------------------------------------------------------------------

def export_chat_room_data(db: Session, chat_room_id: int) -> dict:
    """
    Export all annotated data from a chat room as a structured dict.

    Includes chat-room metadata, all messages, per-message annotations from
    all annotators, and high-level completion statistics for provenance.

    The ``completion_status`` in the returned metadata is one of:
    - ``"COMPLETE"``     — all assigned annotators have annotated every message.
    - ``"PARTIAL"``      — at least 2 annotators are complete but not all.
    - ``"INSUFFICIENT"`` — fewer than 2 annotators have finished.

    Args:
        db: Active database session.
        chat_room_id: ID of the chat room to export.

    Returns:
        A nested dict with keys ``"export_metadata"`` and ``"data"``
        (containing a ``"messages"`` list).

    Raises:
        HTTPException: 404 if the chat room does not exist.
    """
    chat_room = get_chat_room(db, chat_room_id)
    if not chat_room:
        raise HTTPException(status_code=404, detail="Chat room not found")

    # Fetch messages in insertion order for deterministic export output
    messages = db.query(models.ChatMessage).filter(
        models.ChatMessage.chat_room_id == chat_room_id
    ).order_by(models.ChatMessage.id).all()

    # Fetch all annotations with annotator usernames in message + annotator order
    annotations_query = (
        db.query(models.Annotation, models.User.username)
        .join(models.ChatMessage, models.Annotation.message_id == models.ChatMessage.id)
        .join(models.User, models.Annotation.annotator_id == models.User.id)
        .filter(models.ChatMessage.chat_room_id == chat_room_id)
        .order_by(models.ChatMessage.id, models.Annotation.annotator_id)
        .all()
    )

    # Group annotations by message ID for O(1) lookup when building the export
    annotations_by_message = {}
    for annotation, annotator_username in annotations_query:
        message_id = annotation.message_id
        if message_id not in annotations_by_message:
            annotations_by_message[message_id] = []

        annotations_by_message[message_id].append({
            "id": annotation.id,
            "thread_id": annotation.thread_id,
            "annotator_username": annotator_username,
            "created_at": annotation.created_at.isoformat(),
            "updated_at": annotation.updated_at.isoformat() if annotation.updated_at else None
        })

    assigned_users = (
        db.query(models.User)
        .join(models.ProjectAssignment, models.User.id == models.ProjectAssignment.user_id)
        .filter(models.ProjectAssignment.project_id == chat_room.project_id)
        .all()
    )

    total_messages = len(messages)
    total_annotators = len(assigned_users)

    # An annotator is "complete" only if they annotated every single message
    annotator_completion = {}
    for annotation, annotator_username in annotations_query:
        annotator_id = annotation.annotator_id
        if annotator_id not in annotator_completion:
            annotator_completion[annotator_id] = set()
        annotator_completion[annotator_id].add(annotation.message_id)

    completed_annotators = sum(
        1 for message_set in annotator_completion.values()
        if len(message_set) == total_messages
    )

    completion_percentage = (
        (completed_annotators / total_annotators * 100) if total_annotators > 0 else 0
    )

    if completed_annotators == total_annotators and total_annotators > 0:
        completion_status = "COMPLETE"
    elif completed_annotators >= 2:
        completion_status = "PARTIAL"
    else:
        completion_status = "INSUFFICIENT"

    annotated_messages = len(annotations_by_message)

    export_data = {
        "export_metadata": {
            "chat_room_id": chat_room.id,
            "chat_room_name": chat_room.name,
            "project_id": chat_room.project_id,
            "export_timestamp": datetime.now().isoformat(),
            "completion_status": completion_status,
            "completion_percentage": round(completion_percentage, 1),
            "total_annotators": total_annotators,
            "completed_annotators": completed_annotators,
            "total_messages": total_messages,
            "annotated_messages": annotated_messages,
            "annotation_coverage": (
                round((annotated_messages / total_messages * 100), 1)
                if total_messages > 0 else 0
            )
        },
        "data": {
            "messages": []
        }
    }

    for message in messages:
        message_data = {
            "id": message.id,
            "turn_id": message.turn_id,
            "user_id": message.user_id,
            "turn_text": message.turn_text,
            "reply_to_turn": message.reply_to_turn,
            "created_at": message.created_at.isoformat(),
            "annotations": annotations_by_message.get(message.id, [])
        }
        export_data["data"]["messages"].append(message_data)

    return export_data
