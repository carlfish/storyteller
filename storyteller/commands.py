from .engine import Command, Chains
from .models import *
from typing import Callable

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

# class RetryCommand(Command):
#     def run(self, story: Story):
#         if (len(story.current_messages) < 2):
#             raise CommandError("Can't retry, not enough chat history!")
        
#         user_input = story.current_messages[-2]