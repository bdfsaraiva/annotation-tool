# Annotation API Tests Documentation

This document outlines the successful API tests performed for the annotation functionality, starting from login to annotation retrieval.

## Prerequisites

Before running these tests, ensure you have the following:
- A running instance of the annotation backend (e.g., `http://localhost:8000`)
- User credentials (username/password). The `FIRST_ADMIN_USERNAME` and `FIRST_ADMIN_PASSWORD` from your `.env` can be used initially.
- `jq` installed for formatting JSON responses.
- Environment variables set for subsequent steps (these are typically obtained from previous steps):
  - `ADMIN_TOKEN`: Token obtained after admin login.
  - `USER_TOKEN`: Token obtained after a regular user login (if different from admin).
  - `PROJECT_ID`: ID of the project created or used.
  - `MESSAGE_ID`: ID of a message within the project (e.g., after data import).

## Test Flow

### 1. User Authentication (Login)

**Purpose**: Obtain an authentication token for subsequent API calls.

**Command (Admin Example)**:
```bash
# Replace with your actual admin username and password
ADMIN_USERNAME="admin"
ADMIN_PASSWORD="change-this-password"

# Run the login command and capture the token
ADMIN_TOKEN=$(curl -X POST "http://localhost:8000/auth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=$ADMIN_USERNAME&password=$ADMIN_PASSWORD" | jq -r .access_token)

echo "Admin Token: $ADMIN_TOKEN"
```

**Expected Output**: Prints the obtained access token.

**(Optional) Regular User Login**:
```bash
# Replace with your regular user username and password
USER_USERNAME="user"
USER_PASSWORD="userpassword"

USER_TOKEN=$(curl -X POST "http://localhost:8000/auth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=$USER_USERNAME&password=$USER_PASSWORD" | jq -r .access_token)

echo "User Token: $USER_TOKEN"
```

### 2. Create Project (Admin Required)

**Purpose**: Create a new project to hold annotations.

**Command**:
```bash
# Replace with desired project name and description
PROJECT_NAME="Test Project"
PROJECT_DESC="A project for testing annotations"

# Run the create project command and capture the ID
PROJECT_ID=$(curl -X POST "http://localhost:8000/admin/projects" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "'$PROJECT_NAME'", "description": "'$PROJECT_DESC'"}' | jq .id)

echo "Project ID: $PROJECT_ID"
```

**Expected Response**: Prints the ID of the newly created project.

### 3. Import Chat Data (Admin Required)

**Purpose**: Import chat messages from a CSV file into a specific project. This creates the messages that can then be annotated.

**Command**:
```bash
# Replace 'path/to/your/chat_data.csv' with the actual file path
CSV_FILE_PATH="path/to/your/chat_data.csv"

curl -X POST "http://localhost:8000/admin/projects/$PROJECT_ID/import-chat-room-csv" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -F "file=@$CSV_FILE_PATH" | jq
```

**Expected Response**: A JSON object containing details about the created chat room and the import process (counts, errors, warnings).
```json
{
  "chat_room": {
    "name": "chat_data", // Based on CSV filename
    "description": null,
    "project_id": /* PROJECT_ID */,
    "id": /* CHAT_ROOM_ID */,
    "created_at": "...",
    "updated_at": "..."
  },
  "import_details": {
    "total_messages": /* number */,
    "imported_count": /* number */,
    "skipped_count": /* number */,
    "errors": [],
    "warnings": []
  }
}
```
**Note**: After this step, you would typically need to identify a specific `MESSAGE_ID` from the imported data (e.g., by querying `/projects/$PROJECT_ID/chat-rooms/{CHAT_ROOM_ID}/messages`) to use in the annotation steps.

### 4. Creating an Annotation

**Purpose**: Create a new annotation for a specific message in a project.

**Command**:
```bash
# Ensure MESSAGE_ID and USER_TOKEN (or ADMIN_TOKEN) are set

curl -X POST "http://localhost:8000/projects/$PROJECT_ID/messages/$MESSAGE_ID/annotations/" \
  -H "Authorization: Bearer $USER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message_id": '$MESSAGE_ID', "thread_id": "Sample Annotation Tag"}' | jq
```

**Expected Response**:
```json
{
  "message_id": /* MESSAGE_ID */,
  "thread_id": "Sample Annotation Tag",
  "id": /* ANNOTATION_ID */,
  "annotator_id": /* USER_ID */,
  "project_id": /* PROJECT_ID */,
  "created_at": "...",
  "updated_at": "..."
}
```

### 5. Retrieving Annotations

**Purpose**: Get all annotations for a specific message in a project.

**Command**:
```bash
# Ensure PROJECT_ID, MESSAGE_ID and USER_TOKEN (or ADMIN_TOKEN) are set

curl -X GET "http://localhost:8000/projects/$PROJECT_ID/messages/$MESSAGE_ID/annotations/" \
  -H "Authorization: Bearer $USER_TOKEN" | jq
```

**Expected Response**:
```json
[
  {
    "message_id": /* MESSAGE_ID */,
    "thread_id": "Sample Annotation Tag",
    "id": /* ANNOTATION_ID */,
    "annotator_id": /* USER_ID */,
    "project_id": /* PROJECT_ID */,
    "created_at": "...",
    "updated_at": "..."
  }
  // ... potentially more annotations
]
```

## Notes

- Replace placeholder values (like usernames, passwords, project names, file paths) with your actual data.
- Use the token obtained from the login step (`ADMIN_TOKEN` or `USER_TOKEN`) for authorized requests.
- The `PROJECT_ID` obtained from project creation is needed for subsequent project-specific calls.
- The `MESSAGE_ID` needs to be identified after data import before creating annotations.
- Responses are formatted using `jq` for better readability.
- The API follows RESTful conventions with proper HTTP methods. 
