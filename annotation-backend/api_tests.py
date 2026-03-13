#!/usr/bin/env python3
"""
API Test Script for Inter-Annotator Agreement (IAA) Endpoint

This script provides a centralized way to test the new IAA functionality.
It handles authentication and provides dedicated test functions for different scenarios.

Usage:
    python api_tests.py

Requirements:
    - Backend server running (typically on http://localhost:8000)
    - Admin user credentials
    - Test data in the database
"""

import requests
import json
import sys
from typing import Optional, Dict, Any

# Configuration
BASE_URL = "http://localhost:8000"
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin"

class APITester:
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.access_token: Optional[str] = None
        self.headers: Dict[str, str] = {}
    
    def login(self, username: str, password: str) -> bool:
        """Login and get access token"""
        try:
            response = requests.post(
                f"{self.base_url}/auth/token",
                data={
                    "username": username,
                    "password": password
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data["access_token"]
                self.headers = {
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json"
                }
                print(f"✅ Login successful for {username}")
                return True
            else:
                print(f"❌ Login failed: {response.status_code} - {response.text}")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Login error: {e}")
            return False
    
    def test_iaa_endpoint(self, chat_room_id: int) -> bool:
        """Test the IAA endpoint for a specific chat room"""
        print(f"\n🧪 Testing IAA endpoint for chat room {chat_room_id}")
        
        if not self.access_token:
            print("❌ Not authenticated. Please login first.")
            return False
        
        try:
            response = requests.get(
                f"{self.base_url}/admin/chat-rooms/{chat_room_id}/iaa",
                headers=self.headers
            )
            
            print(f"📊 Response Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print("✅ IAA Analysis successful!")
                print(f"📋 Chat Room: {data['chat_room_name']}")
                print(f"📝 Messages: {data['message_count']}")
                print(f"👥 Annotators: {data['annotator_count']}")
                print(f"✔️ Fully Annotated: {data['is_fully_annotated']}")
                print(f"🔍 Pairwise Accuracies:")
                
                for accuracy in data['pairwise_accuracies']:
                    print(f"   {accuracy['annotator_1_username']} vs {accuracy['annotator_2_username']}: {accuracy['accuracy']:.2f}%")
                
                return True
            
            elif response.status_code == 404:
                print(f"❌ Chat room {chat_room_id} not found")
                return False
            
            elif response.status_code == 400:
                error_data = response.json()
                print(f"❌ Bad request: {error_data.get('detail', 'Unknown error')}")
                return False
            
            elif response.status_code == 403:
                print("❌ Access denied. Admin privileges required.")
                return False
            
            else:
                print(f"❌ Unexpected status code: {response.status_code}")
                print(f"Response: {response.text}")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Request error: {e}")
            return False
        except json.JSONDecodeError as e:
            print(f"❌ JSON decode error: {e}")
            return False
    
    def test_iaa_nonexistent_room(self) -> bool:
        """Test IAA endpoint with non-existent chat room"""
        print(f"\n🧪 Testing IAA endpoint with non-existent chat room")
        
        if not self.access_token:
            print("❌ Not authenticated. Please login first.")
            return False
        
        try:
            response = requests.get(
                f"{self.base_url}/admin/chat-rooms/99999/iaa",
                headers=self.headers
            )
            
            print(f"📊 Response Status: {response.status_code}")
            
            if response.status_code == 404:
                print("✅ Correctly returned 404 for non-existent chat room")
                return True
            else:
                print(f"❌ Expected 404, got {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Request error: {e}")
            return False
    
    def list_chat_rooms(self) -> bool:
        """List available chat rooms to help with testing"""
        print(f"\n📋 Listing available chat rooms")
        
        if not self.access_token:
            print("❌ Not authenticated. Please login first.")
            return False
        
        try:
            # First get projects
            response = requests.get(
                f"{self.base_url}/admin/projects",
                headers=self.headers
            )
            
            if response.status_code != 200:
                print(f"❌ Failed to get projects: {response.status_code}")
                return False
            
            projects = response.json()
            print(f"Found {len(projects)} projects:")
            
            for project in projects:
                print(f"  📁 Project {project['id']}: {project['name']}")
                
                # Get chat rooms for this project
                rooms_response = requests.get(
                    f"{self.base_url}/projects/{project['id']}/chat-rooms",
                    headers=self.headers
                )
                
                if rooms_response.status_code == 200:
                    rooms_data = rooms_response.json()
                    chat_rooms = rooms_data.get('chat_rooms', [])
                    
                    for room in chat_rooms:
                        print(f"    💬 Chat Room {room['id']}: {room['name']}")
                else:
                    print(f"    ❌ Failed to get chat rooms for project {project['id']}")
            
            return True
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Request error: {e}")
            return False
    
    def test_server_connection(self) -> bool:
        """Test if the server is running"""
        print(f"🔗 Testing server connection to {self.base_url}")
        
        try:
            response = requests.get(f"{self.base_url}/docs")
            if response.status_code == 200:
                print("✅ Server is running")
                return True
            else:
                print(f"❌ Server responded with status {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            print(f"❌ Server connection failed: {e}")
            return False


def main():
    """Main test function"""
    print("🚀 Starting IAA API Tests")
    print("=" * 50)
    
    tester = APITester()
    
    # Test server connection
    if not tester.test_server_connection():
        print("❌ Cannot connect to server. Make sure the backend is running.")
        sys.exit(1)
    
    # Login
    if not tester.login(ADMIN_USERNAME, ADMIN_PASSWORD):
        print("❌ Login failed. Check credentials and user existence.")
        sys.exit(1)
    
    # List available chat rooms
    tester.list_chat_rooms()
    
    # Test with non-existent room
    tester.test_iaa_nonexistent_room()
    
    # Test with actual chat room (you'll need to update this with a real chat room ID)
    print("\n" + "=" * 50)
    print("📝 Manual Test Instructions:")
    print("1. Look at the chat rooms listed above")
    print("2. Choose a chat room that has annotations from multiple annotators")
    print("3. Update the chat_room_id in the test call below")
    print("4. Run the test")
    print("=" * 50)
    
    # Example test with chat room ID 1 (update this as needed)
    chat_room_id = 1
    print(f"\n🧪 Testing with chat room ID {chat_room_id}")
    print("⚠️  Update this ID based on your actual data!")
    
    tester.test_iaa_endpoint(chat_room_id)
    
    print("\n" + "=" * 50)
    print("✅ Test suite completed!")
    print("📝 To test with different chat rooms, update the chat_room_id variable and run again.")


if __name__ == "__main__":
    main() 
