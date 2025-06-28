# Storyteller Discord Bot

A Discord bot version of the Storyteller chatbot that allows multiple channels to have their own stories.

## Setup

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
   uv run python discordbot.py -p openai
   ```

## Command-Line Model Selection

You can specify the AI model provider and model using command-line arguments:

```bash
# Use OpenAI with default model
uv run python discordbot.py -p openai

# Use OpenAI with specific model
uv run python discordbot.py -p openai --model gpt-4
```

### Available Options

- `-p, --provider PROVIDER` - AI provider to use (openai, anthropic, xai, google, ollama) **[Required]**
- `-m, --model MODEL_NAME` - Specify the model name to use (optional, uses provider default)

## Environment Variables

- Required:
  - `DISCORD_TOKEN`: Your Discord bot token
  - At least one of the following API keys:
    - `OPENAI_API_KEY`: OpenAI API key
    - `ANTHROPIC_API_KEY`: Anthropic API key 
    - `XAI_API_KEY`: XAI API key
    - `GOOGLE_API_KEY`: Google AI API key

- Optional model configuration:
  - `OPENAPI_MODEL`: OpenAI model name (default: "gpt-4.1-mini")
  - `ANTHROPIC_MODEL`: Anthropic model name (default: "claude-4.0-sonnet")
  - `XAI_MODEL`: XAI model name (default: "grok-3-latest")
  - `GOOGLE_MODEL`: Google model name (default: "gemini-2.5-flash")

- Other settings:
  - `DEBUG`: Set to "true" for detailed logging
  - `STORE_DIR`: Directory for saving stories and channel configs (default: "~/story_repo")
  - `HISTORY_MAX_TOKENS`: Maximum tokens in chat history before summarizing (default: 4096)
  - `HISTORY_MIN_TOKENS`: Tokens to retain after summarizing (default: 1024)
  - `PROMPT_DIR`: Directory containing prompt templates (default: "prompts/storyteller/prompts")
  - `STORY_DIR`: Directory containing story templates (default: "prompts/storyteller/stories/genfantasy")


## Bot Commands

All commands start with `~`:

- `~help` - Show available commands
- `~about` - Show information about the bot
- `~newstory` - Start a new story in the current channel
- `~s [text]` - Continue the story (also works in yolo mode without the command)
- `~retry` - Retry the last interaction
- `~rewind` - Go back in the conversation
- `~fix [instructions]` - Regenerate the previous response according to the instructions
- `~replace [text]` - Replace the previous response entirely
- `~chapter [title]` - Start a new chapter
- `~yolo` - Toggle yolo mode (responds to all messages without needing ~s)
- `~ooc` - Send an out-of-character message
- `~dump` - Dump the current story state

## Features

- Each Discord channel can have its own story
- Stories are automatically saved and can be continued later
- Yolo mode allows for more natural conversation without command prefixes
- Automatic story summarization to maintain context
- Character tracking and development
- Chapter and scene organization 