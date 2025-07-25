import pytest
from storyteller.eventstream import *


def create_default_chat_messages() -> list[ChatMessage]:
    """Create a default chain of 3 connected chat messages for testing."""
    return [
        ChatMessage(
            id=1,
            parent=None,
            timestamp=1000,
            source=MessageSource.Human,
            content="Hello, tell me a story",
        ),
        ChatMessage(
            id=2,
            parent=1,
            timestamp=2000,
            source=MessageSource.Bot,
            content="Once upon a time...",
        ),
        ChatMessage(
            id=3,
            parent=2,
            timestamp=3000,
            source=MessageSource.Human,
            content="Continue the story",
        ),
    ]


def test_snapshot_empty_eventstream() -> None:
    empty_stream: EventStream = []
    result = snapshot(empty_stream)
    expected = new_snapshot()

    assert result.chat_messages == expected.chat_messages
    assert len(result.chat_messages) == 0


def test_snapshot_with_chat_messages() -> None:
    messages = create_default_chat_messages()
    # Adjust timestamps for this specific test
    messages[0].timestamp = 1
    messages[1].timestamp = 2
    messages[2].timestamp = 3

    event_stream: EventStream = messages
    result = snapshot(event_stream)

    assert len(result.chat_messages) == 3
    assert result.chat_messages[0] == messages[0]
    assert result.chat_messages[1] == messages[1]
    assert result.chat_messages[2] == messages[2]


def test_snapshot_with_start_value() -> None:
    messages = create_default_chat_messages()
    # Adjust timestamps for this specific test
    messages[0].timestamp = 1
    messages[1].timestamp = 2
    messages[2].timestamp = 3

    event_stream: EventStream = messages
    result = snapshot(event_stream, start_id=2)

    assert len(result.chat_messages) == 2
    assert result.chat_messages[0] == messages[0]
    assert result.chat_messages[1] == messages[1]


def test_snapshot_follows_parent_chain() -> None:
    messages = create_default_chat_messages()
    # Modify parent chain: message3 points to message1 instead of message2
    messages[2].parent = 1
    # Set same timestamp for all
    for msg in messages:
        msg.timestamp = 2

    event_stream: EventStream = messages
    result = snapshot(event_stream)

    assert len(result.chat_messages) == 2
    assert result.chat_messages[0] == messages[0]
    assert result.chat_messages[1] == messages[2]


def test_snapshot_sets_first_and_last_event_timestamps() -> None:
    messages = create_default_chat_messages()
    # timestamps are already 1000, 2000, 3000 from the helper function

    event_stream: EventStream = messages
    result = snapshot(event_stream)

    assert result.first_event.timestamp() == 1000.0  # messages[0] timestamp
    assert result.last_event.timestamp() == 3000.0  # messages[2] timestamp


def test_snapshot_empty_stream_sets_some_default_time() -> None:
    empty_stream: EventStream = []
    result = snapshot(empty_stream)

    # Should have same time for both first and last event in empty stream
    assert result.first_event == result.last_event


def test_snapshot_with_start_id_sets_correct_timestamps() -> None:
    messages = create_default_chat_messages()
    # timestamps are already 1000, 2000, 3000 from the helper function

    event_stream: EventStream = messages
    result = snapshot(event_stream, start_id=2)

    # Should only include messages[0] and messages[1]
    assert result.first_event.timestamp() == 1000.0  # messages[0] timestamp
    assert result.last_event.timestamp() == 2000.0  # messages[1] timestamp


def test_snapshot_with_noop_events_sets_correct_timestamps() -> None:
    noop1 = NoOp(id=1, parent=None, timestamp=1500, reason="Story creation")
    noop2 = NoOp(id=2, parent=1, timestamp=2500, reason="Story updated")

    event_stream: EventStream = [noop1, noop2]
    result = snapshot(event_stream)

    # Should set timestamps from the NoOp events even though no chat messages
    assert result.first_event.timestamp() == 1500.0  # noop1 timestamp
    assert result.last_event.timestamp() == 2500.0  # noop2 timestamp
    assert len(result.chat_messages) == 0  # No chat messages in result


def test_snapshot_fails_with_missing_parent() -> None:
    messages = create_default_chat_messages()
    messages[1].parent = 99

    event_stream: EventStream = messages

    # Should raise an exception when trying to follow parent chain to non-existent parent
    with pytest.raises(ValueError, match="Parent event with ID 99 not found in stream"):
        snapshot(event_stream)

def test_snapshot_fails_with_missing_start_event() -> None:
    messages = create_default_chat_messages()

    event_stream: EventStream = messages

    # Should raise an exception when trying to follow parent chain to non-existent parent
    with pytest.raises(ValueError, match="Parent event with ID 99 not found in stream"):
        snapshot(event_stream, start_id=99)
