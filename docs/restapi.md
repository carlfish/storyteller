# REST API

The storyteller web service provides a REST API for creating and managing interactive stories.

## Command-Line Model Selection

The REST API service requires specifying an AI provider when starting:

```bash
# Start with OpenAI
python webservice.py -p openai

# Start with specific OpenAI model
python webservice.py -p openai -m gpt-4

# Start with Anthropic Claude
python webservice.py -p anthropic -m claude-3-5-sonnet-latest

# Start with XAI Grok
python webservice.py -p xai -m grok-3-latest

# Start with Google Gemini
python webservice.py -p google -m gemini-2.5-flash

# Start with Ollama
python webservice.py -p ollama -m llama2
```

### Available Options

- `-p, --provider PROVIDER` - AI provider to use (openai, anthropic, xai, google, ollama) **[Required]**
- `-m, --model MODEL_NAME` - Specify the model name to use (optional, uses provider default)

## Base URL

By default, the API is available at `http://localhost:8000` (configurable via `HTTP_HOST` and `HTTP_PORT` environment variables).

## Endpoints

### Create Story

**POST** `/stories`

Creates a new story with the provided character descriptions.

**Request Body:**
```json
{
  "characters": "Character descriptions here"
}
```

**Response:**
- Status: 201 Created
- Headers: `Location: /stories/{story_uuid}`
- Body: Empty

### Get Story

**GET** `/stories/{story_uuid}`

Retrieves the complete story state including characters, chapters, scenes, and message history.

**Response:**
```json
{
  "id": "story_uuid",
  "characters": [...],
  "chapters": [...],
  "scenes": [...],
  "messages": [...],
  "created_at": "timestamp",
  "updated_at": "timestamp"
}
```

### Execute Command

**POST** `/stories/{story_uuid}`

Executes a command on the specified story.

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

### 404 Not Found
```json
{
  "detail": "Story not found"
}
```

### 500 Internal Server Error
```json
{
  "detail": "Error message describing what went wrong"
}
```

## Notes

- All commands automatically trigger story summarization to manage context window size
- Stories are persisted to the file system and survive service restarts
- The API uses UUID identifiers for stories to ensure uniqueness
- Character creation is handled automatically when creating a new story using the provided descriptions