# LangChain Storyteller Chatbot

An advanced interactive storytelling chatbot that supports multiple LLM providers and features a rich command system for story management.

## Features

- Interactive chat interface with conversation memory
- Story management with chapter and scene organization
- Character tracking and development
- Automatic conversation summarization
- Message history management with token limits
- Debug mode for detailed logging
- Story repository for saving and loading stories
- Rich command system:
  - `retry`: Retry the last interaction
  - `rewind`: Rewind the conversation
  - `fix [instruction]`: Fix the last message with specific instructions
  - `rewrite [text]`: Rewrite specific text
  - `chapter [title]`: Close the current chapter and start a new one

## Prerequisites

- Python 3.9+
- [uv](https://github.com/astral-sh/uv) package manager
- API key for one of the supported LLM providers:
  - OpenAI (GPT-4.1-mini by default)
  - Anthropic (Claude 3.5 Haiku by default)
  - XAI (Grok-3 by default)

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
     - `HISTORY_MIN_TOKENS`: Minimum tokens to keep in history (default: 1024)
     - `HISTORY_MAX_TOKENS`: Maximum tokens in history (default: 4096)

3. Run the chatbot:
   ```bash
   uv run python chatbot.py
   ```

## Usage

- Start a conversation by typing your message
- Type 'quit' to exit the chatbot
- Use special commands to manage the story:
  - `retry` to retry the last interaction
  - `rewind` to go back in the conversation
  - `fix [instructions]` to fix the last message
  - `rewrite [text]` to rewrite specific text
  - `chapter [title]` to start a new chapter
- The chatbot maintains conversation memory and can reference previous interactions
- Story elements (characters, chapters, scenes) are automatically tracked and managed
- Stories are automatically saved to the repository for later continuation

## Notes

- The chatbot will use the first available API key in the order: OpenAI, Anthropic, XAI
- Stories are saved in a repository located at `~/story_repo`
- The chatbot uses a sophisticated prompt system with separate prompts for different aspects of the story (base, summary, character management, etc.)
- Token limits are configurable through environment variables to manage memory usage and response quality
- Character generation is supported through initial character descriptions 