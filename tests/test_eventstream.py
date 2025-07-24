import pytest
from storyteller.eventstream import *


def test_snapshot_empty_eventstream() -> None:
    empty_stream: EventStream = []
    result = snapshot(empty_stream)
    expected = new_snapshot()

    assert result.unsummarized_messages == expected.unsummarized_messages
    assert len(result.unsummarized_messages) == 0


def test_snapshot_with_chat_messages() -> None:
    message1 = ChatMessage(
        id=1,
        parent=None,
        timestamp=1,
        type=MessageType.Human,
        content="Hello, tell me a story",
    )
    message2 = ChatMessage(
        id=2,
        parent=1,
        timestamp=2,
        type=MessageType.Chatbot,
        content="Once upon a time...",
    )
    message3 = ChatMessage(
        id=3,
        parent=2,
        timestamp=3,
        type=MessageType.Human,
        content="Continue the story",
    )

    event_stream: EventStream = [message1, message2, message3]
    result = snapshot(event_stream)

    assert len(result.unsummarized_messages) == 3
    assert result.unsummarized_messages[0] == message1
    assert result.unsummarized_messages[1] == message2
    assert result.unsummarized_messages[2] == message3


def test_snapshot_with_start_value() -> None:
    message1 = ChatMessage(
        id=1,
        parent=None,
        timestamp=1,
        type=MessageType.Human,
        content="Hello, tell me a story",
    )
    message2 = ChatMessage(
        id=2,
        parent=1,
        timestamp=2,
        type=MessageType.Chatbot,
        content="Once upon a time...",
    )
    message3 = ChatMessage(
        id=3,
        parent=2,
        timestamp=3,
        type=MessageType.Human,
        content="Continue the story",
    )

    event_stream: EventStream = [message1, message2, message3]
    result = snapshot(event_stream, start_id=2)

    assert len(result.unsummarized_messages) == 2
    assert result.unsummarized_messages[0] == message1
    assert result.unsummarized_messages[1] == message2


def test_snapshot_follows_parent_chain() -> None:
    message1 = ChatMessage(
        id=1,
        parent=None,
        timestamp=2,
        type=MessageType.Human,
        content="Hello, tell me a story",
    )
    message2 = ChatMessage(
        id=2,
        parent=1,
        timestamp=2,
        type=MessageType.Chatbot,
        content="Once upon a time...",
    )
    message3 = ChatMessage(
        id=3,
        parent=1,
        timestamp=2,
        type=MessageType.Human,
        content="Continue the story",
    )

    event_stream: EventStream = [message1, message2, message3]
    result = snapshot(event_stream)

    assert len(result.unsummarized_messages) == 2
    assert result.unsummarized_messages[0] == message1
    assert result.unsummarized_messages[1] == message3
