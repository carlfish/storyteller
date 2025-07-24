import hashlib
import json
import os
import uuid
from typing import Any, Optional
from fastapi import FastAPI, HTTPException, Depends, status, Response
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from fastapi_plugin import Auth0FastAPI

from storyteller.models import Story, Characters, StoryIndex
from storyteller.engine import (
    FileStoryRepository,
    StoryEngine,
    Chains,
    StoryRepository,
    create_prompts,
)
from storyteller import (
    commands as c,
)  # Aliased to avoid clash with Response from fastapi
from storyteller.common import add_standard_model_args, init_model
import argparse

load_dotenv()

HTTP_HOST = os.getenv("HTTP_HOST", "0.0.0.0")
HTTP_PORT = int(os.getenv("HTTP_PORT", "8000"))
PROMPT_DIR = os.getenv("PROMPT_DIR", "prompts/storyteller/prompts")
STORY_DIR = os.getenv("STORY_DIR", "prompts/storyteller/stories/genfantasy")
HISTORY_MIN_TOKENS = int(os.getenv("HISTORY_MIN_TOKENS", "1024"))
HISTORY_MAX_TOKENS = int(os.getenv("HISTORY_MAX_TOKENS", "4096"))

AUTH0_DOMAIN = os.getenv("AUTH0_DOMAIN")
AUTH0_API_AUDIENCE = os.getenv("AUTH0_API_AUDIENCE")
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")

app = FastAPI(title="Storyteller API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

model = None
prompts = None
chains = None

auth = Auth0FastAPI(domain=AUTH0_DOMAIN, audience=AUTH0_API_AUDIENCE)

use_scope = ["storyteller:use"]


def get_story_repository(user_id: str) -> StoryRepository:
    hashed_id = hashlib.sha256(user_id.encode()).hexdigest()
    repo_dir = os.path.expanduser(f"~/story_repo/{hashed_id}")
    os.makedirs(repo_dir, exist_ok=True)
    userinfo_path = os.path.join(repo_dir, "userinfo.json")
    if not os.path.exists(userinfo_path):
        with open(userinfo_path, "w") as f:
            json.dump({"userid": user_id}, f)
    return FileStoryRepository(repo_dir=repo_dir)


class CommandRequest(BaseModel):
    command: str
    body: Optional[str] = None


class GenerateCharactersRequest(BaseModel):
    prompt: str


class APIResponse(c.Response):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.messages = []

    async def send_message(self, msg: str):
        self.messages.append(msg)

    async def start_stream(self):
        self.messages.append("")

    async def end_stream(self):
        pass

    async def append(self, msg: str):
        if self.messages:
            self.messages[-1] += msg
        else:
            self.messages.append(msg)


class CreatedStory(Story):
    story_id: str


def make_characters(descriptions: str) -> Characters:
    return chains.character_create_chain.invoke({"characters": descriptions})


@app.get("/stories")
async def list_stories(
    claims: dict = Depends(auth.require_auth(scopes=use_scope)),
) -> list[StoryIndex]:
    """List all stories for the current user"""
    user_id = claims["sub"]
    repo = get_story_repository(user_id)
    return repo.list()


@app.post("/stories", status_code=status.HTTP_201_CREATED)
async def create_story(
    response: Response,
    claims: dict = Depends(auth.require_auth(scopes=use_scope)),
) -> CreatedStory:
    """Create a new story and return redirect to its UUID endpoint"""
    user_id = claims["sub"]

    story_uuid = str(uuid.uuid4())

    story = Story.new()

    repo = get_story_repository(user_id)
    repo.save(story_uuid, story)

    response.headers["Location"] = f"/stories/{story_uuid}"
    return CreatedStory(**story.model_dump(), story_id=story_uuid)


@app.post("/characters/generate")
async def generate_characters(
    request: GenerateCharactersRequest,
    claims: dict = Depends(auth.require_auth(scopes=use_scope)),
) -> Characters:
    """Generate characters for a story"""

    print(claims)

    characters = make_characters(request.prompt)
    return characters


@app.get("/stories/{story_uuid}")
async def get_story(
    story_uuid: str, claims: dict = Depends(auth.require_auth(scopes=use_scope))
) -> Story:
    """Get the full story state"""

    repo = get_story_repository(claims["sub"])

    if not repo.story_exists(story_uuid):
        raise HTTPException(status_code=404, detail="Story not found")

    story = repo.load(story_uuid)
    return story


class CommandResponse(BaseModel):
    status: str
    messages: list[str]


@app.post("/stories/{story_uuid}")
async def execute_command(
    story_uuid: str,
    command_request: CommandRequest,
    claims: dict = Depends(auth.require_auth(scopes=use_scope)),
) -> CommandResponse:
    """Execute a command on the story"""

    repo = get_story_repository(claims["sub"])

    if not repo.story_exists(story_uuid):
        raise HTTPException(status_code=404, detail="Story not found")

    response = APIResponse()

    try:
        cmd = parse_command(command_request, chains, response)
        engine = StoryEngine(story_repository=repo)
        await engine.run_command(story_uuid, cmd)
        summarize_cmd = c.SummarizeCommand(
            chains,
            response=response,
            min_tokens=HISTORY_MIN_TOKENS,
            max_tokens=HISTORY_MAX_TOKENS,
        )
        await engine.run_command(story_uuid, summarize_cmd)

        return CommandResponse(status="success", messages=response.messages)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def parse_command(
    command_request: CommandRequest, chains: Chains, response: APIResponse
):
    """Parse command request into appropriate Command object"""
    cmd_name = command_request.command.lower()
    body = command_request.body or ""

    if cmd_name == "chat":
        return c.ChatCommand(chains, response=response, user_input=body)
    elif cmd_name == "retry":
        return c.RetryCommand(chains, response=response)
    elif cmd_name == "rewind":
        return c.RewindCommand(chains, response=response)
    elif cmd_name == "fix":
        return c.FixCommand(
            chains, fix_prompt=prompts.fix_prompt, response=response, instruction=body
        )
    elif cmd_name == "replace":
        return c.ReplaceCommand(response=response, text=body)
    elif cmd_name == "chapter":
        return c.CloseChapterCommand(
            chains,
            summary_response=response,
            chapter_response=response,
            chapter_title=body,
        )
    else:
        raise ValueError(f"Unknown command: {cmd_name}")


if __name__ == "__main__":
    import uvicorn

    parser = argparse.ArgumentParser(description="Tell a story")
    add_standard_model_args(parser)
    model = init_model(parser.parse_args())
    prompts = create_prompts(PROMPT_DIR)
    chains = Chains(model=model, prompts=prompts)

    uvicorn.run(app, host=HTTP_HOST, port=HTTP_PORT)
