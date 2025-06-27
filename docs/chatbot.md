# Storyteller Chatbot CLI

The main interactive CLI interface for the Storyteller chatbot.

## Setup

1. Install dependencies using uv:
   ```bash
   uv sync
   ```

2. Configure environment variables:
   - Required API keys (at least one):
     - `OPENAI_API_KEY`: Your OpenAI API key
     - `ANTHROPIC_API_KEY`: Your Anthropic API key
     - `XAI_API_KEY`: Your XAI API key
   - Optional model configuration:
     - `OPENAPI_MODEL`: OpenAI model name (default: "gpt-4.1-mini")
     - `ANTHROPIC_MODEL`: Anthropic model name (default: "claude-3-5-haiku-latest")
     - `XAI_MODEL`: XAI model name (default: "grok-3-latest")
   - Other optional settings:
     - `DEBUG`: Set to "true" for detailed logging
     - `HISTORY_MAX_TOKENS`: Maximum tokens in chat history before automatically summarizing (default: 4096)
     - `HISTORY_MIN_TOKENS`: Tokens to retain in chat history after automatically summarizing (default: 1024)

3. Run the chatbot:
   ```bash
   uv run python chatbot.py
   ```

## Usage

- Start and continue the story by typing your message
- Type 'quit' to exit the chatbot
- Use special commands to manage the story:
  - `retry` to retry the last interaction
  - `rewind` to go back in the conversation
  - `fix [instructions]` to fix the last message
  - `replace [text]` to replace the last message
  - `chapter [title]` to start a new chapter
- Stories are automatically saved to the repository for later continuation 