"""
Question-analysis annotation endpoints.

All routes are mounted under the prefix::

    /projects/{project_id}/chat-rooms/{room_id}/question-analysis

Every handler checks that the project is configured for ``"question_analysis"``
annotation mode before proceeding (via ``_ensure_project_mode``).  The
annotation-isolation rule (Pillar 1) is applied in the list endpoint: regular
annotators see only their own annotations; admins see all.

The POST endpoint doubles as a create-or-update (upsert): if a question-analysis
annotation already exists for the current annotator and message, its fields are
updated in place rather than creating a duplicate.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from ..auth import get_current_user
from ..dependencies import verify_project_access
from ..models import (
    User,
    QuestionAnalysisAnnotation as QAModel,
    ChatMessage,
    ChatRoom,
    Project,
)
from ..schemas import (
    QuestionAnalysisAnnotation as QASchema,
    QuestionAnalysisAnnotationCreate,
)
from .. import crud

router = APIRouter(
    prefix="/projects/{project_id}/chat-rooms/{room_id}/question-analysis",
    tags=["question analysis"]
)


def _serialize(annotation: QAModel, annotator_username: str) -> QASchema:
    """Convert a QA annotation ORM row to its Pydantic response shape."""
    return QASchema(
        id=annotation.id,
        message_id=annotation.message_id,
        annotator_id=annotation.annotator_id,
        annotator_username=annotator_username,
        project_id=annotation.project_id,
        is_question=bool(annotation.is_question),
        label=annotation.label,
        trigger_marker=bool(annotation.trigger_marker),
        trigger_primary=bool(annotation.trigger_primary),
        trigger_f2=bool(annotation.trigger_f2),
        trigger_f3=bool(annotation.trigger_f3),
        trigger_f4=bool(annotation.trigger_f4),
        trigger_f5=bool(annotation.trigger_f5),
        trigger_f6=bool(annotation.trigger_f6),
        borderline=bool(annotation.borderline),
        multiform=bool(annotation.multiform),
        created_at=annotation.created_at,
        updated_at=annotation.updated_at,
    )


def _ensure_project_mode(project: Project) -> None:
    """Raise 400 if the project is not configured for question_analysis."""
    if project.annotation_type != "question_analysis":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This project is not configured for question-analysis annotation"
        )


@router.get("/", response_model=List[QASchema])
def list_question_analysis(
    project_id: int,
    room_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(verify_project_access),
) -> List[QASchema]:
    """
    Return question-analysis annotations for a chat room.

    Annotators receive only their own rows; admins receive every annotator's.
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    _ensure_project_mode(project)

    chat_room = db.query(ChatRoom).filter(
        ChatRoom.id == room_id,
        ChatRoom.project_id == project_id,
    ).first()
    if not chat_room:
        raise HTTPException(status_code=404, detail="Chat room not found in this project")

    if current_user.is_admin:
        rows = crud.get_all_question_analysis_for_chat_room_admin(db, chat_room_id=room_id)
    else:
        rows = crud.get_question_analysis_for_chat_room_by_annotator(
            db, chat_room_id=room_id, annotator_id=current_user.id
        )

    return [_serialize(annotation, username) for annotation, username in rows]


@router.post("/", response_model=QASchema)
def upsert_question_analysis(
    project_id: int,
    room_id: int,
    payload: QuestionAnalysisAnnotationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(verify_project_access),
) -> QASchema:
    """
    Create or update a question-analysis annotation for the current annotator.

    Idempotent under ``(message_id, annotator_id)``: a second call with a new
    payload overwrites the existing row's fields in place.
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    _ensure_project_mode(project)

    message = db.query(ChatMessage).filter(
        ChatMessage.id == payload.message_id,
        ChatMessage.chat_room_id == room_id,
    ).first()
    if not message:
        raise HTTPException(status_code=404, detail="Message not found in this chat room")

    annotation = crud.upsert_question_analysis_annotation(
        db=db,
        message_id=payload.message_id,
        annotator_id=current_user.id,
        project_id=project_id,
        payload=payload,
    )
    return _serialize(annotation, current_user.username)


@router.delete("/{annotation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_question_analysis(
    project_id: int,
    room_id: int,
    annotation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(verify_project_access),
) -> None:
    """
    Delete a question-analysis annotation.

    Annotators may only delete their own rows; admins may delete any row.
    """
    annotation = crud.get_question_analysis_annotation(db, annotation_id)
    if not annotation:
        raise HTTPException(status_code=404, detail="Question-analysis annotation not found")

    if annotation.project_id != project_id:
        raise HTTPException(status_code=404, detail="Annotation not found in this project")

    message = db.query(ChatMessage).filter(
        ChatMessage.id == annotation.message_id,
        ChatMessage.chat_room_id == room_id,
    ).first()
    if not message:
        raise HTTPException(status_code=404, detail="Annotation not found in this chat room")

    if annotation.annotator_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not enough permissions to delete this annotation")

    db.delete(annotation)
    db.commit()
    return None
