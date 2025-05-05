from abc import ABC, abstractmethod
import discord
from storyteller.engine import FileStoryRepository, StoryEngine, Chains
import storyteller.commands
import uuid
import re
from storyteller.models import *
from io import StringIO
from textwrap import fill, dedent

class NoOpResponse(storyteller.commands.Response):
    async def send_message(self, content: str, file: discord.File | None = None) -> None:
        pass

    async def start_stream(self) -> None:
        pass

    async def append(self, content: str) -> None:
        pass

    async def end_stream(self) -> None:
        pass
    
class DiscordResponse(storyteller.commands.Response):
    @classmethod
    def to_channel(cls, message: discord.Message) -> "DiscordResponse":
        return cls(message.channel)
    
    @classmethod
    def to_user(cls, message: discord.Message) -> "DiscordResponse":
        return cls(message.author)

    def __init__(self, channel: discord.TextChannel):
        self.channel = channel
        self.stream_message: discord.Message | None = None
        self.stream_content = ""
        self.last_update_time = 0  # Track last update time

    async def send_message(self, content: str, file: discord.File | None = None) -> None:
        await self.channel.send(content, file=file)

    async def start_stream(self) -> None:
        self.stream_message = await self.channel.send("⌛ Thinking...")
        self.stream_content = ""
        self.last_update_time = discord.utils.utcnow().timestamp()

    async def append(self, content: str) -> None:
        if self.stream_message is None:
            return
        self.stream_content += content
        
        # Only update if 5 seconds have passed since last update
        current_time = discord.utils.utcnow().timestamp()
        if current_time - self.last_update_time >= 5:
            await self.stream_message.edit(content=self.stream_content)
            self.last_update_time = current_time

    async def end_stream(self) -> None:
        if self.stream_message is None:
            return
        await self.stream_message.delete()
        await self.channel.send(self.stream_content)
        self.stream_content = ""
        self.last_update_time = 0

class SummaryDiscordResponse(storyteller.commands.Response):
    def __init__(self, channel: discord.TextChannel):
        self.channel = channel
        self.message: discord.Message | None = None

    async def send_message(self, content: str, file: discord.File | None = None) -> None:
        if self.message is None:
            self.message = await self.channel.send(content)
        else:
            await self.message.edit(content=content)

    async def start_stream(self) -> None:
        raise storyteller.commands.CommandError("Unexpected streaming response from summary command.")

    async def append(self, content: str) -> None:
        raise storyteller.commands.CommandError("Unexpected streaming response from summary command.")

    async def end_stream(self) -> None:
        raise storyteller.commands.CommandError("Unexpected streaming response from summary command.")

class CommandContext:
    def __init__(self, story_id: str | None, message: discord.Message, story_engine: StoryEngine, chains: Chains):
        self.story_id = story_id
        self.message = message
        self.story_engine = story_engine
        self.chains = chains

    async def send(self, content: str, file: discord.File | None = None) -> None:
        await self.message.channel.send(content, file=file)

    async def send_dm(self, content: str, file: discord.File | None = None) -> None:
        await self.message.author.send(content, file=file)

    async def add_reaction(self, emoji: str) -> None:
        await self.message.add_reaction(emoji)

class BotCommand(ABC):
    help_text: str

    @abstractmethod
    async def execute(self, ctx: CommandContext, args: str) -> None:
        pass

class OutputCapturingSink:
    def __init__(self):
        self.output = ""

    def __call__(self, message: str) -> None:
        self.output += message

class NewStoryCommand(BotCommand):
    help_text = "- Start a new story, abandoning any story that might be in progress."

    def __init__(self, set_channel_story: callable, story_repository: FileStoryRepository, chargen_prompt: str):
        self.set_channel_story = set_channel_story
        self.story_repository = story_repository
        self.chargen_prompt = chargen_prompt

    def _character_bios(self, characters: list[Character]) -> str:
        return "\n\n".join(
            [f"## {character.name} ({character.role})\n{fill(character.bio, width=80)}" for character in characters], 
        )

    def _character_summaries(self, characters: list[Character]) -> str:
        return "\n".join([f"- {character.name} ({character.role})" for character in characters])

    async def execute(self, ctx: CommandContext, args: str) -> None:
        story = Story.new()
        channel_id = str(ctx.message.channel.id)
        new_story_id = str(uuid.uuid4())
        full_story_id = f"{channel_id}-{new_story_id}"
        self.story_repository.save(full_story_id, story)
        self.set_channel_story(channel_id, new_story_id)

        await ctx.send(dedent(f"""\
            📖 Starting a new story.

            First, let's create some heroes using a generic fantasy prompt. (This will be customizable later.)"""))
        
        await ctx.story_engine.run_command(full_story_id, storyteller.commands.GenerateCharactersCommand(ctx.chains, NoOpResponse(), self.chargen_prompt))
        generated_characters = self.story_repository.load(full_story_id).characters
        file = discord.File(fp=StringIO(self._character_bios(generated_characters)), filename="characters.md")
        await ctx.send(f"Created {len(generated_characters)} characters:\n{self._character_summaries(generated_characters)}", file=file)

class WriteStoryCommand(BotCommand):
    help_text = "[text] - write the next section of the story, and the storyteller will continue from there."

    async def execute(self, ctx: CommandContext, args: str) -> None:
        response = DiscordResponse.to_channel(ctx.message)
        await ctx.story_engine.run_command(ctx.story_id, storyteller.commands.ChatCommand(ctx.chains, response, args))

class RetryCommand(BotCommand):
    help_text = "- regenerate the last storyteller response, in case you didn't like it."

    async def execute(self, ctx: CommandContext, args: str) -> None:
        response = DiscordResponse.to_channel(ctx.message)
        await ctx.story_engine.run_command(ctx.story_id, storyteller.commands.RetryCommand(ctx.chains, response))

class RewindCommand(BotCommand):
    help_text = "- rewind the story, removing the last user message and the storyteller response."

    async def execute(self, ctx: CommandContext, args: str) -> None:
        response = DiscordResponse.to_channel(ctx.message)
        await ctx.story_engine.run_command(ctx.story_id, storyteller.commands.RewindCommand(ctx.chains, response))

class FixCommand(BotCommand):
    help_text = "- Do not use this command."

    async def execute(self, ctx: CommandContext, args: str) -> None:
        response = DiscordResponse.to_channel(ctx.message)
        await ctx.story_engine.run_command(ctx.story_id, storyteller.commands.FixCommand(ctx.chains, response, args))

class RewriteCommand(BotCommand):
    help_text = "[text] - replace the last storyteller response with the provided text."

    async def execute(self, ctx: CommandContext, args: str) -> None:
        response = DiscordResponse.to_channel(ctx.message)
        await ctx.story_engine.run_command(ctx.story_id, storyteller.commands.RewriteCommand(response, args))

class CloseChapterCommand(BotCommand):
    help_text = "[title] - close the current chapter."

    async def execute(self, ctx: CommandContext, args: str) -> None:
        # Send summary and chapter responses in different messages.
        summary_response = SummaryDiscordResponse(ctx.message.channel)
        chapter_response = SummaryDiscordResponse(ctx.message.channel)
        await ctx.story_engine.run_command(ctx.story_id, storyteller.commands.CloseChapterCommand(ctx.chains, summary_response, chapter_response, args))

class HelpCommand(BotCommand):
    help_text = "- show this help."

    def __init__(self, cmd_dict: dict[str, BotCommand]) -> None:
        self.cmd_dict = cmd_dict

    async def execute(self, ctx: CommandContext, args: str) -> None:
        help_text = "Commands:\n" + "\n".join([f"**~{cmd}** {self.cmd_dict[cmd].help_text}" for cmd in self.cmd_dict])
        await ctx.send_dm(help_text)
        await ctx.add_reaction("👍")

class AboutCommand(BotCommand):
    help_text = "- About me, link to source, and caveats/disclaimers."

    def __init__(self, model_name: str):
        self.model_name = model_name

    async def execute(self, ctx: CommandContext, args: str) -> None:
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

        await ctx.message.author.send(about_text, suppress_embeds=True)
        await ctx.add_reaction("👍") 

class YoloCommand(BotCommand):
    help_text = "[on|off] - when yolo mode is on, all messages that are not ~ooc are treated as storyteller messages."

    def __init__(self, set_channel_yolo: callable, get_channel_yolo: callable):
        self.set_channel_yolo = set_channel_yolo
        self.get_channel_yolo = get_channel_yolo

    def _get_yolo_mode_msg(self, yolo_mode: bool) -> str:
        if yolo_mode:
            return f"Yolo mode is **on**. To write a message that is not part of the story, prefix it with ~ooc."
        else:
            return f"Yolo mode is **off**. To write a message that is part of the story, prefix it with ~s."

    def _is_yolo_mode(self, ctx: CommandContext) -> bool:
        return self.get_channel_yolo(str(ctx.message.channel.id))

    async def execute(self, ctx: CommandContext, args: str) -> None:
        arg = args.strip().lower()
        if arg == "on" or arg == "true":
            self.set_channel_yolo(str(ctx.message.channel.id), True)
            message = f"❗ {self._get_yolo_mode_msg(True)}"
        elif arg == "off" or arg == "false":
            self.set_channel_yolo(str(ctx.message.channel.id), False)
            message = f"❗ {self._get_yolo_mode_msg(False)}"
        elif not arg:
            message = f"❗ {self._get_yolo_mode_msg(self._is_yolo_mode(ctx))}"
        else:
            message = f"❗ Usage: ~yolo [on|off]. {self._get_yolo_mode_msg(self._is_yolo_mode(ctx))}"

        await ctx.send(message)

class OocCommand(BotCommand):
    help_text = "[text] - write a message that will be ignored when yolo mode is on."

    async def execute(self, ctx: CommandContext, args: str) -> None:
        pass
