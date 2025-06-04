# Storyteller Chatbot

An interactive storytelling chatbot that supports multiple LLM providers and tries its best to minimize clutter 
in the context window.

## Background

As far as I've been able to tell, the enemy of interactive fiction-writing in modern chat AIs is the context 
window.

Firstly, and most obviously, it's finite. If you fill it up, the AI will start "forgetting" things.

Secondly, the signal-to-noise ratio is terrible. If you put the entire chat history in the context, you
progressively confound the AI with irrelevant detail, while it self-reinforces on repeated phrases and
response structures.

This code is an experiment in extracting the signal from that noise by progressively compressing the story into
live-updating character bios, scene summaries, and chapter summaries, while keeping enough of a window of recent
messages to maintain a consistency of tone and detail.

## Features

- Interactive chat interface with conversation memory
- Story management with chapter and scene organization
- Character tracking and development
- Automatic conversation summarization
- Message history management with token limits
- Story repository for saving and loading stories

## Prerequisites

- Python 3.9+
- [uv](https://github.com/astral-sh/uv) package manager
- API key for one of the supported LLM providers:
  - OpenAI (GPT-4.1-mini by default)
  - Anthropic (Claude 3.5 Haiku by default)
  - XAI (Grok-3 by default)

## Documentation

- [CLI Chatbot](docs/chatbot.md) - Main interactive CLI interface
- [Quickrun Tool](docs/quickrun.md) - Utility for quick prompts and chat sessions
- [Discord Bot](docs/discordbot.md) - Discord bot version with multi-channel support

## Notes

- The chatbot will use the first available API key in the order: OpenAI, Anthropic, XAI
- Token limits are configurable through environment variables to manage memory usage and response quality
- Character generation is supported through initial character descriptions 