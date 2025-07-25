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
        source=MessageSource.Human,
        content="Hello, tell me a story",
    )
    message2 = ChatMessage(
        id=2,
        parent=1,
        timestamp=2,
        source=MessageSource.Bot,
        content="Once upon a time...",
    )
    message3 = ChatMessage(
        id=3,
        parent=2,
        timestamp=3,
        source=MessageSource.Human,
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
        source=MessageSource.Human,
        content="Hello, tell me a story",
    )
    message2 = ChatMessage(
        id=2,
        parent=1,
        timestamp=2,
        source=MessageSource.Bot,
        content="Once upon a time...",
    )
    message3 = ChatMessage(
        id=3,
        parent=2,
        timestamp=3,
        source=MessageSource.Human,
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
        source=MessageSource.Human,
        content="Hello, tell me a story",
    )
    message2 = ChatMessage(
        id=2,
        parent=1,
        timestamp=2,
        source=MessageSource.Bot,
        content="Once upon a time...",
    )
    message3 = ChatMessage(
        id=3,
        parent=1,
        timestamp=2,
        source=MessageSource.Human,
        content="Continue the story",
    )

    event_stream: EventStream = [message1, message2, message3]
    result = snapshot(event_stream)

    assert len(result.unsummarized_messages) == 2
    assert result.unsummarized_messages[0] == message1
    assert result.unsummarized_messages[1] == message3


def test_snapshot_sets_first_and_last_event_timestamps() -> None:
    message1 = ChatMessage(
        id=1,
        parent=None,
        timestamp=1000,
        source=MessageSource.Human,
        content="First message",
    )
    message2 = ChatMessage(
        id=2,
        parent=1,
        timestamp=2000,
        source=MessageSource.Bot,
        content="Second message",
    )
    message3 = ChatMessage(
        id=3,
        parent=2,
        timestamp=3000,
        source=MessageSource.Human,
        content="Third message",
    )

    event_stream: EventStream = [message1, message2, message3]
    result = snapshot(event_stream)

    assert result.first_event.timestamp() == 1000.0  # message1 timestamp / 1000
    assert result.last_event.timestamp() == 3000.0  # message3 timestamp / 1000


def test_snapshot_empty_stream_sets_some_default_time() -> None:
    empty_stream: EventStream = []
    result = snapshot(empty_stream)

    # Should have same time for both first and last event in empty stream
    assert result.first_event == result.last_event


def test_snapshot_with_start_id_sets_correct_timestamps() -> None:
    message1 = ChatMessage(
        id=1,
        parent=None,
        timestamp=1000,
        source=MessageSource.Human,
        content="First message",
    )
    message2 = ChatMessage(
        id=2,
        parent=1,
        timestamp=2000,
        source=MessageSource.Bot,
        content="Second message",
    )
    message3 = ChatMessage(
        id=3,
        parent=2,
        timestamp=3000,
        source=MessageSource.Human,
        content="Third message",
    )

    event_stream: EventStream = [message1, message2, message3]
    result = snapshot(event_stream, start_id=2)

    # Should only include message1 and message2
    assert result.first_event.timestamp() == 1000.0  # message1 timestamp / 1000
    assert result.last_event.timestamp() == 2000.0  # message2 timestamp / 1000


def test_snapshot_with_noop_events_sets_correct_timestamps() -> None:
    noop1 = NoOp(id=1, parent=None, timestamp=1500, reason="Story creation")
    noop2 = NoOp(id=2, parent=1, timestamp=2500, reason="Story updated")

    event_stream: EventStream = [noop1, noop2]
    result = snapshot(event_stream)

    # Should set timestamps from the NoOp events even though no chat messages
    assert result.first_event.timestamp() == 1500.0  # noop1 timestamp
    assert result.last_event.timestamp() == 2500.0  # noop2 timestamp
    assert len(result.unsummarized_messages) == 0  # No chat messages in result


def test_snapshot_fails_with_missing_parent() -> None:
    # Message with parent ID that doesn't exist in the stream
    message1 = ChatMessage(
        id=1,
        parent=None,
        timestamp=1000,
        source=MessageSource.Human,
        content="First message",
    )
    message2 = ChatMessage(
        id=2,
        parent=99,  # Parent ID 99 doesn't exist in stream
        timestamp=2000,
        source=MessageSource.Bot,
        content="Second message",
    )

    event_stream: EventStream = [message1, message2]

    # Should raise an exception when trying to follow parent chain to non-existent parent
    with pytest.raises(ValueError, match="Parent event with ID 99 not found in stream"):
        snapshot(event_stream)
