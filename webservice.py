import os
import uuid
from typing import Optional
from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel
from dotenv import load_dotenv

from storyteller.models import Story
from storyteller.engine import FileStoryRepository, StoryEngine, Chains, create_prompts
from storyteller import (
    commands as c,
)  # Aliased to avoid clash with Response from fastapi
from storyteller.common import add_standard_model_args, init_model
import argparse

load_dotenv()

app = FastAPI(title="Storyteller API", version="0.1.0")

HTTP_HOST = os.getenv("HTTP_HOST", "0.0.0.0")
HTTP_PORT = int(os.getenv("HTTP_PORT", "8000"))
PROMPT_DIR = os.getenv("PROMPT_DIR", "prompts/storyteller/prompts")
STORY_DIR = os.getenv("STORY_DIR", "prompts/storyteller/stories/genfantasy")
HISTORY_MIN_TOKENS = int(os.getenv("HISTORY_MIN_TOKENS", "1024"))
HISTORY_MAX_TOKENS = int(os.getenv("HISTORY_MAX_TOKENS", "4096"))

parser = argparse.ArgumentParser(description="Tell a story")
add_standard_model_args(parser)
model = init_model(parser.parse_args())

prompts = create_prompts(PROMPT_DIR)

chains = Chains(model=model, prompts=prompts)
repo = FileStoryRepository(repo_dir=os.path.expanduser("~/story_repo"))
engine = StoryEngine(story_repository=repo)


class CommandRequest(BaseModel):
    command: str
    body: Optional[str] = None


class CreateStoryRequest(BaseModel):
    characters: str


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


def make_characters(descriptions: str):
    return chains.character_create_chain.invoke({"characters": descriptions}).characters


@app.post("/stories")
async def create_story(request: CreateStoryRequest):
    """Create a new story and return redirect to its UUID endpoint"""
    story_uuid = str(uuid.uuid4())

    story = Story.new()
    story.characters = make_characters(descriptions=request.characters)

    repo.save(story_uuid, story)

    return Response(
        content="", status_code=201, headers={"Location": f"/stories/{story_uuid}"}
    )


@app.get("/stories/{story_uuid}")
async def get_story(story_uuid: str):
    """Get the full story state"""
    if not repo.story_exists(story_uuid):
        raise HTTPException(status_code=404, detail="Story not found")

    story = repo.load(story_uuid)
    return story.model_dump()


@app.post("/stories/{story_uuid}")
async def execute_command(story_uuid: str, command_request: CommandRequest):
    """Execute a command on the story"""
    if not repo.story_exists(story_uuid):
        raise HTTPException(status_code=404, detail="Story not found")

    response = APIResponse()

    try:
        cmd = parse_command(command_request, chains, response)
        await engine.run_command(story_uuid, cmd)
        summarize_cmd = c.SummarizeCommand(
            chains,
            response=response,
            min_tokens=HISTORY_MIN_TOKENS,
            max_tokens=HISTORY_MAX_TOKENS,
        )
        await engine.run_command(story_uuid, summarize_cmd)

        return {"status": "success", "messages": response.messages}

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

    uvicorn.run(app, host=HTTP_HOST, port=HTTP_PORT)
