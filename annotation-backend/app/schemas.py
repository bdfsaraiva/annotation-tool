"""
Pydantic schemas for request/response validation and serialisation.

The module is organised by domain: User, Project, ChatRoom, ChatMessage,
Annotation, AdjacencyPair, read-status, chat-room completion, auth tokens,
and import/export operations.

Each domain typically has a hierarchy:
- ``<Model>Base``   — shared fields
- ``<Model>Create`` — payload accepted on creation endpoints
- ``<Model>``       — response shape returned to clients
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ---------------------------------------------------------------------------
# User Schemas
# ---------------------------------------------------------------------------

class UserBase(BaseModel):
    """Shared fields for all user-related payloads."""
    username: str = Field(..., min_length=3)


class UserCreate(UserBase):
    """Payload accepted when creating a new user account."""
    password: str
    is_admin: bool = False


class UserUpdate(BaseModel):
    """
    Partial payload for updating an existing user.

    All fields are optional so callers can update only what changed.
    """
    username: Optional[str] = Field(default=None, min_length=3)
    password: Optional[str] = None
    is_admin: Optional[bool] = None


class User(UserBase):
    """Full user representation returned by the API."""
    id: int
    is_admin: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Project Schemas
# ---------------------------------------------------------------------------

class ProjectBase(BaseModel):
    """Shared fields for project payloads."""
    name: str
    description: Optional[str] = None
    annotation_type: str = Field(default="disentanglement")
    relation_types: List[str] = Field(default_factory=list)
    iaa_alpha: float = Field(default=0.8, ge=0.0, le=1.0)
    """Weighting factor α used in the combined adjacency-pair IAA formula."""


class ProjectCreate(ProjectBase):
    """Payload accepted when creating a new project."""
    pass


class Project(ProjectBase):
    """Full project representation returned by the API."""
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProjectList(BaseModel):
    """Paginated list of projects."""
    projects: List[Project]


class ProjectUpdate(BaseModel):
    """
    Partial payload for updating project metadata.

    All fields are optional; only provided fields are applied.
    """
    name: Optional[str] = None
    description: Optional[str] = None
    annotation_type: Optional[str] = None
    relation_types: Optional[List[str]] = None
    iaa_alpha: Optional[float] = Field(default=None, ge=0.0, le=1.0)


# ---------------------------------------------------------------------------
# Chat Room Schemas
# ---------------------------------------------------------------------------

class ChatRoomBase(BaseModel):
    """Shared fields for chat room payloads."""
    name: str
    description: Optional[str] = None


class ChatRoomCreate(ChatRoomBase):
    """Payload accepted when creating a new chat room."""
    project_id: int


class ChatRoomUpdate(BaseModel):
    """Partial payload for renaming or re-describing a chat room."""
    name: Optional[str] = Field(default=None, min_length=1)
    description: Optional[str] = None


class ChatRoom(ChatRoomBase):
    """Full chat room representation returned by the API."""
    id: int
    project_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ChatRoomList(BaseModel):
    """List of chat rooms."""
    chat_rooms: List[ChatRoom]


# ---------------------------------------------------------------------------
# Message Schemas
# ---------------------------------------------------------------------------

class ChatMessageBase(BaseModel):
    """Shared fields for chat message payloads."""
    turn_id: str
    """Original identifier from the source CSV (e.g. ``"VAC_R10_001"``)."""
    user_id: str
    """Identifier of the participant who sent the turn."""
    turn_text: str
    reply_to_turn: Optional[str] = None
    """``turn_id`` of the message this turn directly replies to, if any."""


class ChatMessageCreate(ChatMessageBase):
    """Payload accepted when creating a chat message."""
    pass


class ChatMessage(ChatMessageBase):
    """Full chat message representation returned by the API."""
    id: int
    chat_room_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class MessageList(BaseModel):
    """Paginated list of messages with a total count for cursor navigation."""
    messages: List[ChatMessage]
    total: int


# ---------------------------------------------------------------------------
# Annotation Schemas (disentanglement)
# ---------------------------------------------------------------------------

class AnnotationBase(BaseModel):
    """Shared fields for disentanglement annotation payloads."""
    message_id: int
    thread_id: str = Field(..., min_length=1, max_length=50)
    """Free-form thread label chosen by the annotator."""


class AnnotationCreate(AnnotationBase):
    """Payload accepted when creating a new annotation."""
    pass


class Annotation(AnnotationBase):
    """Full annotation representation returned by the API."""
    id: int
    annotator_id: int
    annotator_username: str
    project_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AnnotationList(BaseModel):
    """List of annotations."""
    annotations: List[Annotation]


# ---------------------------------------------------------------------------
# Adjacency Pair Schemas
# ---------------------------------------------------------------------------

class AdjacencyPairBase(BaseModel):
    """Shared fields for adjacency-pair annotation payloads."""
    from_message_id: int
    """Database ID of the First Pair Part (FPP) message."""
    to_message_id: int
    """Database ID of the Second Pair Part (SPP) message."""
    relation_type: str = Field(..., min_length=1, max_length=100)
    """Relation label; must be one of the project's configured ``relation_types``."""


class AdjacencyPairCreate(AdjacencyPairBase):
    """Payload accepted when creating or updating an adjacency pair."""
    pass


class AdjacencyPair(AdjacencyPairBase):
    """Full adjacency pair representation returned by the API."""
    id: int
    annotator_id: int
    annotator_username: str
    project_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Message Read Status Schemas
# ---------------------------------------------------------------------------

class MessageReadStatusItem(BaseModel):
    """A single message read-status flag within a batch update payload."""
    message_id: int
    is_read: bool


class MessageReadStatusBatchUpdate(BaseModel):
    """Payload for a batch read-status update (multiple messages at once)."""
    statuses: List[MessageReadStatusItem]


class MessageReadStatusResponse(BaseModel):
    """Read-status for a single message returned by the API."""
    message_id: int
    is_read: bool


class ReadStatusEntry(BaseModel):
    """One annotator's read flag for one message (used in admin summaries)."""
    message_id: int
    annotator_id: int
    annotator_username: str
    is_read: bool


class RoomReadStatusSummary(BaseModel):
    """Admin-level summary of all read-status flags in a chat room."""
    chat_room_id: int
    entries: List[ReadStatusEntry]


# ---------------------------------------------------------------------------
# Chat Room Completion Schemas
# ---------------------------------------------------------------------------

class ChatRoomCompletionUpdate(BaseModel):
    """Payload to mark or unmark a chat room as completed."""
    is_completed: bool


class ChatRoomCompletion(BaseModel):
    """Completion record for a single (room, annotator) pair."""
    chat_room_id: int
    annotator_id: int
    project_id: int
    is_completed: bool
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Authentication Schemas
# ---------------------------------------------------------------------------

class Token(BaseModel):
    """Standard OAuth2 token response."""
    access_token: str
    token_type: str


class RefreshTokenRequest(BaseModel):
    """Request body for the token-refresh endpoint."""
    refresh_token: str


class TokenData(BaseModel):
    """Decoded JWT payload; ``username`` is the ``sub`` claim."""
    username: Optional[str] = None


# ---------------------------------------------------------------------------
# CSV Import / Export Schemas
# ---------------------------------------------------------------------------

class CSVImportResponse(BaseModel):
    """Summary of a completed CSV chat-message import operation."""
    message: str = "Import completed"
    total_messages: int
    imported_count: int
    skipped_count: int
    errors: List[str] = []
    warnings: List[str] = []


class CSVPreviewRow(BaseModel):
    """A single row returned during a CSV preview (before committing)."""
    turn_id: str
    user_id: str
    turn_text: str
    reply_to_turn: Optional[str] = None


class CSVPreviewResponse(BaseModel):
    """Preview result showing the first N rows of a CSV file."""
    total_rows: int
    preview_rows: List[CSVPreviewRow]
    warnings: List[str] = []


class ChatRoomImportResponse(BaseModel):
    """Combined response for the single-step chat-room creation + CSV import."""
    chat_room: ChatRoom  # Details of the newly created chat room
    import_details: CSVImportResponse  # Import statistics


# ---------------------------------------------------------------------------
# Annotation Import Schemas (Phase 2)
# ---------------------------------------------------------------------------

class AnnotationImportResponse(BaseModel):
    """Summary of a completed single-annotator annotation CSV import."""
    message: str = "Annotation import completed"
    chat_room_id: int
    annotator_id: int
    annotator_username: str
    total_annotations: int
    imported_count: int
    skipped_count: int
    errors: List[str] = []


class AnnotationPreviewRow(BaseModel):
    """A single row returned during an annotation CSV preview."""
    turn_id: str
    thread_id: str


class AnnotationPreviewResponse(BaseModel):
    """Preview result showing the first N rows of an annotation CSV."""
    total_rows: int
    preview_rows: List[AnnotationPreviewRow]


# ---------------------------------------------------------------------------
# Aggregated Annotation Analysis Schemas (Phase 3)
# ---------------------------------------------------------------------------

class AnnotationDetail(BaseModel):
    """One annotator's thread assignment for a single message."""
    annotator_id: int
    annotator_username: str
    thread_id: str


class AggregatedMessageAnnotations(BaseModel):
    """All annotations for a single message, from all annotators."""
    message_id: int
    message_text: str
    turn_id: str
    user_id: str
    annotations: List[AnnotationDetail]


class AggregatedAnnotationsResponse(BaseModel):
    """Full aggregated annotation response for a chat room (admin view)."""
    chat_room_id: int
    messages: List[AggregatedMessageAnnotations]
    total_messages: int
    annotated_messages: int
    total_annotators: int
    annotators: List[str]  # Sorted list of annotator usernames present in the data


# ---------------------------------------------------------------------------
# Batch Annotation Import Schemas (Phase 4)
# ---------------------------------------------------------------------------

class BatchAnnotationItem(BaseModel):
    """A single (turn_id, thread_id) pair within a batch import."""
    turn_id: str
    thread_id: str


class BatchAnnotatorMetadata(BaseModel):
    """Optional provenance metadata attached to one annotator's batch entry."""
    tool_used: Optional[str] = None
    source_file: Optional[str] = None
    total_annotations: Optional[int] = None
    experience_level: Optional[str] = None
    notes: Optional[str] = None


class BatchAnnotator(BaseModel):
    """One annotator's data block within a batch import JSON file."""
    annotator_username: str = Field(..., min_length=3)
    annotator_name: str
    annotator_metadata: Optional[BatchAnnotatorMetadata] = None
    annotations: List[BatchAnnotationItem]


class BatchMetadata(BaseModel):
    """Top-level metadata block of a batch import JSON file."""
    project_id: int
    chat_room_id: int
    import_description: Optional[str] = None
    import_timestamp: str
    created_by: Optional[str] = None
    source_files: Optional[List[str]] = None


class BatchAnnotationImport(BaseModel):
    """Root structure of a batch annotation JSON file."""
    batch_metadata: BatchMetadata
    annotators: List[BatchAnnotator]


class BatchAnnotationResult(BaseModel):
    """Per-annotator outcome from a batch import operation."""
    annotator_username: str
    annotator_name: str
    user_id: int
    imported_count: int
    skipped_count: int
    errors: List[str] = []


class BatchAnnotationImportResponse(BaseModel):
    """Summary returned after a batch annotation import completes."""
    message: str = "Batch annotation import completed"
    chat_room_id: int
    total_annotators: int
    total_annotations_processed: int
    total_imported: int
    total_skipped: int
    results: List[BatchAnnotationResult]
    global_errors: List[str] = []


class BatchAnnotationPreviewAnnotator(BaseModel):
    """Summary of one annotator's entry shown during a batch import preview."""
    annotator_username: str
    annotator_name: str
    annotations_count: int


class BatchAnnotationPreviewResponse(BaseModel):
    """Preview result for a batch annotation JSON file (before committing)."""
    chat_room_id: int
    project_id: int
    total_annotators: int
    total_annotations: int
    preview_annotators: List[BatchAnnotationPreviewAnnotator]


# ---------------------------------------------------------------------------
# Inter-Annotator Agreement (IAA) Schemas (Phase 5)
# ---------------------------------------------------------------------------

class PairwiseAccuracy(BaseModel):
    """Represents the one-to-one accuracy score between two annotators."""
    annotator_1_id: int
    annotator_2_id: int
    annotator_1_username: str
    annotator_2_username: str
    accuracy: float
    """Percentage score (0–100) from the Hungarian-algorithm matching."""


class PairwiseAdjIAA(BaseModel):
    """Represents the combined IAA score for adjacency pairs between two annotators."""
    annotator_1_id: int
    annotator_2_id: int
    annotator_1_username: str
    annotator_2_username: str
    link_f1: float
    """F1 score measuring overlap of linked message pairs (ignoring relation type)."""
    type_accuracy: float
    """Fraction of agreed links where both annotators assigned the same relation type."""
    agreed_links_count: int
    combined_iaa: float
    """Combined score: ``link_f1 × (α + (1 − α) × type_accuracy)``."""
    iaa_alpha: float
    """The α weighting used in this calculation."""


class AnnotatorInfo(BaseModel):
    """Information about an annotator."""
    id: int
    username: str


class ChatRoomCompletionSummary(BaseModel):
    """
    Summary of how many assigned annotators have marked a room as complete.
    """
    chat_room_id: int
    total_assigned: int
    completed_count: int
    completed_annotators: List[AnnotatorInfo]


class AdjacencyPairsStatus(BaseModel):
    """
    High-level annotation status for an adjacency-pairs chat room.

    ``status`` is one of ``"NotStarted"``, ``"Started"``, or ``"Completed"``.
    """
    chat_room_id: int
    status: str
    total_assigned: int
    completed_count: int
    has_relations: bool
    """True if at least one adjacency pair has been created in this room."""


class ChatRoomIAA(BaseModel):
    """Holds the complete IAA analysis for a single chat room."""
    chat_room_id: int
    chat_room_name: str
    message_count: int
    annotation_type: str  # "disentanglement" or "adjacency_pairs"

    # "Complete" = all assigned annotators are done,
    # "Partial"  = some are done,
    # "NotEnoughData" = fewer than 2 annotators have completed the room.
    analysis_status: str

    total_annotators_assigned: int
    completed_annotators: List[AnnotatorInfo]
    pending_annotators: List[AnnotatorInfo]

    # Disentanglement mode — one entry per annotator pair
    pairwise_accuracies: List[PairwiseAccuracy] = []

    # Adjacency pairs mode
    iaa_alpha: Optional[float] = None
    """The α value used for the combined IAA formula (adjacency_pairs only)."""
    pairwise_adj_iaa: List[PairwiseAdjIAA] = []
