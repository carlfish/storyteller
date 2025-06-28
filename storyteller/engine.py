from abc import ABC, abstractmethod
from langchain_core.chat_history import BaseMessage, BaseChatMessageHistory
from langchain_core.language_models.base import BaseLanguageModel, Runnable
from langchain_core.prompts import (
    PromptTemplate,
    ChatPromptTemplate,
    MessagesPlaceholder,
)
from langchain_core.messages.utils import merge_message_runs
from langchain_core.messages.ai import AIMessageChunk, add_ai_message_chunks

from .models import Story, Scenes, Chapter, Characters, Prompts, OpeningSuggestions

from pydantic import BaseModel
from typing import List, Sequence, TypeVar
from threading import Lock

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
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", base_prompt),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
        ]
    )

    # Create the chain
    return prompt | llm


def make_basic_chain(model: BaseLanguageModel, prompt: str):
    return PromptTemplate.from_template(prompt) | model


def make_structured_chain(
    model: BaseLanguageModel, prompt: str, output_format: type[_BM]
):
    return PromptTemplate.from_template(prompt) | model.with_structured_output(
        output_format, method="json_schema"
    )


class Chains:
    def __init__(self, model: BaseLanguageModel, prompts: Prompts):
        self.chat_chain = make_chat_chain(model, prompts.base_prompt)
        self.summary_chain = make_structured_chain(
            model, prompts.scene_summary_prompt, Scenes
        )
        self.fix_chain = make_basic_chain(model, prompts.fix_prompt)
        self.chapter_chain = make_structured_chain(
            model, prompts.chapter_summary_prompt, Chapter
        )
        self.character_bio_chain = make_structured_chain(
            model, prompts.character_summary_prompt, Characters
        )
        self.character_create_chain = make_structured_chain(
            model, prompts.character_creation_prompt, Characters
        )
        self.opening_suggestions_chain = make_structured_chain(
            model, prompts.opening_suggestions_prompt, OpeningSuggestions
        )


class StoryRepository(ABC):
    @abstractmethod
    def lock(self, story_id: str) -> None:
        pass

    @abstractmethod
    def unlock(self, story_id: str) -> None:
        pass

    @abstractmethod
    def story_exists(self, story_id: str) -> bool:
        pass

    @abstractmethod
    def load(self, story_id: str) -> Story:
        pass

    @abstractmethod
    def save(self, story_id: str, story: Story) -> None:
        pass


class StoryLocked(Exception):
    pass


class FileStoryRepository(StoryRepository):
    locklock = Lock()
    locks: dict[str, bool] = {}

    def __init__(self, repo_dir: str):
        self.repo_dir = repo_dir

    def _repofile(self, story_id: str) -> str:
        return os.path.join(self.repo_dir, f"story-{story_id}.json")

    def lock(self, story_id: str) -> None:
        with self.locklock:
            if story_id in self.locks:
                raise StoryLocked(f"Story {story_id} is locked by another process.")

            self.locks[story_id] = True

    def unlock(self, story_id: str) -> None:
        with self.locklock:
            del self.locks[story_id]

    def story_exists(self, story_id: str) -> bool:
        return os.path.exists(self._repofile(story_id))

    def load(self, story_id: str) -> Story:
        with open(self._repofile(story_id)) as f:
            return Story.model_validate_json(f.read())

    def save(self, story_id: str, story: Story) -> None:
        with open(self._repofile(story_id), "w") as f:
            f.write(story.model_dump_json(indent=2))


class Command(ABC):
    @abstractmethod
    async def run(self, story: Story) -> None:
        pass

class StoryEngine:
    def __init__(self, story_repository: StoryRepository):
        self.story_repository = story_repository

    async def run_command(self, story_id: str, cmd: Command):
        try:
            self.story_repository.lock(story_id)
            story = self.story_repository.load(story_id)
            await cmd.run(story)
            self.story_repository.save(story_id, story)
        finally:
            self.story_repository.unlock(story_id)

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

# Helper functions

async def run_chat(
    chat_chain: Runnable,
    context: dict,
    current_messages: List[BaseMessage],
    user_input: str,
    response: Response,
) -> List[BaseMessage]:
    chunks = []

    await response.start_stream()

    async for chunk in chat_chain.astream(
        {
            **context,
            "chat_history": current_messages,
            "input": user_input,
        }
    ):
        chunks.append(chunk)
        await response.append(chunk.content)

    await response.end_stream()

    merged: list[BaseMessage] = []
    if len(chunks) > 0 and all(isinstance(chunk, AIMessageChunk) for chunk in chunks):
        merged = [add_ai_message_chunks(*chunks)]
    else:
        merged = merge_message_runs(
            chunks, chunk_separator=""
        )  # just in case, but the output will probably be wonky

    return merged
