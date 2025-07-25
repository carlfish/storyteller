from datetime import datetime
from pydantic import BaseModel, field_validator
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, AIMessageChunk


class Chapter(BaseModel):
    title: str
    summary: str


class Character(BaseModel):
    name: str
    role: str
    bio: str


class Scene(BaseModel):
    time_and_location: str
    events: str


class OpeningSuggestion(BaseModel):
    category: str
    opening_paragraph: str


class Story(BaseModel):
    @classmethod
    def new(cls):
        return cls(
            characters=[], chapters=[], scenes=[], old_messages=[], current_messages=[]
        )

    @classmethod
    def to_lc_message(cls, data):
        if data["type"] == "HumanMessage" or data["type"] == "human":
            return HumanMessage(data["content"])
        elif data["type"] == "AIMessage":
            return AIMessage(data["content"])
        elif data["type"] == "AIMessageChunk":
            return AIMessageChunk(data["content"])

    @classmethod
    def to_lc_messages(cls, messages):
        return [Story.to_lc_message(message) for message in messages]

    @field_validator("old_messages", mode="before")
    @classmethod
    def load_old_messages(cls, messages):
        return Story.to_lc_messages(messages)

    @field_validator("current_messages", mode="before")
    @classmethod
    def load_current_messages(cls, messages):
        return Story.to_lc_messages(messages)

    @classmethod
    def to_saved_message(cls, msg: BaseMessage):
        return {"type": msg.__class__.__name__, "content": msg.content}

    model_config = {
        "json_encoders": {BaseMessage: lambda msg: Story.to_saved_message(msg)}
    }

    title: str = "New Story"
    characters: list[Character]
    chapters: list[Chapter]
    scenes: list[Scene]
    old_messages: list[BaseMessage]
    current_messages: list[BaseMessage]


class StoryIndex(BaseModel):
    id: str
    title: str
    chapters: int
    characters: int
    created: datetime
    last_modified: datetime


class Prompts(BaseModel):
    """Prompts used to drive the story engine:
    - base_prompt: story-telling chat prompt (the main story engine)
    - character_creation_prompt: create an initial set of character bios
    - scene_summary_prompt: compress a chat history into scenes
    - chapter_summary_prompt: compress scenes into a chapter summary
    - character_summary_prompt: update character bios based on the chat history
    - fix_prompt: allow the user to request specific changes to the story
    - opening_suggestions_prompt: suggest three different opening paragraphs for a story involving the characters
    """

    base_prompt: str
    character_creation_prompt: str = ""
    scene_summary_prompt: str
    chapter_summary_prompt: str
    character_summary_prompt: str
    fix_prompt: str
    opening_suggestions_prompt: str


class Context(BaseModel):
    """State of the storytelling engine"""

    prompts: Prompts
    story: Story


class Characters(BaseModel):
    """Wrapper for a list of characters, used as
    structured output for the character summary
    prompt.
    """

    characters: list[Character]


class Scenes(BaseModel):
    """Wrapper for a list of scenes, used as
    structured output for the scene summary
    prompt.
    """

    scenes: list[Scene]


class OpeningSuggestions(BaseModel):
    """Wrapper for a list of opening suggestions, used as
    structured output for the opening suggestions prompt.
    """

    suggestions: list[OpeningSuggestion]
