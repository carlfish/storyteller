# Web Service

A FastAPI-based web service that provides HTTP endpoints for the storyteller chatbot functionality.

## Usage

```bash
python webservice.py
```

The service will start on the configured host and port, providing REST endpoints for story creation and management.

## Configuration

### Environment Variables

**Server Configuration:**
- `HTTP_HOST`: Server host address (default: 0.0.0.0)
- `HTTP_PORT`: Server port number (default: 8000)

**Story Configuration:**
- `PROMPT_DIR`: Directory containing prompt templates (default: prompts/storyteller/prompts)
- `STORY_DIR`: Directory containing story templates (default: prompts/storyteller/stories/genfantasy)
- `HISTORY_MIN_TOKENS`: Minimum tokens before summarization (default: 1024)
- `HISTORY_MAX_TOKENS`: Maximum tokens before summarization (default: 4096)

**LLM Provider (uses first available):**
- `OPENAI_API_KEY`: OpenAI API key (uses gpt-4.1-mini by default)
- `ANTHROPIC_API_KEY`: Anthropic API key (uses claude-3-5-haiku-latest by default)
- `XAI_API_KEY`: XAI API key (uses grok-3-latest by default)

### API Documentation

See: [restapi.md]

### Story Repository

Stories are saved to `~/story_repo` as JSON files, allowing persistence across service restarts.

## Examples

Start the service on a custom port:
```bash
HTTP_PORT=3000 python webservice.py
```

Run with specific story configuration:
```bash
STORY_DIR=/path/to/stories PROMPT_DIR=/path/to/prompts python webservice.py
```