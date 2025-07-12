# REST API

The storyteller web service provides a REST API for creating and managing interactive stories with JWT authentication.

## Authentication

All API endpoints require authentication using Auth0 JWT Bearer tokens with the `storyteller:use` scope.

### Authorization Header
Include the JWT token in the Authorization header:
```
Authorization: Bearer <your-jwt-token>
```

### Getting a Token
Obtain a JWT token from your Auth0 application configured for the Storyteller API audience.

## Command-Line Model Selection

The REST API service requires specifying an AI provider when starting:

```bash
# Start with OpenAI
python webservice.py -p openai

# Start with specific OpenAI model
python webservice.py -p openai -m gpt-4
```

### Available Options

- `-p, --provider PROVIDER` - AI provider to use (openai, anthropic, xai, google, ollama) **[Required]**
- `-m, --model MODEL_NAME` - Specify the model name to use (optional, uses provider default)

## Base URL

By default, the API is available at `http://localhost:8000` (configurable via `HTTP_HOST` and `HTTP_PORT` environment variables).

## Endpoints

### Create Story

**POST** `/stories`

Creates a new empty story and returns the complete story object with UUID.

**Headers:**
```
Authorization: Bearer <jwt-token>
Content-Type: application/json
```

**Response:**
- Status: 201 Created
- Headers: `Location: /stories/{story_uuid}`
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "characters": [],
  "chapters": [],
  "scenes": [],
  "old_messages": [],
  "current_messages": []
}
```

### Generate Characters

**POST** `/characters/generate`

Generates characters based on a text prompt using AI.

**Headers:**
```
Authorization: Bearer <jwt-token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "prompt": "A brave knight named Sir Galahad who seeks the Holy Grail. A wise wizard named Merlin who guides heroes on their quests."
}
```

**Response:**
```json
{
  "characters": [
    {
      "name": "Sir Galahad",
      "description": "A brave knight who seeks the Holy Grail"
    },
    {
      "name": "Merlin",
      "description": "A wise wizard who guides heroes on their quests"
    }
  ]
}
```

### Get Story

**GET** `/stories/{story_uuid}`

Retrieves the complete story state including characters, chapters, scenes, and message history.

**Headers:**
```
Authorization: Bearer <jwt-token>
```

**Response:**
```json
{
  "id": "story_uuid",
  "characters": [...],
  "chapters": [...],
  "scenes": [...],
  "old_messages": [...],
  "current_messages": [...]
}
```

### Execute Command

**POST** `/stories/{story_uuid}`

Executes a command on the specified story.

**Headers:**
```
Authorization: Bearer <jwt-token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "command": "command_name",
  "body": "optional command body"
}
```

**Response:**
```json
{
  "status": "success",
  "messages": [
    "Response messages from the AI and system"
  ]
}
```

## Supported Commands

### chat
Continue the story conversation.
- **Body**: User input/message to add to the story
- **Example**: `{"command": "chat", "body": "I walk into the tavern"}`

### retry
Regenerate the last AI response.
- **Body**: Not used
- **Example**: `{"command": "retry"}`

### rewind
Remove the last message from the story history.
- **Body**: Not used
- **Example**: `{"command": "rewind"}`

### fix
Apply a correction to the last AI response.
- **Body**: Instructions for how to fix the response
- **Example**: `{"command": "fix", "body": "Make the character more friendly"}`

### replace
Replace the last AI response with new text.
- **Body**: New text to replace the last response
- **Example**: `{"command": "replace", "body": "The knight smiled warmly."}`

### chapter
Close the current chapter and start a new one.
- **Body**: Title for the new chapter
- **Example**: `{"command": "chapter", "body": "The Journey Begins"}`

## Error Responses

### 401 Unauthorized
Missing or invalid JWT token:
```json
{
  "detail": "Unauthorized"
}
```

### 403 Forbidden
Valid token but insufficient scope:
```json
{
  "detail": "Insufficient scope"
}
```

### 404 Not Found
Story not found:
```json
{
  "detail": "Story not found"
}
```

### 500 Internal Server Error
Server error:
```json
{
  "detail": "Error message describing what went wrong"
}
```

## Environment Variables

Required for Auth0 integration:
- `AUTH0_DOMAIN` - Your Auth0 domain
- `AUTH0_API_AUDIENCE` - API audience identifier

## Notes

- All commands automatically trigger story summarization to manage context window size
- Stories are persisted to the file system and survive service restarts
- The API uses UUID identifiers for stories to ensure uniqueness
- JWT tokens must include the `storyteller:use` scope to access any endpoint
- Character generation is now a separate endpoint that can be called independently