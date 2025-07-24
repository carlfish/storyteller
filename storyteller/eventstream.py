from pydantic import BaseModel
from enum import StrEnum

EventId = int


class Event(BaseModel):
    id: EventId
    parent: EventId | None
    timestamp: int


EventStream = list[Event]


class AnnotationType(StrEnum):
    Fixed = "Fixed"


class Annotation(BaseModel):
    type: AnnotationType
    content: str


class MessageType(StrEnum):
    Human = "HumanMessage"
    Chatbot = "AIMessage"


class ChatMessage(Event):
    type: MessageType
    content: str
    annotation: Annotation | None = None


class StorySnapshot(BaseModel):
    unsummarized_messages: list[ChatMessage]


def new_snapshot():
    return StorySnapshot(unsummarized_messages=[])


def snapshot(events: EventStream, start_id: EventId | None = None) -> StorySnapshot:
    if len(events) == 0:
        return new_snapshot()
    elif start_id == None:
        next_id = events[-1].id
    else:
        next_id = start_id

    unsummarized_messages = []
    for event in reversed(events):
        if event.id == next_id:
            if isinstance(event, ChatMessage):
                unsummarized_messages.append(event)

            if event.parent == None:
                break
            else:
                next_id = event.parent

    unsummarized_messages.reverse()
    return StorySnapshot(unsummarized_messages=list(unsummarized_messages))
