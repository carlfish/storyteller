# Common development tasks

# Update dependencies including dev dependencies
update:
    uv sync --extra dev

# Run the main CLI chatbot
chatbot:
    uv run python chatbot.py

# Run Discord bot
discord:
    uv run python discordbot.py

# Run linting
lint:
    ruff check --fix

# Run formatting
format:
    ruff format

# Run mypy
typecheck:
    mypy .

lint-all: lint format typecheck

# Run both linting and formatting
check: lint format

