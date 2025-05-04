from langchain_core.chat_history import BaseMessage, BaseChatMessageHistory
from langchain_core.language_models.base import BaseLanguageModel
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory

from .models import *

from pydantic import BaseModel
from typing import List, Sequence, TypeVar

import os

_BM = TypeVar("_BM", bound=BaseModel)

class StoryBackedMessageHistory(BaseChatMessageHistory):
    def __init__(self, story: Story):
        self.story = story

    @property
    def messages(self) -> List[BaseMessage]:
        return self.story.current_messages

    @messages.setter
    def messages(self, new_value):
        self.story.current_messages = new_value

    def add_message(self, message: BaseMessage) -> None:
        self.messages.append(message)

    def add_messages(self, messages: Sequence[BaseMessage]) -> None:
        self.messages.extend(messages)

    def clear(self) -> None:
        self.messages = []

def make_chat_chain(llm: BaseLanguageModel, base_prompt: str):
    # Create a prompt template
    prompt = ChatPromptTemplate.from_messages([
        ("system", base_prompt),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}")
    ])
    
    # Create the chain
    return prompt | llm
        
def make_basic_chain(model: BaseLanguageModel, prompt: str):
    return PromptTemplate.from_template(prompt) | model

def make_structured_chain(model: BaseLanguageModel, prompt: str, output_format: type[_BM]):    
    return PromptTemplate.from_template(prompt) | model.with_structured_output(output_format, method="json_schema")

class Chains:
    def __init__(self, model: BaseLanguageModel, prompts: Prompts):
        self.naked_chat_chain = make_chat_chain(model, prompts.base_prompt)
        self.summary_chain = make_structured_chain(model, prompts.scene_summary_prompt, Scenes)
        self.fix_chain = make_basic_chain(model, prompts.fix_prompt)
        self.chapter_chain = make_basic_chain(model, prompts.chapter_summary_prompt)
        self.character_bio_chain = make_basic_chain(model, prompts.character_summary_prompt)
        self.character_create_chain = make_structured_chain(model, prompts.character_creation_prompt, Characters)

    def chat_chain(self, story: Story):
        def get_session_history():
            return StoryBackedMessageHistory(story)

        # Create the chain with message history
        return RunnableWithMessageHistory(
            self.naked_chat_chain,
            get_session_history,
            input_messages_key="input",
            history_messages_key="chat_history",
        )

class StoryRepository:
    def load(self, story_id: str) -> Story:
        pass

    def save(self, story_id: str, story: Story) -> None:
        pass

class FakeStoryRepository(StoryRepository):
    repofile = os.path.expanduser("~/v2-chat-dump.json")
    def load(self, story_id: str) -> Story:
        with open(self.repofile) as f:
            return Story.model_validate_json(f.read())

    def save(self, story_id: str, story: Story) -> None:
        with open(self.repofile, "w") as f:
            f.write(story.model_dump_json(indent=2))

class Command[T]:
    def run(story: Story) -> T:
        pass

class StoryEngine:
    def __init__(self, story_repository: StoryRepository):
        self.story_repository = story_repository

    def run_command(self, story_id: str, cmd: Command):
        story = self.story_repository.load(story_id)
        cmd.run(story)
        self.story_repository.save(story_id, story)

    def fix(self, message: str, instruction: str) -> str:        
        response = self.chains.fix_chain.invoke({
            "message": message.text(),
            "instruction": instruction,
        })

        return response.content
    
    def make_chapter_summary(self, chapter_title: str, scenes: List[Scene]) -> Chapter:
        scenes_block = "\n".join([f"## {scene.time_and_location}\n{scene.events}" for scene in scenes])
        response = self.chains.chapter_chain.invoke({
            "scenes": scenes_block
        })
        return Chapter(title=chapter_title, summary=response.content)