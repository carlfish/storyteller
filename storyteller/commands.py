from typing import List
from .engine import Command, Chains, run_chat
from .models import Character, Scenes, Story, Chapter, Characters, Scene
from langchain_core.messages import BaseMessage, AIMessage, HumanMessage
from langchain_core.messages.utils import count_tokens_approximately
from abc import ABC, abstractmethod


class CommandError(Exception):
    pass


class Response(ABC):
    @abstractmethod
    async def send_message(self, msg: str):
        pass

    @abstractmethod
    async def start_stream(self):
        pass

    @abstractmethod
    async def end_stream(self):
        pass

    @abstractmethod
    async def append(self, msg: str):
        pass


class ChatCommand(Command[None]):
    def __init__(self, chains: Chains, response: Response, user_input: str):
        self.chains: Chains = chains
        self.response: Response = response
        self.user_input: str = user_input

    def _make_chapters(self, chapters: List[Chapter]):
        summary = ""
        for idx, chapter in enumerate(chapters):
            summary = (
                summary
                + f"## Chapter {idx + 1}: {chapter.title}\n {chapter.summary}\n\n"
            )

        return summary

    def _make_scenes(self, scenes: List[Scene]):
        summary = ""
        for idx, scene in enumerate(scenes):
            summary = summary + f"### {scene.time_and_location}\n{scene.events}\n\n"

        return summary

    async def run(self, story: Story) -> None:
        chat_chain = self.chains.chat_chain
        merged = await run_chat(
            chat_chain=chat_chain,
            context={
                "characters": story.characters,
                "scenes": f"## Chapter {len(story.chapters) + 1}\n\n {self._make_scenes(story.scenes)}",
                "chapters": self._make_chapters(story.chapters),
            },
            current_messages=story.current_messages,
            user_input=self.user_input,
            response=self.response,
        )

        story.current_messages.append(HumanMessage(self.user_input))
        story.current_messages.extend(merged)


class RetryCommand(Command):
    def __init__(self, chains: Chains, response: Response):
        self.chains = chains
        self.response = response

    async def run(self, story: Story):
        if len(story.current_messages) < 2:
            raise CommandError("There is no message to retry!")

        user_input = story.current_messages[-2]
        story.current_messages = story.current_messages[0:-2]
        await ChatCommand(self.chains, self.response, user_input).run(story)


class RewindCommand(Command):
    def __init__(self, chains: Chains, response: Response):
        self.chains = chains
        self.response = response

    async def run(self, story: Story):
        if len(story.current_messages) < 2:
            raise CommandError("There is no message to rewind!")

        await self.response.send_message("⌛ Rewinding…\n\n")
        story.current_messages = story.current_messages[0:-2]

        if len(story.current_messages) > 0:
            await self.response.send_message(
                f"📖 Rewound to last message:\n\n{story.current_messages[-1].content}"
            )
        else:
            await self.response.send_message("❗ Already at start of message history.")


class FixCommand(Command):
    def __init__(self, chains: Chains, response: Response, instruction: str):
        self.chains = chains
        self.response = response
        self.instruction = instruction

    async def fix_message(self, message: str, instruction: str):
        print("\n[Fixing…] " + instruction)
        fixed = ""
        await self.response.start_stream()

        async for chunk in self.chains.fix_chain.astream(
            {
                "message": message.text(),
                "instruction": instruction,
            }
        ):
            await self.response.append(chunk.content)
            fixed = fixed + chunk.content

        await self.response.end_stream()
        return fixed

    async def run(self, story: Story):
        if len(story.current_messages) < 1:
            raise CommandError("There is no message to fix!")

        last_message = story.current_messages[-1]
        fixed = await self.fix_message(last_message, self.instruction)
        story.current_messages[-1] = AIMessage(fixed)


class RewriteCommand(Command):
    def __init__(self, response: Response, text: str):
        self.response = response
        self.text = text

    async def run(self, story: Story):
        if len(story.current_messages) < 1:
            raise CommandError("There is no message to rewrite!")

        story.current_messages[-1] = AIMessage(self.text)
        await self.response.send_message(
            f"📖 Last response rewritten to:\n\n{self.text}"
        )


class SummarizeCommand(Command):
    def __init__(
        self, chains: Chains, response: Response, min_tokens: int, max_tokens: int
    ):
        self.chains = chains
        self.response = response
        self.min_tokens = min_tokens
        self.max_tokens = max_tokens

    def trim(self, messages: List[BaseMessage]):
        old = []
        remaining = messages.copy()

        if count_tokens_approximately(remaining) > self.max_tokens:
            while count_tokens_approximately(remaining) > self.min_tokens:
                old.append(remaining.pop(0))

        return (old, remaining)

    async def update_scenes(
        self, old_scenes: List[Scene], messages, msg_count: int
    ) -> List[Scene]:
        await self.response.send_message(
            f"⌛ Pruning {len(messages)} of {msg_count} messages: updating scene summaries…"
        )

        scene_dump = "\n\n".join(
            [f"## {scene.time_and_location}\n{scene.events}" for scene in old_scenes]
        )
        message_dump = "\n\n".join([message.text() for message in messages])

        response: Scenes = await self.chains.summary_chain.ainvoke(
            {"previous_scenes": scene_dump, "message_dump": message_dump}
        )

        return response.scenes

    async def update_characters(
        self, old_characters: List[Character], messages, msg_count: int
    ) -> List[Character]:
        await self.response.send_message(
            f"⌛ Pruning {len(messages)} of {msg_count} messages: Updating character bios…"
        )

        character_dump = "\n\n".join(
            [
                f"## {character.name} ({character.role})\n{character.bio}"
                for character in old_characters
            ]
        )
        message_dump = "\n\n".join([message.text() for message in messages])

        response: Characters = await self.chains.character_bio_chain.ainvoke(
            {"characters": character_dump, "story": message_dump}
        )
        return response.characters

    async def run(self, story: Story):
        if count_tokens_approximately(story.current_messages) > self.max_tokens:
            msg_count = len(story.current_messages)
            scene_count = len(story.scenes)
            char_count = len(story.characters)
            pruned_messages, remaining_messages = self.trim(story.current_messages)
            story.current_messages = remaining_messages
            story.old_messages.extend(pruned_messages)
            story.scenes = await self.update_scenes(
                story.scenes, pruned_messages, msg_count
            )
            story.characters = await self.update_characters(
                story.characters, pruned_messages, msg_count
            )
            await self.response.send_message(
                f"📖 Pruned {len(pruned_messages)} of {msg_count} messages. Scenes {scene_count}→{len(story.scenes)}. Characters {char_count}→{len(story.characters)}."
            )


class CloseChapterCommand(Command):
    def __init__(
        self,
        chains: Chains,
        summary_response: Response,
        chapter_response: Response,
        chapter_title: str,
    ):
        self.chains = chains
        self.summary_response = summary_response
        self.chapter_response = chapter_response
        self.chapter_title = chapter_title

    async def close_chapter(self, story: Story):
        await self.chapter_response.send_message(
            f"⏳ Closing chapter {len(story.chapters) + 1}…"
        )
        scene_dump = "\n\n".join(
            [f"## {scene.time_and_location}\n{scene.events}" for scene in story.scenes]
        )

        response: Chapter = await self.chains.chapter_chain.ainvoke(
            {
                "scenes": scene_dump,
            }
        )

        if self.chapter_title:
            response.title = self.chapter_title

        story.chapters.append(response)
        story.scenes = []
        await self.chapter_response.send_message(
            f"📖 Closed chapter {len(story.chapters)}: {response.title}"
        )

    async def run(self, story: Story):
        await SummarizeCommand(self.chains, self.summary_response, 0, 0).run(story)
        await self.close_chapter(story)


class GenerateCharactersCommand(Command):
    def __init__(self, chains: Chains, response: Response, prompt: str):
        self.chains = chains
        self.response = response
        self.prompt = prompt

    async def make_characters(self, descriptions: str) -> List[Character]:
        response: Characters = await self.chains.character_create_chain.ainvoke(
            {"characters": descriptions}
        )
        return response.characters

    async def run(self, story: Story):
        characters = await self.make_characters(self.prompt)
        story.characters = characters
        await self.response.send_message(
            f"Created {len(characters)} characters:\n\n{self.prompt}"
        )
