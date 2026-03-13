"""
Data Transformer for Excel Chat Room Data

This module transforms parsed Excel data into formats compatible with the annotation API.
"""

import re
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class ChatRoomCreate:
    """Schema for creating a chat room."""
    name: str
    description: Optional[str] = None
    project_id: Optional[int] = None


@dataclass
class ChatMessage:
    """Schema for chat messages."""
    turn_id: str
    user_id: str
    turn_text: str
    reply_to_turn: Optional[str] = None


@dataclass
class AnnotationCreate:
    """Schema for creating annotations."""
    turn_id: str
    thread_id: str


@dataclass
class UserCreate:
    """Schema for creating users."""
    username: str
    name: str
    password: str = "password"
    is_admin: bool = False


class ChatRoomDataTransformer:
    """
    Transforms Excel data into API-compatible format.
    
    Handles conversion of parsed Excel data to Pydantic-like schemas
    that can be used with the annotation API.
    """
    
    def __init__(self, min_username_length: int = 3):
        """
        Initialize the transformer.
        
        Args:
            min_username_length: Minimum username length to enforce
        """
        self.min_username_length = max(3, min_username_length)
    
    def generate_username(self, annotator_name: str) -> str:
        """
        Generate a username from annotator name.
        
        Args:
            annotator_name: Name of the annotator
            
        Returns:
            Generated username
        """
        # Clean the name: remove special characters, convert to lowercase
        clean_name = re.sub(r'[^a-zA-Z0-9]', '', annotator_name.lower())
        
        # Ensure minimum length
        if len(clean_name) < self.min_username_length:
            suffix = abs(hash(annotator_name)) % 10000
            clean_name = f"user{suffix}"
            if len(clean_name) < self.min_username_length:
                clean_name = "user"
        
        return clean_name
    
    def generate_user_display_name(self, annotator_name: str) -> str:
        """
        Generate display name from annotator name.
        
        Args:
            annotator_name: Name of the annotator
            
        Returns:
            Cleaned display name
        """
        # Capitalize first letter of each word
        return ' '.join(word.capitalize() for word in annotator_name.split())
    
    def excel_to_chat_room_schema(self, excel_data: Dict[str, Any], project_id: int) -> ChatRoomCreate:
        """
        Convert Excel chat room data to ChatRoomCreate schema.
        
        Args:
            excel_data: Parsed Excel data from a sheet
            project_id: ID of the project to assign the chat room to
            
        Returns:
            ChatRoomCreate schema
        """
        chat_room_data = excel_data['chat_room_data']
        
        return ChatRoomCreate(
            name=chat_room_data['name'],
            description=chat_room_data['description'],
            project_id=project_id
        )
    
    def excel_to_chat_messages_schema(self, excel_data: Dict[str, Any]) -> List[ChatMessage]:
        """
        Convert Excel messages data to ChatMessage schemas.
        
        Args:
            excel_data: Parsed Excel data from a sheet
            
        Returns:
            List of ChatMessage schemas
        """
        messages_data = excel_data['messages_data']
        messages = []
        
        for msg_data in messages_data:
            message = ChatMessage(
                turn_id=msg_data['turn_id'],
                user_id=msg_data['user_id'],
                turn_text=msg_data['turn_text'],
                reply_to_turn=msg_data['reply_to_turn']
            )
            messages.append(message)
        
        return messages
    
    def excel_to_annotations_schema(self, excel_data: Dict[str, Any]) -> List[AnnotationCreate]:
        """
        Convert Excel annotations data to AnnotationCreate schemas.
        
        Args:
            excel_data: Parsed Excel data from a sheet
            
        Returns:
            List of AnnotationCreate schemas
        """
        annotations_data = excel_data['annotations_data']
        annotations = []
        
        for ann_data in annotations_data:
            annotation = AnnotationCreate(
                turn_id=ann_data['turn_id'],
                thread_id=ann_data['thread_id']
            )
            annotations.append(annotation)
        
        return annotations
    
    def excel_to_user_schema(self, annotator_name: str) -> UserCreate:
        """
        Convert annotator name to UserCreate schema.
        
        Args:
            annotator_name: Name of the annotator
            
        Returns:
            UserCreate schema
        """
        return UserCreate(
            username=self.generate_username(annotator_name),
            name=self.generate_user_display_name(annotator_name),
            password="password",  # Simple default password for testing
            is_admin=False
        )
    
    def create_chat_room_name(self, base_name: str, annotators: List[str]) -> str:
        """
        Create a simple chat room name using just the base name.
        
        Args:
            base_name: Base name from Excel file
            annotators: List of annotator names (not used, kept for compatibility)
            
        Returns:
            Clean chat room name (just the base name)
        """
        # Simply return the base name without any suffixes
        return base_name
    
    def prepare_chat_room_import_data(self, 
                                      sheets_data: Dict[str, Dict[str, Any]], 
                                      project_id: int) -> Dict[str, Any]:
        """
        Prepare complete import data for a chat room from multiple sheets.
        
        Args:
            sheets_data: Dictionary of parsed sheet data
            project_id: ID of the project
            
        Returns:
            Complete import data structure
        """
        if not sheets_data:
            raise ValueError("No sheet data provided")
        
        # Get base information from first sheet
        first_sheet = next(iter(sheets_data.values()))
        base_name = first_sheet['chat_room_data']['base_name']
        
        # Collect all annotators
        annotators = []
        for sheet_data in sheets_data.values():
            annotator = sheet_data['annotator_name']
            if annotator not in annotators:
                annotators.append(annotator)
        
        # Create chat room schema
        chat_room_name = self.create_chat_room_name(base_name, annotators)
        chat_room = ChatRoomCreate(
            name=chat_room_name,
            description=f"Chat room imported from Excel with annotations from: {', '.join(annotators)}",
            project_id=project_id
        )
        
        # Get messages from first sheet (they should be the same across all sheets)
        messages = self.excel_to_chat_messages_schema(first_sheet)
        
        # Collect all users and annotations
        users = []
        annotations_by_user = {}
        
        for sheet_data in sheets_data.values():
            annotator_name = sheet_data['annotator_name']
            
            # Create user
            user = self.excel_to_user_schema(annotator_name)
            users.append(user)
            
            # Get annotations for this user
            annotations = self.excel_to_annotations_schema(sheet_data)
            annotations_by_user[user.username] = annotations
        
        return {
            "chat_room": chat_room,
            "messages": messages,
            "users": users,
            "annotations_by_user": annotations_by_user,
            "annotators": annotators,
            "base_name": base_name,
            "total_messages": len(messages),
            "total_annotations": sum(len(anns) for anns in annotations_by_user.values())
        }
    
    def convert_to_api_format(self, data: Any) -> Dict[str, Any]:
        """
        Convert data objects to dictionary format for API calls.
        
        Args:
            data: Data object to convert
            
        Returns:
            Dictionary representation
        """
        if hasattr(data, '__dict__'):
            return {k: v for k, v in data.__dict__.items() if v is not None}
        elif isinstance(data, list):
            return [self.convert_to_api_format(item) for item in data]
        elif isinstance(data, dict):
            return {k: self.convert_to_api_format(v) for k, v in data.items()}
        else:
            return data
    
    def prepare_csv_import_data(self, messages: List[ChatMessage]) -> str:
        """
        Convert messages to CSV format for API import.
        
        Args:
            messages: List of ChatMessage objects
            
        Returns:
            CSV string
        """
        import io
        import csv
        
        output = io.StringIO()
        writer = csv.writer(output, delimiter=',')  # Use comma delimiter, not semicolon
        
        # Write header
        writer.writerow(['user_id', 'turn_id', 'turn_text', 'reply_to_turn'])
        
        # Write messages
        for message in messages:
            writer.writerow([
                message.user_id,
                message.turn_id,
                message.turn_text,
                message.reply_to_turn or ''
            ])
        
        return output.getvalue()
    
    def prepare_annotations_import_data(self, annotations: List[AnnotationCreate]) -> str:
        """
        Convert annotations to CSV format for API import.
        
        Args:
            annotations: List of AnnotationCreate objects
            
        Returns:
            CSV string
        """
        import io
        import csv
        
        output = io.StringIO()
        writer = csv.writer(output, delimiter=',')  # Use comma delimiter, not semicolon
        
        # Write header
        writer.writerow(['turn_id', 'thread_id'])
        
        # Write annotations
        for annotation in annotations:
            writer.writerow([
                annotation.turn_id,
                annotation.thread_id
            ])
        
        return output.getvalue()
    
    def validate_import_data(self, import_data: Dict[str, Any]) -> List[str]:
        """
        Validate the prepared import data.
        
        Args:
            import_data: Prepared import data
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        # Check required fields
        required_fields = ['chat_room', 'messages', 'users', 'annotations_by_user']
        for field in required_fields:
            if field not in import_data:
                errors.append(f"Missing required field: {field}")
        
        if errors:
            return errors
        
        # Validate chat room
        chat_room = import_data['chat_room']
        if not chat_room.name:
            errors.append("Chat room name is required")
        
        # Validate messages
        messages = import_data['messages']
        if not messages:
            errors.append("At least one message is required")
        
        turn_ids = set()
        for message in messages:
            if not message.turn_id:
                errors.append("All messages must have turn_id")
            elif message.turn_id in turn_ids:
                errors.append(f"Duplicate turn_id: {message.turn_id}")
            else:
                turn_ids.add(message.turn_id)
        
        # Validate users
        users = import_data['users']
        if not users:
            errors.append("At least one user is required")
        
        usernames = set()
        for user in users:
            if not user.username:
                errors.append("All users must have username")
            elif user.username in usernames:
                errors.append(f"Duplicate username: {user.username}")
            else:
                usernames.add(user.username)
        
        # Validate annotations
        annotations_by_user = import_data['annotations_by_user']
        for username, annotations in annotations_by_user.items():
            for annotation in annotations:
                if not annotation.turn_id:
                    errors.append(f"Invalid annotation for {username}: missing turn_id")
                elif annotation.turn_id not in turn_ids:
                    errors.append(f"Invalid annotation for {username}: turn_id '{annotation.turn_id}' not found in messages")
                
                if not annotation.thread_id:
                    errors.append(f"Invalid annotation for {username}: missing thread_id")
        
        return errors
    
    def generate_import_summary(self, import_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a summary of the import data.
        
        Args:
            import_data: Prepared import data
            
        Returns:
            Summary dictionary
        """
        total_annotations = sum(len(anns) for anns in import_data['annotations_by_user'].values())
        
        # Calculate annotation statistics
        annotation_stats = {}
        for username, annotations in import_data['annotations_by_user'].items():
            thread_counts = {}
            for annotation in annotations:
                thread_id = annotation.thread_id
                thread_counts[thread_id] = thread_counts.get(thread_id, 0) + 1
            annotation_stats[username] = {
                "total_annotations": len(annotations),
                "unique_threads": len(thread_counts),
                "thread_distribution": thread_counts
            }
        
        return {
            "chat_room_name": import_data['chat_room'].name,
            "base_name": import_data['base_name'],
            "total_users": len(import_data['users']),
            "total_messages": len(import_data['messages']),
            "total_annotations": total_annotations,
            "users": [user.username for user in import_data['users']],
            "annotation_stats": annotation_stats
        } 
