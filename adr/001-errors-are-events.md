# STORYENGINE-001: Errors are events

## Status

Accepted

## Context

How do we handle errors where a command is processed, but something downstream fails?

We already have a client mechanism for retrying unwanted responses, adding another error path would require a separate, equivalent mechanism.

## Decision

Once a command has been accepted for processing, downstream errors are reported back as just another result type, not as 5xx-style server errors. Clients can use the retry/rewind mechanism to make another attempt.

## Implementation Notes

The obvious exception here is any error that prevents us from persisting the command response. This would have to be reported as a 500.