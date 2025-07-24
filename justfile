set dotenv-load := true

# Common development tasks

update:
    uv sync --extra dev

test: 
    uv run pytest

lint:
    uv run ruff check --fix

format:
    uv run ruff format

typecheck:
   uv run mypy .

check: lint format

lint-all: lint format typecheck

# Default app runners

chatbot provider='openai': 
    uv run python chatbot.py -p {{provider}}

discord provider='openai': 
    uv run python discordbot.py -p {{provider}}

webservice provider='openai':
    uv run python webservice.py -p {{provider}}

# Generate an auth token for local testing
generate-token:
    auth0 test token $AUTH0_TEST_CLIENT_ID --audience $AUTH0_API_AUDIENCE --scopes storyteller:use

# Update OpenAPI documentation
update-swagger:
    uv run python scripts/dump_swagger.py > docs/restapi.json