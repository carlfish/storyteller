import discord
from storyteller.engine import FileStoryRepository, StoryEngine, Chains
from storyteller.common import load_file, add_standard_model_args, init_model
import storyteller.commands
import re
import os
import json
from storyteller.models import Prompts
from pydantic import BaseModel
from threading import Lock
from dotenv import load_dotenv
import bot.commands as bot_commands
import argparse

load_dotenv()

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True

client = discord.Client(intents=intents)

COMMAND_REGEX = re.compile(r"^~(\w+)(?:\s+)?([\s\S]*)$", re.MULTILINE)
HISTORY_MIN_TOKENS = int(os.getenv("HISTORY_MIN_TOKENS", "1024"))
HISTORY_MAX_TOKENS = int(os.getenv("HISTORY_MAX_TOKENS", "4096"))

STORE_DIR = os.path.expanduser("~/story_repo")
PROMPT_DIR = os.getenv("PROMPT_DIR", "prompts/storyteller/prompts")
STORY_DIR = os.getenv("STORY_DIR", "prompts/storyteller/stories/genfantasy")


class ChannelConfig(BaseModel):
    @classmethod
    def new(cls, story_id: str) -> "ChannelConfig":
        return cls(story_id=story_id, yolo_mode=False)

    story_id: str | None
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


prompts = Prompts(
    base_prompt=load_file(f"{PROMPT_DIR}/base_prompt.md"),
    fix_prompt=load_file(f"{PROMPT_DIR}/fix_prompt.md"),
    scene_summary_prompt=load_file(f"{PROMPT_DIR}/summary_prompt.md"),
    chapter_summary_prompt=load_file(f"{PROMPT_DIR}/chapter_summary_prompt.md"),
    character_summary_prompt=load_file(f"{PROMPT_DIR}/character_summary_prompt.md"),
    character_creation_prompt=load_file(f"{PROMPT_DIR}/character_create_prompt.md"),
)


@client.event
async def on_ready():
    print(f"Logged in as {client.user}")


parser = argparse.ArgumentParser(description="Tell a story")
add_standard_model_args(parser)
model = init_model(parser.parse_args())

story_repository = FileStoryRepository(STORE_DIR)
story_engine = StoryEngine(story_repository)
chains = Chains(model, prompts)

channel_configs = ChannelConfigRegistry(STORE_DIR)


def set_channel_story(channel_id: str, story_id: str) -> None:
    cfg = channel_configs.get_config(channel_id)
    if cfg is None:
        cfg = ChannelConfig.new(story_id)
    else:
        cfg.story_id = story_id
    channel_configs.save_config(channel_id, cfg)


def set_channel_yolo(channel_id: str, yolo_mode: bool) -> None:
    cfg = channel_configs.get_config(channel_id)
    if cfg is None:
        cfg = ChannelConfig.new(None)

    cfg.yolo_mode = yolo_mode
    channel_configs.save_config(channel_id, cfg)


def get_channel_yolo(channel_id: str) -> bool:
    cfg = channel_configs.get_config(channel_id)
    if cfg is None:
        return False
    return cfg.yolo_mode


chargen_prompt = load_file(f"{STORY_DIR}/chargen.md")

story_commands: dict[str, bot_commands.BotCommand] = {
    "newstory": bot_commands.NewStoryCommand(
        set_channel_story, story_repository, chargen_prompt
    ),
    "s": bot_commands.WriteStoryCommand(),
    "retry": bot_commands.RetryCommand(),
    "rewind": bot_commands.RewindCommand(),
    # "fix": FixCommand(), -- Fix doesn't work well enough.
    "rewrite": bot_commands.RewriteCommand(),
    "chapter": bot_commands.CloseChapterCommand(),
    "about": bot_commands.AboutCommand(model.model_name),
    "yolo": bot_commands.YoloCommand(set_channel_yolo, get_channel_yolo),
    "ooc": bot_commands.OocCommand(),
    "dump": bot_commands.DumpStoryCommand(story_repository),
}
story_commands["help"] = bot_commands.HelpCommand(story_commands)

no_story_commands: dict[str, bot_commands.BotCommand] = {
    "newstory": bot_commands.NewStoryCommand(
        set_channel_story, story_repository, chargen_prompt
    ),
    "yolo": bot_commands.YoloCommand(set_channel_yolo, get_channel_yolo),
    "about": bot_commands.AboutCommand(model.model_name),
}
no_story_commands["help"] = bot_commands.HelpCommand(story_commands)

dm_commands: dict[str, bot_commands.BotCommand] = {
    "about": bot_commands.AboutCommand(model.model_name),
}
dm_commands["help"] = bot_commands.HelpCommand(story_commands)


async def _run_summary(
    story_id: str | None,
    story_engine: StoryEngine,
    chains: Chains,
    channel: discord.TextChannel,
) -> None:
    if story_id:
        response = bot_commands.SummaryDiscordResponse(channel)
        await story_engine.run_command(
            story_id,
            storyteller.commands.SummarizeCommand(
                chains, response, HISTORY_MIN_TOKENS, HISTORY_MAX_TOKENS
            ),
        )


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
                ctx = bot_commands.CommandContext(
                    story_id, message, story_engine, chains
                )
                await cmd_dict[command].execute(ctx, args)
                await _run_summary(story_id, story_engine, chains, message.channel)
        elif cfg and cfg.yolo_mode:
            ctx = bot_commands.CommandContext(story_id, message, story_engine, chains)
            await cmd_dict["s"].execute(ctx, content)
            await _run_summary(story_id, story_engine, chains, message.channel)
    except Exception as e:
        await message.channel.send(f"Error: {e}")
        raise e


client.run(os.getenv("DISCORD_TOKEN"))
