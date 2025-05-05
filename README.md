# Storyteller Chatbot

An interactive storytelling chatbot that supports multiple LLM providers and tries its best to minimize clutter in the context window.

## Features

- Interactive chat interface with conversation memory
- Story management with chapter and scene organization
- Character tracking and development
- Automatic conversation summarization
- Message history management with token limits
- Story repository for saving and loading stories


## Prerequisites

- Python 3.9+
- [uv](https://github.com/astral-sh/uv) package manager
- API key for one of the supported LLM providers:
  - OpenAI (GPT-4.1-mini by default)
  - Anthropic (Claude 3.5 Haiku by default)
  - XAI (Grok-3 by default)

## Interactive CLI Setup

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

### Usage

- Start and continue the story by typing your message
- Type 'quit' to exit the chatbot
- Use special commands to manage the story:
  - `retry` to retry the last interaction
  - `rewind` to go back in the conversation
  - `fix [instructions]` to fix the last message
  - `rewrite [text]` to rewrite specific text
  - `chapter [title]` to start a new chapter
- Stories are automatically saved to the repository for later continuation


## Discord Bot Setup

1. Create a Discord application and bot:
   - Go to the [Discord Developer Portal](https://discord.com/developers/applications)
   - Create a new application
   - Go to the "Bot" section and create a bot
   - Copy the bot token

2. Add the Discord bot token to your environment variables:
   ```
   DISCORD_TOKEN=your_bot_token_here
   ```

3. Invite the bot to your server:
   - Go to OAuth2 > URL Generator in your Discord application
   - Select the "bot" scope
   - Select the following permissions:
     - Read Messages/View Channels
     - Send Messages
     - Read Message History
   - Use the generated URL to invite the bot to your server

4. Run the Discord bot:
   ```bash
   uv run python discordbot.py
   ```

### Discord Bot Commands

The Discord bot supports the following commands:

- `~newstory` - Start a new story, abandoning any story in progress
- `~s [text]` - Write the next section of the story
- `~retry` - Regenerate the last storyteller response
- `~rewind` - Remove the last user message and storyteller response
- `~rewrite [text]` - Replace the last storyteller response with provided text
- `~chapter [title]` - Close the current chapter
- `~help` - Show available commands
- `~about` - Show information about the bot

Each Discord channel can have its own story, and stories are automatically saved and can be continued later.

## Notes

- The chatbot will use the first available API key in the order: OpenAI, Anthropic, XAI
- Stories are saved in a repository located at `~/story_repo`
- The chatbot uses a sophisticated prompt system with separate prompts for different aspects of the story (base, summary, character management, etc.)
- Token limits are configurable through environment variables to manage memory usage and response quality
- Character generation is supported through initial character descriptions 