from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from ..database import get_db
from ..auth import get_current_user
from ..dependencies import verify_project_access
from ..models import User, AdjacencyPair, ChatMessage, ChatRoom, Project
from ..schemas import AdjacencyPair as AdjacencyPairSchema, AdjacencyPairCreate
from .. import crud

router = APIRouter(
    prefix="/projects/{project_id}/chat-rooms/{room_id}/adjacency-pairs",
    tags=["adjacency pairs"]
)

def _ensure_project_mode(project: Project) -> None:
    if project.annotation_type != "adjacency_pairs":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This project is not configured for adjacency pair annotation"
        )

@router.get("/", response_model=List[AdjacencyPairSchema])
def list_adjacency_pairs(
    project_id: int,
    room_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(verify_project_access)
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    _ensure_project_mode(project)

    chat_room = db.query(ChatRoom).filter(
        ChatRoom.id == room_id,
        ChatRoom.project_id == project_id
    ).first()
    if not chat_room:
        raise HTTPException(status_code=404, detail="Chat room not found in this project")

    if current_user.is_admin:
        pairs_data = crud.get_all_adjacency_pairs_for_chat_room_admin(db, chat_room_id=room_id)
    else:
        pairs_data = crud.get_adjacency_pairs_for_chat_room_by_annotator(
            db, chat_room_id=room_id, annotator_id=current_user.id
        )

    result = []
    for pair, annotator_username in pairs_data:
        pair_dict = pair.__dict__
        pair_dict['annotator_username'] = annotator_username
        result.append(pair_dict)
    return result

@router.post("/", response_model=AdjacencyPairSchema)
def create_adjacency_pair(
    project_id: int,
    room_id: int,
    pair: AdjacencyPairCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(verify_project_access)
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    _ensure_project_mode(project)

    if not project.relation_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No relation types configured for this project"
        )
    if pair.relation_type not in project.relation_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid relation type for this project"
        )
    if pair.from_message_id == pair.to_message_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot create a relation from a message to itself"
        )

    # Verify both messages exist and belong to this chat room
    from_message = db.query(ChatMessage).filter(
        ChatMessage.id == pair.from_message_id,
        ChatMessage.chat_room_id == room_id
    ).first()
    to_message = db.query(ChatMessage).filter(
        ChatMessage.id == pair.to_message_id,
        ChatMessage.chat_room_id == room_id
    ).first()
    if not from_message or not to_message:
        raise HTTPException(status_code=404, detail="One or both messages not found in this chat room")

    existing = db.query(AdjacencyPair).filter(
        AdjacencyPair.from_message_id == pair.from_message_id,
        AdjacencyPair.to_message_id == pair.to_message_id,
        AdjacencyPair.annotator_id == current_user.id
    ).first()

    if existing:
        existing.relation_type = pair.relation_type
        existing.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(existing)
        pair_dict = existing.__dict__
        pair_dict['annotator_username'] = current_user.username
        return pair_dict

    db_pair = AdjacencyPair(
        from_message_id=pair.from_message_id,
        to_message_id=pair.to_message_id,
        annotator_id=current_user.id,
        project_id=project_id,
        relation_type=pair.relation_type,
        created_at=datetime.utcnow()
    )
    db.add(db_pair)
    db.commit()
    db.refresh(db_pair)
    pair_dict = db_pair.__dict__
    pair_dict['annotator_username'] = current_user.username
    return pair_dict

@router.delete("/{pair_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_adjacency_pair(
    project_id: int,
    room_id: int,
    pair_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(verify_project_access)
):
    pair = crud.get_adjacency_pair(db, pair_id)
    if not pair:
        raise HTTPException(status_code=404, detail="Adjacency pair not found")

    if pair.project_id != project_id:
        raise HTTPException(status_code=404, detail="Adjacency pair not found in this project")

    from_message = db.query(ChatMessage).filter(
        ChatMessage.id == pair.from_message_id,
        ChatMessage.chat_room_id == room_id
    ).first()
    to_message = db.query(ChatMessage).filter(
        ChatMessage.id == pair.to_message_id,
        ChatMessage.chat_room_id == room_id
    ).first()
    if not from_message or not to_message:
        raise HTTPException(status_code=404, detail="Adjacency pair not found in this chat room")

    if pair.annotator_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not enough permissions to delete this relation")

    db.delete(pair)
    db.commit()
    return None
