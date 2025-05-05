from abc import ABC, abstractmethod
import discord
from langchain.chat_models import init_chat_model
from storyteller.engine import FileStoryRepository, StoryEngine, Chains
import storyteller.commands
import uuid
import re
import os
import json
from storyteller.models import *
from threading import Lock
from dotenv import load_dotenv
from io import StringIO
from textwrap import fill, dedent
load_dotenv()

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True

client = discord.Client(intents=intents)

COMMAND_REGEX = re.compile(r'^~(\w+)(?:\s+)?([\s\S]*)$', re.MULTILINE)
HISTORY_MIN_TOKENS = int(os.getenv("HISTORY_MIN_TOKENS", "1024"))
HISTORY_MAX_TOKENS = int(os.getenv("HISTORY_MAX_TOKENS", "4096"))

STORY_DIR = os.path.expanduser("~/story_repo")
PROMPT_DIR = "prompts/storyteller/prompts"
INIT_STORY_DIR = "prompts/storyteller/stories/genfantasy"

def load_file(filename: str) -> str:
    with open(filename, "r") as f:
        return f.read().strip()

class ChannelConfig(BaseModel):
    @classmethod
    def new(cls, story_id: str) -> "ChannelConfig":
        return cls(story_id=story_id, yolo_mode=False)

    story_id: str
    yolo_mode: bool

class ChannelConfigs(BaseModel):
    channel: dict[str, ChannelConfig]
class ChannelConfigRegistry:
    REGFILE = "channel_configs.json"
    lock = Lock()

    def __init__(self, story_dir: str):
        self.story_dir = story_dir

    def _save(self, channels: ChannelConfigs) -> None:
        with open(os.path.join(self.story_dir, self.REGFILE), "w") as f:
            json.dump(channels.model_dump(), f)

    def _load(self) -> ChannelConfigs:
        if not os.path.exists(os.path.join(self.story_dir, self.REGFILE)):
            return ChannelConfigs(channel={})

        with open(os.path.join(self.story_dir, self.REGFILE), "r") as f:
            return ChannelConfigs.model_validate_json(f.read())

    def get_config(self, channel_id: str) -> ChannelConfig:
        with self.lock:
            channels = self._load()
            return channels.channel.get(channel_id, None)

    def save_config(self, channel_id: str, config: ChannelConfig) -> None:
        with self.lock:
            channels = self._load()
            channels.channel[channel_id] = config
            self._save(channels)

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
    async def execute(self, story_id: str, message: discord.Message, args: str) -> None:
        pass

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
    help_text = "- Start a new story, abandoning any story that might be in progress."

    def __init__(self, channel_registry: ChannelConfigRegistry, story_repository: FileStoryRepository):
        self.channel_registry = channel_registry
        self.story_repository = story_repository

    def _character_bios(self, characters: list[Character]) -> str:
        return "\n\n".join(
            [f"## {character.name} ({character.role})\n{fill(character.bio, width=80)}" for character in characters], 
        )

    def _character_summaries(self, characters: list[Character]) -> str:
        return "\n".join([f"- {character.name} ({character.role})" for character in characters])

    async def execute(self, story_id: str, message: discord.Message, args: str) -> None:
        story = Story.new()
        channel_id = str(message.channel.id)
        new_story_id = str(uuid.uuid4())
        full_story_id = f"{channel_id}-{new_story_id}"
        self.story_repository.save(full_story_id, story)

        cfg = ChannelConfig.new(new_story_id)
        self.channel_registry.save_config(channel_id, cfg)

        chargen_prompt = re.sub(r'^', '> ', load_file(f"{INIT_STORY_DIR}/chargen.md"), flags=re.MULTILINE)

        await message.channel.send(dedent(f"""\
            📖 Starting a new story.

            First, let's create some heroes using a generic fantasy prompt. (This will be customizable later.)"""))
        story_engine.run_command(full_story_id, storyteller.commands.GenerateCharactersCommand(chains, lambda x: None, chargen_prompt))
        generated_characters = self.story_repository.load(full_story_id).characters
        file = discord.File(fp=StringIO(self._character_bios(generated_characters)), filename="characters.md")
        await message.channel.send(f"Created {len(generated_characters)} characters:\n{self._character_summaries(generated_characters)}", file=file)
class OutputCapturingSink:
    def __init__(self):
        self.output = ""

    def __call__(self, message: str) -> None:
        self.output += message

class WriteStoryCommand(BotCommand):
    help_text = "[text] - write the next section of the story, and the storyteller will continue from there."

    async def execute(self, story_id: str, message: discord.Message, args: str) -> None:
        sink = OutputCapturingSink()
        story_engine.run_command(story_id, storyteller.commands.ChatCommand(chains, sink, args))
        await message.channel.send(sink.output)

class RetryCommand(BotCommand):
    help_text = "- regenerate the last storyteller response, in case you didn't like it."

    async def execute(self, story_id: str, message: discord.Message, args: str) -> None:
        sink = OutputCapturingSink()
        story_engine.run_command(story_id, storyteller.commands.RetryCommand(chains, sink))
        await message.channel.send(sink.output)

class RewindCommand(BotCommand):
    help_text = "- rewind the story, removing the last user message and the storyteller response."

    async def execute(self, story_id: str, message: discord.Message, args: str) -> None:
        sink = OutputCapturingSink()
        story_engine.run_command(story_id, storyteller.commands.RewindCommand(chains, sink))
        await message.channel.send(sink.output)

class FixCommand(BotCommand):
    help_text = "- Do not use this command."

    async def execute(self, story_id: str, message: discord.Message, args: str) -> None:
        sink = OutputCapturingSink()
        story_engine.run_command(story_id, storyteller.commands.FixCommand(chains, sink, args))
        await message.channel.send(sink.output)

class RewriteCommand(BotCommand):
    help_text = "[text] - replace the last storyteller response with the provided text."

    async def execute(self, story_id: str, message: discord.Message, args: str) -> None:
        sink = OutputCapturingSink()
        story_engine.run_command(story_id, storyteller.commands.RewriteCommand(sink, args))
        await message.channel.send(sink.output)

class CloseChapterCommand(BotCommand):
    help_text = "[title] - close the current chapter."

    async def execute(self, story_id: str, message: discord.Message, args: str) -> None:
        sink = OutputCapturingSink()
        story_engine.run_command(story_id, storyteller.commands.CloseChapterCommand(chains, sink, args))
        await message.channel.send(sink.output)

class HelpCommand(BotCommand):
    help_text = "- show this help."

    def __init__(self, cmd_dict: dict[str, BotCommand]) -> None:
        self.cmd_dict = cmd_dict

    async def execute(self, story_id: str, message: discord.Message, args: str) -> None:
        help_text = "Commands:\n" + "\n".join([f"**~{cmd}** {self.cmd_dict[cmd].help_text}" for cmd in self.cmd_dict])
        await message.author.send(help_text)
        await message.add_reaction("👍")

class AboutCommand(BotCommand):
    help_text = "- About me, link to source, and caveats/disclaimers."

    def __init__(self, model_name: str):
        self.model_name = model_name

    async def execute(self, story_id: str, message: discord.Message, args: str) -> None:
        about_text = dedent(f"""\
            # 📖 Storyteller bot
                            
            Collaborate with me to write stories! Currently I only support generic fantasy stories, think the old Dragonlance or early Forgotten Realms novels.

            Currently using: {self.model_name}

            Source code is available under the BSD license at https://github.com/carlfish/storyteller
                            
            ## Caveats and Disclaimers:
                            
            - I'm not very good at writing.
            - Try to close chapters when it makes sense, it cleans my memory of unnecessary details.
            - No effort was made to prevent prompt injection, so please… don't do that?
            - I do my best to keep things PG, but see previous point.
            - If I can write at all, it's because the billionaire backers of AI companies have funded  models trained on a massive corpus of stories and books, most not in the public domain, for their own profit, without compensating or crediting the authors in any way.
            - If you have enjoyed playing with this bot, **BUY A BOOK**.
        """)

        await message.author.send(about_text, suppress_embeds=True)
        await message.add_reaction("👍")

channel_configs = ChannelConfigRegistry(STORY_DIR)



story_commands: dict[str, BotCommand] = {
    "newstory": NewStoryCommand(channel_configs, story_repository), 
    "s": WriteStoryCommand(),
    "retry": RetryCommand(),
    "rewind": RewindCommand(),
    # "fix": FixCommand(), -- Fix doesn't work well enough.
    "rewrite": RewriteCommand(),
    "chapter": CloseChapterCommand(),
    "about": AboutCommand(model.model_name),
    }
story_commands["help"] = HelpCommand(story_commands)

no_story_commands: dict[str, BotCommand] = {
    "newstory": NewStoryCommand(channel_configs, story_repository),
    "about": AboutCommand(model.model_name),
    }
no_story_commands["help"] = HelpCommand(story_commands)

dm_commands: dict[str, BotCommand] = {
    "about": AboutCommand(model.model_name),
    }
dm_commands["help"] = HelpCommand(story_commands)

async def _run_summary(story_id: str, channel: discord.TextChannel) -> None:
    if (story_id):
        summary_sink = OutputCapturingSink()
        story_engine.run_command(story_id, storyteller.commands.SummarizeCommand(chains, summary_sink, HISTORY_MIN_TOKENS, HISTORY_MAX_TOKENS))
        if (summary_sink.output):
            await channel.send(summary_sink.output)

@client.event
async def on_message(message):
    # Ignore messages from the bot itself
    if message.author == client.user:
        return

    channel_id = str(message.channel.id)
    
    try:
        if isinstance(message.channel, discord.DMChannel):
            cmd_dict = dm_commands
            story_id = None
        else:
            cfg = channel_configs.get_config(channel_id)

            if not cfg or not cfg.story_id:
                cmd_dict = no_story_commands
                story_id = None
            else:
                cmd_dict = story_commands
                story_id = f"{channel_id}-{cfg.story_id}"

        content = message.content.strip()
        match = COMMAND_REGEX.match(content)
        if match:
            command = match.group(1)
            args = match.group(2).strip()

            if command in cmd_dict:
                await cmd_dict[command].execute(story_id, message, args)
                await _run_summary(story_id, message)
        elif cfg and cfg.yolo_mode:
            await cmd_dict["s"].execute(story_id, message, content)
            await _run_summary(story_id, message.channel)
    except Exception as e:
        await message.channel.send(f"Error: {e}")
        raise e

client.run(os.getenv("DISCORD_TOKEN"))