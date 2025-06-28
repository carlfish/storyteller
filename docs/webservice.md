# Web Service

A FastAPI-based web service that provides HTTP endpoints for the storyteller chatbot functionality.

## Usage

```bash
python webservice.py -p openai
```

The service will start on the configured host and port, providing REST endpoints for story creation and management.

## Command-Line Model Selection

The web service requires specifying an AI provider when starting:

```bash
# Start with OpenAI (default model)
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
- `GOOGLE_API_KEY`: Google AI API key (uses gemini-2.5-flash by default)

### API Documentation

See: [restapi.md]

### Story Repository

Stories are saved to `~/story_repo` as JSON files, allowing persistence across service restarts.

## Examples

Start the service on a custom port:
```bash
HTTP_PORT=3000 python webservice.py -p openai
```

Run with specific story configuration:
```bash
STORY_DIR=/path/to/stories PROMPT_DIR=/path/to/prompts python webservice.py -p google
```