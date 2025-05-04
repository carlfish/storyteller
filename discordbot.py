from abc import ABC, abstractmethod
import discord
from langchain.chat_models import init_chat_model
from storyteller.engine import FileStoryRepository, StoryEngine, Chains
from storyteller.commands import *
import uuid
import re
import os
import json
from storyteller.models import *
from threading import Lock
from dotenv import load_dotenv
from io import StringIO
import textwrap
load_dotenv()

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True

client = discord.Client(intents=intents)

COMMAND_REGEX = re.compile(r'^!(\w+)(?:\s+)?([\s\S]*)$', re.MULTILINE)
HISTORY_MIN_TOKENS = int(os.getenv("HISTORY_MIN_TOKENS", "1024"))
HISTORY_MAX_TOKENS = int(os.getenv("HISTORY_MAX_TOKENS", "4096"))

STORY_DIR = os.path.expanduser("~/story_repo")
PROMPT_DIR = "prompts/storyteller/prompts"
INIT_STORY_DIR = "prompts/storyteller/stories/genfantasy"

def load_file(filename: str) -> str:
    with open(filename, "r") as f:
        return f.read().strip()


class StoryRegistry:
    REGFILE = "story_registry.json"
    lock = Lock()

    def __init__(self, story_dir: str):
        self.story_dir = story_dir

    def _save_registry(self, registry: dict[str, str]) -> None:
        with open(os.path.join(self.story_dir, self.REGFILE), "w") as f:
            json.dump(registry, f)

    def _load_registry(self) -> dict[str, str]:
        if not os.path.exists(os.path.join(self.story_dir, self.REGFILE)):
            return {}

        with open(os.path.join(self.story_dir, self.REGFILE), "r") as f:
            return json.load(f)

    def current_story(self, channel_id: str) -> str:
        with self.lock:
            registry = self._load_registry()
            return registry.get(channel_id, None)

    def set_current_story(self, channel_id: str, story_id: str) -> None:
        with self.lock:
            registry = self._load_registry()
            registry[channel_id] = story_id
            self._save_registry(registry)


prompts=Prompts(
            base_prompt=load_file(f"{PROMPT_DIR}/base_prompt.md"),
            fix_prompt=load_file(f"{PROMPT_DIR}/fix_prompt.md"),
            scene_summary_prompt=load_file(f"{PROMPT_DIR}/summary_prompt.md"),
            chapter_summary_prompt=load_file(f"{PROMPT_DIR}/chapter_summary_prompt.md"),
            character_summary_prompt=load_file(f"{PROMPT_DIR}/character_summary_prompt.md"),
            character_creation_prompt=load_file(f"{PROMPT_DIR}/character_create_prompt.md")
        )

@client.event
async def on_ready():
    print(f'Logged in as {client.user}')

class BotCommand(ABC):
    help_text: str

    @abstractmethod
    async def execute(self, channel_id: str, args: str) -> None:
        pass

class CheeseCommand(BotCommand):
    help_text = "Cheese"

    async def execute(self, channel: discord.TextChannel, args: str) -> None:
        await channel.send("Cheese")


story_registry = StoryRegistry(STORY_DIR)

if os.getenv("OPENAI_API_KEY", None):
    model = init_chat_model(model=os.getenv("OPENAPI_MODEL", "gpt-4.1-mini"), model_provider="openai")
elif os.getenv("ANTHROPIC_API_KEY", None):
    model = init_chat_model(model=os.getenv("ANTHROPIC_MODEL", "claude-3-5-haiku-latest"), model_provider="anthropic")
elif os.getenv("XAI_API_KEY", None):
    model = init_chat_model(model=os.getenv("XAI_MODEL", "grok-3-latest"), model_provider="xai")
else:
    raise ValueError("No API key found")

story_repository = FileStoryRepository(STORY_DIR)
story_engine = StoryEngine(story_repository)
chains = Chains(model, prompts)

class NewStoryCommand(BotCommand):
    help_text = "Create a new story."

    async def execute(self, channel: discord.TextChannel, args: str) -> None:
        story_id = str(uuid.uuid4())
        story_registry.set_current_story(str(channel.id), story_id)
        story=Story(
            characters=[],
            chapters=[],
            scenes=[],
            current_messages=[],
            old_messages=[]
        )
        story_repository.save(story_id, story)

        chargen_prompt = re.sub(r'^', '> ', load_file(f"{INIT_STORY_DIR}/chargen.md"), flags=re.MULTILINE)

        await channel.send(
            f"""📖 Starting a new story.

First, let's create some heroes using a generic fantasy prompt. (This will be customizable later.)

{chargen_prompt}"""
        )
        story_engine.run_command(story_id, GenerateCharactersCommand(chains, lambda x: None, chargen_prompt))
        generated_characters = story_repository.load(story_id).characters
        character_dump = "\n\n".join(
            [f"## {character.name} ({character.role})\n{textwrap.fill(character.bio, width=80, initial_indent='', subsequent_indent='')}" for character in generated_characters], 
        )
        character_summaries = "\n".join([f"- {character.name} ({character.role})" for character in generated_characters])
        file = discord.File(fp=StringIO(character_dump), filename="characters.md")
        await channel.send(f"Created {len(generated_characters)} characters:\n{character_summaries}", file=file)

class OutputCapturingSink:
    def __init__(self):
        self.output = ""

    def __call__(self, message: str) -> None:
        self.output += message

class WriteStoryCommand(BotCommand):
    help_text = "Write a story."

    async def execute(self, channel: discord.TextChannel, args: str) -> None:
        print(channel.id)
        story_id = story_registry.current_story(str(channel.id))
        if story_id is None:
            await channel.send("No story currently in progress.")
            return

        story = story_repository.load(story_id)
        sink = OutputCapturingSink()
        story_engine.run_command(story_id, ChatCommand(chains, sink, args))
        await channel.send(sink.output)

no_story_commands: dict[str, BotCommand] = {"cheese": CheeseCommand(), "newstory": NewStoryCommand()}
story_commands: dict[str, BotCommand] = {"newstory": NewStoryCommand(), "s": WriteStoryCommand()}

@client.event
async def on_message(message):
    # Ignore messages from the bot itself
    if message.author == client.user:
        return

    content = message.content.strip()
    channel_id = str(message.channel.id)
    
    match = COMMAND_REGEX.match(content)

    story_id = story_registry.current_story(channel_id)
    if story_id is None:
        cmd_dict = no_story_commands
    else:
        cmd_dict = story_commands

    if match:
        command = match.group(1)
        args = match.group(2)

        if command in cmd_dict:
            await cmd_dict[command].execute(message.channel, args)

client.run(os.getenv("DISCORD_TOKEN"))