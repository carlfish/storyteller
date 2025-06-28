# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Instructions

- Do not include comments that just describe what the code obviously does.

## Common Commands

### Dependencies and Environment
- Install dependencies: `uv sync`
- Run main CLI chatbot: `python chatbot.py`
- Run quickrun utility: `python quickrun.py -p <provider> [-t chat|single] [-f prompt_file] [-m model]`
- lint and format: `ruff check --fix` and `ruff format`
- Run Discord bot: `python discordbot.py`

### Environment Variables
Required API keys (chatbot uses first available):
- `OPENAI_API_KEY` (uses gpt-4.1-mini by default)
- `ANTHROPIC_API_KEY` (uses claude-3-5-haiku-latest by default)  
- `XAI_API_KEY` (uses grok-3-latest by default)
- `GOOGLE_API_KEY` (uses gemini-2.5-flash by default)

Configuration:
- `STORYTELLER_CLI_STORY`: Story name for CLI (default: "floop")
- `HISTORY_MIN_TOKENS`/`HISTORY_MAX_TOKENS`: Token limits for summarization (default: 1024/4096)
- `DEBUG`: Enable debug logging (default: false)
- `PROMPT_DIR`: Prompt directory (default: "prompts/storyteller/prompts")
- `STORY_DIR`: Story directory (default: "prompts/storyteller/stories/genfantasy")

## Architecture

### Core Concept
Interactive storytelling chatbot that manages context window size by:
- Compressing story history into character bios, scene summaries, and chapter summaries
- Maintaining recent message window for tone consistency
- Progressive summarization to prevent context overflow

### Key Components

**storyteller/engine.py**: Core story engine with command pattern
- `StoryEngine`: Main orchestrator for story operations
- `FileStoryRepository`: Persists stories to `~/story_repo`
- `Chains`: LangChain wrapper for LLM operations

**storyteller/models.py**: Pydantic models for story structure
- `Story`: Contains characters, chapters, scenes, and message history
- `Character`, `Chapter`, `Scene`: Core story elements
- Message handling for LangChain integration

**storyteller/commands.py**: Command pattern implementations
- `ChatCommand`: Handle user input and generate responses
- `SummarizeCommand`: Compress old messages when token limits exceeded
- `FixCommand`, `RetryCommand`, `RewindCommand`: Story editing operations
- `CloseChapterCommand`: Create chapter summaries

**chatbot.py**: CLI interface with interactive commands
- Commands: `retry`, `rewind`, `fix: <instruction>`, `rewrite: <text>`, `chapter: <title>`
- Automatic summarization after each command
- Story persistence between sessions

**quickrun.py**: Utility for quick prompts and chat sessions
- Single prompt execution or chat sessions
- Multi-provider support with model overrides

### Story Management
- Stories saved to `~/story_repo` as JSON files
- Character generation from initial descriptions in `chargen.md`
- Automatic context compression based on token limits
- Chapter/scene organization with summaries