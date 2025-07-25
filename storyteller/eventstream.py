from pydantic import BaseModel
from enum import StrEnum
from datetime import datetime

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


class MessageSource(StrEnum):
    Human = "Human"
    Bot = "Bot"


class ChatMessage(Event):
    """
    Event representing a message sent to a chatbot, or
    received back from it.
    """

    source: MessageSource
    content: str
    annotation: Annotation | None = None


class NoOp(Event):
    """
    Event that does nothing. Useful e.g. to insert into the
    stream to mark creation or last-touched times.
    """

    reason: str | None = None


class TitleUpdate(Event):
    source: MessageSource
    content: str


class StorySnapshot(BaseModel):
    """
    A snapshot of the "current" state of an event
    stream, with enough information to run new
    commands against.
    """

    first_event: datetime
    last_event: datetime

    chat_messages: list[ChatMessage]


def new_snapshot():
    """
    The story snapshot of an empty event stream.
    """
    snapshot_ts = datetime.now()
    return StorySnapshot(
        first_event=snapshot_ts,
        last_event=snapshot_ts,
        chat_messages=[],
    )


def snapshot(events: EventStream, start_id: EventId | None = None) -> StorySnapshot:
    """
    Generate a story snapshot from the given event stream, working
    backwards from the event at start_id.
    """
    if len(events) == 0:
        return new_snapshot()
    elif start_id == None:
        next_id = events[-1].id
    else:
        next_id = start_id

    chat_messages = []
    first_event_ts = None
    last_event_ts = None
    for event in reversed(events):
        if event.id == next_id:
            if last_event_ts == None:
                last_event_ts = event.timestamp

            first_event_ts = event.timestamp

            if isinstance(event, ChatMessage):
                chat_messages.append(event)

            next_id = event.parent
            if next_id == None:
                break

    if next_id != None:
        raise ValueError(f"Parent event with ID {next_id} not found in stream")

    chat_messages.reverse()
    return StorySnapshot(
        first_event=datetime.fromtimestamp(first_event_ts),
        last_event=datetime.fromtimestamp(last_event_ts),
        chat_messages=list(chat_messages),
    )
