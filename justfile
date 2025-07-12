set dotenv-load := true

# Common development tasks

# Update dependencies including dev dependencies
update:
    uv sync --extra dev

# Run the main CLI chatbot
chatbot provider='openai': 
    uv run python chatbot.py -p {{provider}}

# Run Discord bot
discord provider='openai': 
    uv run python discordbot.py -p {{provider}}

# Run the web service
webservice provider='openai':
    uv run python webservice.py -p {{provider}}

# Generate a test bearer token for the web service
generate-token:
    auth0 test token $AUTH0_TEST_CLIENT_ID --audience $AUTH0_API_AUDIENCE --scopes storyteller:use

# Run linting
lint:
    uv run ruff check --fix

# Run formatting
format:
    uv run ruff format

# Run mypy
typecheck:
   uv run mypy .

lint-all: lint format typecheck

# Run both linting and formatting
check: lint format

