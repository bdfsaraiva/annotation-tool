"""
API Client for Annotation System

This module provides a client for interacting with the annotation API,
handling authentication, user management, and data import operations.
"""

import requests
import time
import tempfile
import os
from typing import Dict, List, Any, Optional, Tuple
from urllib.parse import urljoin
import logging

logger = logging.getLogger(__name__)


class APIError(Exception):
    """Custom exception for API errors."""
    pass


class AnnotationAPIClient:
    """
    Client for interacting with the annotation API.
    
    Handles authentication, user management, chat room operations,
    and data import functionality.
    """
    
    def __init__(self, base_url: str, admin_username: str, admin_password: str, timeout: int = 30):
        """
        Initialize the API client.
        
        Args:
            base_url: Base URL of the API
            admin_username: Admin username for authentication
            admin_password: Admin password for authentication
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.admin_username = admin_username
        self.admin_password = admin_password
        self.timeout = timeout
        self.access_token = None
        self.current_project_id = None
        self.session = requests.Session()
        
        # Set default headers
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """
        Make an HTTP request with error handling.
        
        Args:
            method: HTTP method
            endpoint: API endpoint
            **kwargs: Additional arguments for requests
            
        Returns:
            Response object
            
        Raises:
            APIError: If request fails
        """
        url = urljoin(self.base_url, endpoint)
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                timeout=self.timeout,
                **kwargs
            )
        except requests.exceptions.ConnectionError:
            raise APIError(f"Cannot connect to API at {self.base_url}")
        except requests.exceptions.Timeout:
            raise APIError(f"Request timed out after {self.timeout} seconds")
        except requests.exceptions.RequestException as e:
            raise APIError(f"Request failed: {str(e)}")
        
        return response
    
    def check_health(self) -> bool:
        """
        Check if the API is healthy and reachable.
        
        Returns:
            True if API is healthy
            
        Raises:
            APIError: If API is not reachable
        """
        try:
            response = self._make_request('GET', '/')
            if response.status_code == 200:
                logger.info(f"API is healthy at {self.base_url}")
                return True
            else:
                raise APIError(f"API health check failed with status {response.status_code}")
        except Exception as e:
            logger.error(f"API health check failed: {e}")
            raise
    
    def authenticate(self) -> str:
        """
        Authenticate with the API and get access token.
        
        Returns:
            Access token
            
        Raises:
            APIError: If authentication fails
        """
        login_data = {
            "username": self.admin_username,
            "password": self.admin_password
        }
        
        try:
            # Use form data (not JSON) for OAuth2PasswordRequestForm
            # Override the session's default JSON content-type for this request
            headers = {'Content-Type': 'application/x-www-form-urlencoded'}
            response = self.session.post(
                f"{self.base_url}/auth/token",
                data=login_data,  # Form data, not JSON
                headers=headers,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data['access_token']
                
                # Update session headers with token
                self.session.headers.update({
                    'Authorization': f'Bearer {self.access_token}'
                })
                
                logger.info(f"Successfully authenticated as {self.admin_username}")
                return self.access_token
            else:
                raise APIError(f"Authentication failed: {response.text}")
                
        except APIError:
            raise
        except Exception as e:
            raise APIError(f"Authentication error: {str(e)}")
    
    def create_or_get_user(self, username: str, name: str, password: str = "ChangeMe123!") -> int:
        """
        Create a new user or get existing user ID.
        
        Args:
            username: Username
            name: User display name
            password: User password (default temporary password)
            
        Returns:
            User ID
            
        Raises:
            APIError: If operation fails
        """
        # First, try to get existing user
        try:
            response = self._make_request('GET', '/admin/users')
            if response.status_code == 200:
                users = response.json()
                for user in users:
                    if user['username'] == username:
                        logger.info(f"User already exists: {username} (ID: {user['id']})")
                        return user['id']
        except Exception:
            pass  # Continue to create user
        
        # Create new user
        user_data = {
            "username": username,
            "password": password,
            "is_admin": False
        }
        
        try:
            response = self._make_request('POST', '/admin/users', json=user_data)
            
            if response.status_code in [200, 201]:
                user = response.json()
                user_id = user['id']
                logger.info(f"Created user: {username} (ID: {user_id})")
                return user_id
            else:
                raise APIError(f"Failed to create user {username}: {response.text}")
                
        except APIError:
            raise
        except Exception as e:
            raise APIError(f"Error creating user {username}: {str(e)}")
    
    def assign_user_to_project(self, project_id: int, user_id: int) -> bool:
        """
        Assign a user to a project.
        
        Args:
            project_id: Project ID
            user_id: User ID
            
        Returns:
            True if successful
            
        Raises:
            APIError: If operation fails
        """
        try:
            response = self._make_request('POST', f'/projects/{project_id}/assign/{user_id}')
            
            if response.status_code in [200, 201, 204]:
                logger.info(f"Assigned user {user_id} to project {project_id}")
                return True
            else:
                # Check if already assigned
                if response.status_code == 400 and "already assigned" in response.text.lower():
                    logger.info(f"User {user_id} already assigned to project {project_id}")
                    return True
                else:
                    raise APIError(f"Failed to assign user to project: {response.text}")
                    
        except APIError:
            raise
        except Exception as e:
            raise APIError(f"Error assigning user {user_id} to project {project_id}: {str(e)}")
    
    def create_chat_room_and_import_messages(self, project_id: int, name: str, messages_csv: str) -> Dict[str, Any]:
        """
        Create a chat room and import messages in one operation.
        
        Args:
            project_id: Project ID
            name: Chat room name
            messages_csv: CSV data containing messages
            
        Returns:
            Combined result with chat room info and import details
            
        Raises:
            APIError: If operation fails
        """
        # Create temporary file in binary mode to avoid encoding issues
        with tempfile.NamedTemporaryFile(mode='w+b', suffix='.csv', delete=False) as f:
            f.write(messages_csv.encode('utf-8'))
            temp_file_path = f.name
        
        try:
            # Re-open the file to be sent
            with open(temp_file_path, 'rb') as f_to_send:
                files = {'file': (f'{name}.csv', f_to_send, 'text/csv')}
                
                # Create completely fresh headers with only Authorization
                # DO NOT use session headers which contain Content-Type: application/json
                headers = {
                    'Authorization': self.session.headers.get('Authorization')
                }
                
                url = f"{self.base_url}/admin/projects/{project_id}/import-chat-room-csv"
                
                # Use requests.post directly instead of session.post to avoid header pollution
                response = requests.post(
                    url,
                    files=files,
                    headers=headers,
                    timeout=self.timeout
                )
                
                if response.status_code in [200, 201]:
                    result = response.json()
                    chat_room_id = result['chat_room']['id']
                    logger.info(f"Created chat room and imported messages: {name} (ID: {chat_room_id})")
                    return result
                else:
                    raise APIError(f"Failed to create chat room and import messages for {name}: {response.text}")
                    
        except APIError:
            raise
        except Exception as e:
            raise APIError(f"Error creating chat room and importing messages for {name}: {str(e)}")
        finally:
            # Clean up temporary file
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
    
    def import_chat_messages(self, chat_room_id: int, messages_csv: str) -> Dict[str, Any]:
        """
        Import chat messages from CSV data.
        
        Args:
            chat_room_id: Chat room ID
            messages_csv: CSV data containing messages
            
        Returns:
            Import result
            
        Raises:
            APIError: If import fails
        """
        # Create temporary file in binary mode to avoid encoding issues
        with tempfile.NamedTemporaryFile(mode='w+b', suffix='.csv', delete=False) as f:
            f.write(messages_csv.encode('utf-8'))
            temp_file_path = f.name
        
        try:
            with open(temp_file_path, 'rb') as f_to_send:
                files = {'file': ('messages.csv', f_to_send, 'text/csv')}
                
                # Create completely fresh headers with only Authorization
                headers = {
                    'Authorization': self.session.headers.get('Authorization')
                }

                # Use requests.post directly to avoid header pollution
                response = requests.post(
                    f'{self.base_url}/admin/chat-rooms/{chat_room_id}/import-csv',
                    files=files,
                    headers=headers,
                    timeout=self.timeout
                )
                
                if response.status_code in [200, 201]:
                    result = response.json()
                    logger.info(f"Imported {result.get('imported_count', 0)} messages to chat room {chat_room_id}")
                    return result
                else:
                    raise APIError(f"Failed to import messages: {response.text}")
                    
        except APIError:
            raise
        except Exception as e:
            raise APIError(f"Error importing messages: {str(e)}")
        finally:
            # Clean up temporary file
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
    
    def import_annotations(self, chat_room_id: int, user_id: int, annotations_csv: str) -> Dict[str, Any]:
        """
        Import annotations from CSV data.
        
        Args:
            chat_room_id: Chat room ID
            user_id: User ID of the annotator
            annotations_csv: CSV data containing annotations
            
        Returns:
            Import result
            
        Raises:
            APIError: If import fails
        """
        # Create temporary file in binary mode to avoid encoding issues
        with tempfile.NamedTemporaryFile(mode='w+b', suffix='.csv', delete=False) as f:
            f.write(annotations_csv.encode('utf-8'))
            temp_file_path = f.name
        
        try:
            with open(temp_file_path, 'rb') as f_to_send:
                files = {'file': ('annotations.csv', f_to_send, 'text/csv')}
                data = {'user_id': str(user_id)}
                
                # Create completely fresh headers with only Authorization
                headers = {
                    'Authorization': self.session.headers.get('Authorization')
                }
                
                # Use requests.post directly to avoid header pollution
                response = requests.post(
                    f'{self.base_url}/admin/chat-rooms/{chat_room_id}/import-annotations',
                    files=files,
                    data=data,
                    headers=headers,
                    timeout=self.timeout
                )
                
                if response.status_code in [200, 201]:
                    result = response.json()
                    logger.info(f"Imported {result.get('imported_count', 0)} annotations for user {user_id}")
                    return result
                else:
                    raise APIError(f"Failed to import annotations: {response.text}")
                    
        except APIError:
            raise
        except Exception as e:
            raise APIError(f"Error importing annotations: {str(e)}")
        finally:
            # Clean up temporary file
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
    
    def get_projects(self) -> List[Dict[str, Any]]:
        """
        Get list of all projects.
        
        Returns:
            List of projects
            
        Raises:
            APIError: If operation fails
        """
        try:
            response = self._make_request('GET', '/admin/projects')
            
            if response.status_code == 200:
                projects = response.json()
                logger.info(f"Retrieved {len(projects)} projects")
                return projects
            else:
                raise APIError(f"Failed to get projects: {response.text}")
                
        except APIError:
            raise
        except Exception as e:
            raise APIError(f"Error getting projects: {str(e)}")
    
    def get_project(self, project_id: int) -> Dict[str, Any]:
        """
        Get project details.
        
        Args:
            project_id: Project ID
            
        Returns:
            Project details
            
        Raises:
            APIError: If operation fails
        """
        try:
            response = self._make_request('GET', f'/admin/projects/{project_id}')
            
            if response.status_code == 200:
                project = response.json()
                logger.info(f"Retrieved project: {project['name']} (ID: {project_id})")
                return project
            elif response.status_code == 404:
                raise APIError(f"Project {project_id} not found")
            else:
                raise APIError(f"Failed to get project {project_id}: {response.text}")
                
        except APIError:
            raise
        except Exception as e:
            raise APIError(f"Error getting project {project_id}: {str(e)}")
    
    def validate_project_access(self, project_id: int) -> bool:
        """
        Validate that we have access to a project.
        Creates a default project if it doesn't exist.
        
        Args:
            project_id: Project ID to validate
            
        Returns:
            True if we have access
            
        Raises:
            APIError: If we don't have access or project creation fails
        """
        try:
            self.get_project(project_id)
            return True
        except APIError as e:
            if "not found" in str(e):
                # Project doesn't exist, create a default one
                logger.info(f"Project {project_id} does not exist, creating default project...")
                project = self.create_default_project()
                # Update the project_id to use the newly created project
                self.current_project_id = project['id']
                logger.info(f"Using newly created project ID: {self.current_project_id}")
                return True
            else:
                raise APIError(f"No access to project {project_id}")

    def create_project(self, name: str, description: str = "") -> Dict[str, Any]:
        """
        Create a new project with custom name and description.
        
        Args:
            name: Project name
            description: Project description
            
        Returns:
            Created project details
            
        Raises:
            APIError: If project creation fails
        """
        project_data = {
            "name": name,
            "description": description
        }
        
        try:
            logger.debug(f"Creating project with data: {project_data}")
            response = self._make_request('POST', '/admin/projects', json=project_data)
            
            logger.debug(f"Project creation response status: {response.status_code}")
            logger.debug(f"Project creation response text: {response.text}")
            
            if response.status_code in [200, 201]:
                project = response.json()
                project_id = project['id']
                self.current_project_id = project_id
                logger.info(f"Created project: {project['name']} (ID: {project_id})")
                return project
            else:
                error_detail = f"Status {response.status_code}: {response.text}"
                raise APIError(f"Failed to create project: {error_detail}")
                
        except APIError:
            raise
        except Exception as e:
            raise APIError(f"Project creation error: {str(e)}")
    
    def create_default_project(self) -> Dict[str, Any]:
        """
        Create a default project.
        
        Returns:
            Project data
            
        Raises:
            APIError: If project creation fails
        """
        return self.create_project(
            name="Excel Import Project",
            description="Default project for Excel annotation imports"
        )
    
    def wait_for_api(self, max_attempts: int = 10, wait_time: int = 5) -> bool:
        """
        Wait for API to become available.
        
        Args:
            max_attempts: Maximum number of attempts
            wait_time: Time to wait between attempts
            
        Returns:
            True if API becomes available
            
        Raises:
            APIError: If API doesn't become available
        """
        for attempt in range(max_attempts):
            try:
                self.check_health()
                return True
            except APIError:
                if attempt < max_attempts - 1:
                    logger.info(f"API not available, waiting {wait_time}s... (attempt {attempt + 1}/{max_attempts})")
                    time.sleep(wait_time)
                else:
                    raise APIError(f"API not available after {max_attempts} attempts")
        
        return False
    
    def batch_create_users(self, users_data: List[Dict[str, str]]) -> Dict[str, int]:
        """
        Create multiple users and return username -> user_id mapping.
        
        Args:
            users_data: List of user data dictionaries
            
        Returns:
            Dictionary mapping username to user ID
        """
        user_mapping = {}
        
        for user_data in users_data:
            try:
                user_id = self.create_or_get_user(
                    username=user_data['username'],
                    name=user_data['name'],
                    password=user_data.get('password', "ChangeMe123!")
                )
                user_mapping[user_data['username']] = user_id
            except APIError as e:
                logger.error(f"Failed to create user {user_data['username']}: {e}")
                # Continue with other users
                continue
        
        return user_mapping
    
    def batch_assign_users_to_project(self, project_id: int, user_ids: List[int]) -> List[int]:
        """
        Assign multiple users to a project.
        
        Args:
            project_id: Project ID
            user_ids: List of user IDs
            
        Returns:
            List of successfully assigned user IDs
        """
        assigned_users = []
        
        for user_id in user_ids:
            try:
                if self.assign_user_to_project(project_id, user_id):
                    assigned_users.append(user_id)
            except APIError as e:
                logger.error(f"Failed to assign user {user_id} to project {project_id}: {e}")
                # Continue with other users
                continue
        
        return assigned_users
    
    def get_import_statistics(self, chat_room_id: int) -> Dict[str, Any]:
        """
        Get statistics about imported data.
        
        Args:
            chat_room_id: Chat room ID
            
        Returns:
            Statistics dictionary
        """
        try:
            # Get chat room details
            response = self._make_request('GET', f'/admin/chat-rooms/{chat_room_id}')
            if response.status_code != 200:
                raise APIError(f"Failed to get chat room details: {response.text}")
            
            chat_room = response.json()
            
            # Get messages count (we'll use a simple approach)
            # This would need to be implemented based on your actual API endpoints
            
            return {
                "chat_room_id": chat_room_id,
                "chat_room_name": chat_room.get('name', ''),
                "status": "imported"
            }
            
        except Exception as e:
            logger.error(f"Failed to get import statistics: {e}")
            return {
                "chat_room_id": chat_room_id,
                "status": "error",
                "error": str(e)
            } 
