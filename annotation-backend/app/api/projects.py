from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from sqlalchemy import select

from ..database import get_db
from ..models import User, Project, ProjectAssignment, ChatMessage, ChatRoom
from ..schemas import (
    Project as ProjectSchema, 
    ProjectCreate, 
    User as UserSchema, 
    ProjectList, 
    MessageList,
    ChatRoom as ChatRoomSchema,
    ChatMessage as ChatMessageSchema,
    Annotation as AnnotationSchema,
    ChatRoomCompletion as ChatRoomCompletionSchema,
    ChatRoomCompletionUpdate as ChatRoomCompletionUpdateSchema
)
from ..auth import get_current_user, get_current_admin_user
from ..dependencies import verify_project_access
from .. import crud

router = APIRouter()

# Removed redundant create_project endpoint. Admin creation is handled in admin.py

@router.get("/", response_model=ProjectList)
async def list_user_projects(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all projects assigned to the current user"""
    try:
        if current_user.is_admin:
            # Admins can see all projects
            projects = db.query(Project).all()
        else:
            # Regular users only see assigned projects
            projects = (
                db.query(Project)
                .join(ProjectAssignment)
                .filter(ProjectAssignment.user_id == current_user.id)
                .all()
            )
        
        return ProjectList(projects=projects)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list projects: {str(e)}"
        )

@router.get("/{project_id}", response_model=ProjectSchema)
async def get_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific project if the user has access"""
    try:
        # First check if project exists
        project = db.query(Project).filter(Project.id == project_id).first()
        
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
        
        # Check access
        if not current_user.is_admin:
            assignment = (
                db.query(ProjectAssignment)
                .filter(
                    ProjectAssignment.project_id == project_id,
                    ProjectAssignment.user_id == current_user.id
                )
                .first()
            )
            
            if not assignment:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not authorized to access this project"
                )
        
        return project
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get project: {str(e)}"
        )

@router.post("/{project_id}/assign/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def assign_user_to_project(
    project_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Assign a user to a project (admin only)"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can assign users to projects"
        )
    
    try:
        # Check if project exists
        project = db.query(Project).filter(Project.id == project_id).first()
        
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
        
        # Check if user exists
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Check if assignment already exists
        assignment = (
            db.query(ProjectAssignment)
            .filter(
                ProjectAssignment.project_id == project_id,
                ProjectAssignment.user_id == user_id
            )
            .first()
        )
        
        if assignment:
            return  # Already assigned
        
        # Create assignment
        assignment = ProjectAssignment(project_id=project_id, user_id=user_id)
        db.add(assignment)
        db.commit()
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to assign user to project: {str(e)}"
        )

@router.delete("/{project_id}/assign/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_user_from_project(
    project_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Remove a user from a project (admin only)"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can remove users from projects"
        )
    
    try:
        # Find assignment
        assignment = (
            db.query(ProjectAssignment)
            .filter(
                ProjectAssignment.project_id == project_id,
                ProjectAssignment.user_id == user_id
            )
            .first()
        )
        
        if assignment:
            db.delete(assignment)
            db.commit()
            
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove user from project: {str(e)}"
        )

@router.get("/{project_id}/users", response_model=List[UserSchema])
async def get_project_users(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all users assigned to a project"""
    try:
        # First check if project exists and user has access
        project = db.query(Project).filter(Project.id == project_id).first()
        
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
        
        # Check access if not admin
        if not current_user.is_admin:
            assignment = (
                db.query(ProjectAssignment)
                .filter(
                    ProjectAssignment.project_id == project_id,
                    ProjectAssignment.user_id == current_user.id
                )
                .first()
            )
            
            if not assignment:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not authorized to access this project"
                )
        
        # Get all users assigned to the project
        users = (
            db.query(User)
            .join(ProjectAssignment)
            .filter(ProjectAssignment.project_id == project_id)
            .all()
        )
        
        return users
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get project users: {str(e)}"
        )

# === Chat Room and Message Endpoints (Moved from chat.py) ===

# Note: Using the existing 'router' instance from projects.py
# The prefix from chat.py was /projects/{project_id}/chat-rooms

@router.get("/{project_id}/chat-rooms", response_model=List[ChatRoomSchema], tags=["chat rooms"])
def get_project_chat_rooms(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all chat rooms the user has access to within a project"""
    # Verify project exists and user has access
    project_query = db.query(Project).filter(Project.id == project_id)
    if not current_user.is_admin:
        project_query = project_query.filter(Project.assignments.any(user_id=current_user.id))
    
    project = project_query.first()
    
    if not project:
         # Re-check existence without access constraint for 404 vs 403
        project_exists = db.query(Project.id).filter(Project.id == project_id).first()
        if not project_exists:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
        else:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this project")

    # Get all chat rooms in the project
    chat_rooms = db.query(ChatRoom).filter(
        ChatRoom.project_id == project_id
    ).all()
    
    return chat_rooms

@router.get("/{project_id}/chat-rooms/{room_id}", response_model=ChatRoomSchema, tags=["chat rooms"])
def get_chat_room(
    project_id: int,
    room_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific chat room in a project if the user has access"""
    # Verify project exists and user has access (using the same logic as get_project_chat_rooms)
    project_query = db.query(Project).filter(Project.id == project_id)
    if not current_user.is_admin:
        project_query = project_query.filter(Project.assignments.any(user_id=current_user.id))
    
    project = project_query.first()

    if not project:
        project_exists = db.query(Project.id).filter(Project.id == project_id).first()
        if not project_exists:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
        else:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this project")

    # Get the chat room
    chat_room = db.query(ChatRoom).filter(
        ChatRoom.id == room_id,
        ChatRoom.project_id == project_id # Ensure room belongs to the specified project path
    ).first()
    
    if not chat_room:
        raise HTTPException(status_code=404, detail=f"Chat room with id {room_id} not found in project {project_id}")
    
    return chat_room

@router.get("/{project_id}/chat-rooms/{room_id}/messages", response_model=List[ChatMessageSchema], tags=["chat rooms"])
def get_chat_messages(
    project_id: int,
    room_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get messages from a specific chat room if the user has access to the project"""
    # Verify project exists and user has access (checks access to project first)
    project_query = db.query(Project).filter(Project.id == project_id)
    if not current_user.is_admin:
        project_query = project_query.filter(Project.assignments.any(user_id=current_user.id))
    
    project = project_query.first()

    if not project:
        project_exists = db.query(Project.id).filter(Project.id == project_id).first()
        if not project_exists:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
        else:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this project")

    # Get the chat room (verify it belongs to the project)
    chat_room = db.query(ChatRoom.id).filter(
        ChatRoom.id == room_id,
        ChatRoom.project_id == project_id
    ).first()
    
    if not chat_room:
        raise HTTPException(status_code=404, detail=f"Chat room with id {room_id} not found in project {project_id}")
    
    # Get messages from the specific chat room
    messages = db.query(ChatMessage).filter(
        ChatMessage.chat_room_id == room_id
    ).order_by(ChatMessage.created_at).offset(skip).limit(limit).all() # Added ordering
    
    return messages 

@router.get("/{project_id}/chat-rooms/{room_id}/annotations", response_model=List[AnnotationSchema], tags=["annotations"])
def get_chat_room_annotations(
    project_id: int,
    room_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(verify_project_access)
):
    """
    Get annotations for a specific chat room within a project.
    PHASE 1 SECURITY: Annotators see only their own annotations, admins see all.
    """
    # Dependency takes care of project access.
    # We still need to verify the chat room belongs to the project.
    chat_room = db.query(ChatRoom).filter(
        ChatRoom.id == room_id,
        ChatRoom.project_id == project_id
    ).first()

    if not chat_room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat room not found in this project"
        )

    # PILLAR 1: Isolate annotations based on user role
    if current_user.is_admin:
        # Admins can see ALL annotations
        annotations_data = crud.get_all_annotations_for_chat_room_admin(db, chat_room_id=room_id)
    else:
        # Annotators can ONLY see their own annotations
        annotations_data = crud.get_annotations_for_chat_room_by_annotator(
            db, chat_room_id=room_id, annotator_id=current_user.id
        )

    # Manually construct the response to match the schema
    result = []
    for annotation, annotator_email in annotations_data:
        annotation_dict = annotation.__dict__
        annotation_dict['annotator_email'] = annotator_email
        result.append(annotation_dict)

    return result 

@router.get(
    "/{project_id}/chat-rooms/{room_id}/completion",
    response_model=ChatRoomCompletionSchema,
    tags=["chat rooms"]
)
def get_chat_room_completion(
    project_id: int,
    room_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(verify_project_access)
):
    chat_room = db.query(ChatRoom).filter(
        ChatRoom.id == room_id,
        ChatRoom.project_id == project_id
    ).first()
    if not chat_room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat room not found in this project"
        )

    completion = crud.get_chat_room_completion(db, room_id, current_user.id)
    if completion:
        return completion

    return ChatRoomCompletionSchema(
        chat_room_id=room_id,
        annotator_id=current_user.id,
        project_id=project_id,
        is_completed=False,
        updated_at=None
    )

@router.put(
    "/{project_id}/chat-rooms/{room_id}/completion",
    response_model=ChatRoomCompletionSchema,
    tags=["chat rooms"]
)
def update_chat_room_completion(
    project_id: int,
    room_id: int,
    payload: ChatRoomCompletionUpdateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(verify_project_access)
):
    chat_room = db.query(ChatRoom).filter(
        ChatRoom.id == room_id,
        ChatRoom.project_id == project_id
    ).first()
    if not chat_room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat room not found in this project"
        )

    completion = crud.upsert_chat_room_completion(
        db=db,
        chat_room_id=room_id,
        project_id=project_id,
        annotator_id=current_user.id,
        is_completed=payload.is_completed
    )
    return completion
