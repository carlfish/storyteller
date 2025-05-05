from .engine import Command, Chains
from .models import *
from typing import Callable
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, AIMessageChunk
from langchain_core.messages.utils import count_tokens_approximately

class CommandError(Exception):
    pass

class ChatCommand(Command[None]):
    def __init__(self, chains: Chains, sink: Callable[[str], None], user_input: str):
        self.chains = chains        
        self.sink = sink
        self.user_input = user_input

    def _make_chapters(self, chapters: List[Chapter]):
        summary = ""
        for (idx, chapter) in enumerate(chapters):
            summary = summary + f"## Chapter {idx + 1}: {chapter.title}\n {chapter.summary}\n\n"

        return summary
    
    def _make_scenes(self, scenes: List[Scene]):
        summary = ""
        for (idx, scene) in enumerate(scenes):
            summary = summary + f"### {scene.time_and_location}\n{scene.events}\n\n"

        return summary
    
    def run(self, story: Story) -> None:
        chat_chain = self.chains.chat_chain(story)

        for chunk in chat_chain.stream({
            "input": self.user_input, 
            "characters": story.characters, 
            "scenes": f"## Chapter {len(story.chapters) + 1}\n\n {self._make_scenes(story.scenes)}",
            "chapters": self._make_chapters(story.chapters)
        }):
            self.sink(chunk.content)

class RetryCommand(Command):
    def __init__(self, chains: Chains, sink: Callable[[str], None]):
        self.chains = chains        
        self.sink = sink

    def run(self, story: Story):
        if (len(story.current_messages) < 2):
            raise CommandError("There is no message to retry!")
        
        user_input = story.current_messages[-2]
        story.current_messages = story.current_messages[0:-2]
        ChatCommand(self.chains, self.sink, user_input).run(story)

class RewindCommand(Command):
    def __init__(self, chains: Chains, sink: Callable[[str], None]):
        self.chains = chains        
        self.sink = sink

    def run(self, story: Story):
        if (len(story.current_messages) < 2):
            raise CommandError("There is no message to rewind!")
        
        self.sink("⌛ Rewinding…\n\n")
        story.current_messages = story.current_messages[0:-2]

        if (len(story.current_messages) > 0):
            self.sink(f"Last message:\n\n{story.current_messages[-1].content}\n\n")
        else:
            self.sink(f"At start of message history.\n")

class FixCommand(Command):
    def __init__(self, chains: Chains, sink: Callable[[str], None], instruction: str):
        self.chains = chains        
        self.sink = sink
        self.instruction = instruction

    def fix_message(self, message: str, instruction: str):
        print("\n[Fixing…] " + instruction)
        fixed = ""

        for chunk in self.chains.fix_chain.stream({
            "message": message.text(),
            "instruction": instruction,
        }):
            self.sink(chunk.content)
            fixed = fixed + chunk.content

        return fixed

    def run(self, story: Story):
        if (len(story.current_messages) < 1):
            raise CommandError("There is no message to fix!")
        
        last_message = story.current_messages[-1]
        fixed = self.fix_message(last_message, self.instruction)
        story.current_messages[-1] = AIMessage(fixed)

class RewriteCommand(Command):
    def __init__(self, sink: Callable[[str], None], text: str):
        self.sink = sink
        self.text = text

    def run(self, story: Story):
        if (len(story.current_messages) < 1):
            raise CommandError("There is no message to rewrite!")
        
        story.current_messages[-1] = AIMessage(self.text)
        self.sink(f"Last response rewritten to:\n\n{self.text}\n\n")

class SummarizeCommand(Command):
    def __init__(self, chains: Chains, sink: Callable[[str], None], min_tokens: int, max_tokens: int):
        self.chains = chains
        self.sink = sink
        self.min_tokens = min_tokens
        self.max_tokens = max_tokens

    def trim(self, messages: List[BaseMessage]):
        old = []
        remaining = messages.copy()

        if count_tokens_approximately(remaining) > self.max_tokens:
            while count_tokens_approximately(remaining) > self.min_tokens:
                old.append(remaining.pop(0))

        return (old, remaining)

    def update_scenes(self, old_scenes: List[Scene], messages) -> List[Scene]:
        self.sink(f"[⌛ Updating scene summary ({len(old_scenes)} scenes, {len(messages)} messages)…]\n")

        scene_dump = "\n\n".join([f"## {scene.time_and_location}\n{scene.events}" for scene in old_scenes])
        message_dump = "\n\n".join([message.text() for message in messages])

        response: Scenes = self.chains.summary_chain.invoke({
            "previous_scenes": scene_dump,
            "message_dump": message_dump
        })

        self.sink(f"[Summary updated ({len(response.scenes)} scenes)]\n")

        return response.scenes

    def update_characters(self, old_characters: List[Character], messages) -> List[Character]:
        self.sink(f"[⌛ Updating character bios ({len(old_characters)} characters, {len(messages)} messages)…]\n")

        character_dump = "\n\n".join([f"## {character.name} ({character.role})\n{character.bio}" for character in old_characters])
        message_dump = "\n\n".join([message.text() for message in messages])

        response: Characters = self.chains.character_bio_chain.invoke({
            "characters": character_dump,
            "story": message_dump
        })

        self.sink(f"[Character bios updated ({len(response.characters)} characters)]\n")
        return response.characters

    def run(self, story: Story):
        if (count_tokens_approximately(story.current_messages) > self.max_tokens):
            pruned_messages, remaining_messages = self.trim(story.current_messages)
            story.current_messages = remaining_messages
            story.old_messages.extend(pruned_messages)
            story.scenes = self.update_scenes(story.scenes, pruned_messages)
            story.characters = self.update_characters(story.characters, pruned_messages)

class CloseChapterCommand(Command):
    def __init__(self, chains: Chains, sink: Callable[[str], None], chapter_title: str):
        self.chains = chains
        self.sink = sink
        self.chapter_title = chapter_title

    def close_chapter(self, story: Story):
        self.sink(f"[Closing chapter]")
        scene_dump = "\n\n".join([f"## {scene.time_and_location}\n{scene.events}" for scene in story.scenes])

        response: Chapter = self.chains.chapter_chain.invoke({
            "scenes": scene_dump,
        })

        if self.chapter_title:
            response.title = self.chapter_title
            
        story.chapters.append(response)
        story.scenes = []
        self.sink(f"[Closed chapter {len(story.chapters)}: {response.title}]\n")

    def run(self, story: Story):
        SummarizeCommand(self.chains, self.sink, 0, 0).run(story)
        self.close_chapter(story)
        
class GenerateCharactersCommand(Command):
    def __init__(self, chains: Chains, sink: Callable[[str], None], prompt: str):
        self.chains = chains
        self.sink = sink
        self.prompt = prompt

    def make_characters(self, descriptions: str) -> List[Character]:
        return self.chains.character_create_chain.invoke({"characters": descriptions}).characters

    def run(self, story: Story):
        characters = self.make_characters(self.prompt)
        story.characters = characters
        self.sink(f"Created {len(characters)} characters:\n\n{self.prompt}\n\n")
