"""
SQLAlchemy ORM models for the LACE annotation platform.

Each class maps to a database table.  Relationships use ``cascade="all,
delete-orphan"`` so that child rows are removed automatically when their
parent is deleted.
"""
from sqlalchemy import Column, Integer, String, Text, ForeignKey, Boolean, DateTime, UniqueConstraint, Index, JSON
from sqlalchemy.orm import relationship, declarative_base, Mapped, mapped_column
from sqlalchemy.sql import func
from datetime import datetime

Base = declarative_base()


class User(Base):
    """A registered user of the platform (annotator or admin)."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, server_default='false')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    project_assignments = relationship("ProjectAssignment", back_populates="user", cascade="all, delete-orphan")
    annotations = relationship("Annotation", back_populates="annotator", cascade="all, delete-orphan")
    adjacency_pairs = relationship("AdjacencyPair", back_populates="annotator", cascade="all, delete-orphan")
    chat_room_completions = relationship("ChatRoomCompletion", back_populates="annotator", cascade="all, delete-orphan")


class Project(Base):
    """
    An annotation project grouping one or more chat rooms.

    ``annotation_type`` is either ``"disentanglement"`` (thread labelling) or
    ``"adjacency_pairs"`` (linking FPP/SPP pairs).

    ``relation_types`` is a JSON list of allowed relation labels used in
    adjacency-pair projects (e.g. ``["Q-A", "Greeting"]``).

    ``iaa_alpha`` is the weighting factor applied to type accuracy in the
    combined IAA formula for adjacency-pair projects.
    """

    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    annotation_type: Mapped[str] = mapped_column(String, nullable=False, default="disentanglement")
    relation_types: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    iaa_alpha: Mapped[float] = mapped_column(default=0.8, nullable=False, server_default="0.8")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    chat_rooms = relationship("ChatRoom", back_populates="project", cascade="all, delete-orphan")
    assignments = relationship("ProjectAssignment", back_populates="project", cascade="all, delete-orphan")
    annotations = relationship("Annotation", back_populates="project", cascade="all, delete-orphan")
    adjacency_pairs = relationship("AdjacencyPair", back_populates="project", cascade="all, delete-orphan")


class ProjectAssignment(Base):
    """
    Many-to-many join table that grants a user access to a project.

    A unique constraint on ``(user_id, project_id)`` prevents duplicate
    assignments.
    """

    __tablename__ = "project_assignments"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))

    # Relationships
    user = relationship("User", back_populates="project_assignments")
    project = relationship("Project", back_populates="assignments")

    # Constraints
    __table_args__ = (
        UniqueConstraint('user_id', 'project_id', name='uix_user_project'),
    )


class ChatRoom(Base):
    """
    A single conversation imported into a project.

    Each chat room contains an ordered set of ``ChatMessage`` rows imported
    from a CSV file.
    """

    __tablename__ = "chat_rooms"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    project = relationship("Project", back_populates="chat_rooms")
    messages = relationship("ChatMessage", back_populates="chat_room", cascade="all, delete-orphan")


class ChatMessage(Base):
    """
    A single turn within a chat room.

    ``turn_id`` is the original identifier from the imported CSV (e.g.
    ``"VAC_R10_001"``).  ``reply_to_turn`` stores the ``turn_id`` of the
    message this turn is a direct reply to, or ``None`` if there is no
    explicit reply link.

    Compound indexes accelerate the common queries that filter by
    ``chat_room_id`` and look up messages by ``turn_id`` or ``reply_to_turn``.
    """

    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    turn_id: Mapped[str] = mapped_column(String, nullable=False)
    user_id: Mapped[str] = mapped_column(String, nullable=False)
    turn_text: Mapped[str] = mapped_column(Text, nullable=False)
    reply_to_turn: Mapped[str] = mapped_column(String, nullable=True)
    chat_room_id: Mapped[int] = mapped_column(ForeignKey("chat_rooms.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    chat_room = relationship("ChatRoom", back_populates="messages")
    annotations = relationship("Annotation", back_populates="message", cascade="all, delete-orphan")
    outgoing_pairs = relationship(
        "AdjacencyPair",
        back_populates="from_message",
        foreign_keys="AdjacencyPair.from_message_id",
        cascade="all, delete-orphan"
    )
    incoming_pairs = relationship(
        "AdjacencyPair",
        back_populates="to_message",
        foreign_keys="AdjacencyPair.to_message_id",
        cascade="all, delete-orphan"
    )

    # Indexes and constraints
    __table_args__ = (
        Index('ix_chat_messages_chatroom_turn', 'chat_room_id', 'turn_id'),
        Index('ix_chat_messages_chatroom_reply', 'chat_room_id', 'reply_to_turn'),
        UniqueConstraint('chat_room_id', 'turn_id', name='uix_chatroom_turn'),
    )


class Annotation(Base):
    """
    A disentanglement annotation: one annotator assigns one message to a thread.

    ``thread_id`` is a free-form string label chosen by the annotator (e.g.
    ``"Thread_0"``).  The unique constraint on ``(message_id, annotator_id)``
    enforces one annotation per message per annotator.
    """

    __tablename__ = "disentanglement_annotation"

    id: Mapped[int] = mapped_column(primary_key=True)
    message_id: Mapped[int] = mapped_column(ForeignKey("chat_messages.id", ondelete="CASCADE"))
    annotator_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    thread_id: Mapped[str] = mapped_column(String)  # Thread identifier chosen by the annotator
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    message = relationship("ChatMessage", back_populates="annotations")
    annotator = relationship("User", back_populates="annotations")
    project = relationship("Project", back_populates="annotations")

    # Indexes and constraints
    __table_args__ = (
        Index('ix_annotations_message_annotator', 'message_id', 'annotator_id'),
        Index('ix_annotations_thread', 'thread_id'),
        UniqueConstraint('message_id', 'annotator_id', name='uix_message_annotator'),
    )


class AdjacencyPair(Base):
    """
    An adjacency-pair annotation linking two messages with a typed relation.

    An adjacency pair consists of a First Pair Part (FPP, ``from_message``)
    and a Second Pair Part (SPP, ``to_message``).  ``relation_type`` must be
    one of the labels configured in the parent ``Project.relation_types`` list.

    The unique constraint on ``(from_message_id, to_message_id, annotator_id)``
    ensures an annotator can only create one relation between any two messages,
    though the relation type can be updated.
    """

    __tablename__ = "adj_pairs_annotation"

    id: Mapped[int] = mapped_column(primary_key=True)
    from_message_id: Mapped[int] = mapped_column(ForeignKey("chat_messages.id", ondelete="CASCADE"), nullable=False)
    to_message_id: Mapped[int] = mapped_column(ForeignKey("chat_messages.id", ondelete="CASCADE"), nullable=False)
    annotator_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    relation_type: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    from_message = relationship("ChatMessage", foreign_keys=[from_message_id], back_populates="outgoing_pairs")
    to_message = relationship("ChatMessage", foreign_keys=[to_message_id], back_populates="incoming_pairs")
    annotator = relationship("User", back_populates="adjacency_pairs")
    project = relationship("Project", back_populates="adjacency_pairs")

    # Indexes and constraints
    __table_args__ = (
        Index('ix_adjacency_pairs_from', 'from_message_id'),
        Index('ix_adjacency_pairs_to', 'to_message_id'),
        Index('ix_adjacency_pairs_project', 'project_id'),
        UniqueConstraint('from_message_id', 'to_message_id', 'annotator_id', name='uix_adjacency_pair'),
    )


class MessageReadStatus(Base):
    """
    Per-annotator read/unread flag for a single message.

    Used to let annotators track which turns they have already reviewed.
    The unique constraint on ``(message_id, annotator_id)`` means one flag
    row per (message, annotator) pair; updates are done in-place.
    """

    __tablename__ = "message_read_status"

    id: Mapped[int] = mapped_column(primary_key=True)
    message_id: Mapped[int] = mapped_column(ForeignKey("chat_messages.id", ondelete="CASCADE"), nullable=False)
    annotator_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, server_default='false')
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint('message_id', 'annotator_id', name='uix_message_read_status'),
        Index('ix_message_read_status_message', 'message_id'),
        Index('ix_message_read_status_annotator', 'annotator_id'),
    )


class ChatRoomCompletion(Base):
    """
    Records whether a specific annotator has marked a chat room as complete.

    Completion is set explicitly by the annotator via a PUT endpoint, as
    opposed to being inferred automatically from annotation coverage.  This
    allows annotators to signal they are done even if they chose not to
    annotate every message.

    The unique constraint on ``(chat_room_id, annotator_id)`` ensures a single
    completion record per annotator per room.
    """

    __tablename__ = "chat_room_completions"

    id: Mapped[int] = mapped_column(primary_key=True)
    chat_room_id: Mapped[int] = mapped_column(ForeignKey("chat_rooms.id", ondelete="CASCADE"), nullable=False)
    annotator_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False, server_default='false')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    annotator = relationship("User", back_populates="chat_room_completions")

    __table_args__ = (
        UniqueConstraint('chat_room_id', 'annotator_id', name='uix_chat_room_completion'),
        Index('ix_chat_room_completions_chat_room', 'chat_room_id'),
        Index('ix_chat_room_completions_project', 'project_id'),
    )
