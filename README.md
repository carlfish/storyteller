# Storyteller Chatbot

An interactive storytelling chatbot that supports multiple LLM providers and tries its best to minimize clutter 
in the context window.

## Background

As far as I've been able to tell, the enemy of interactive fiction-writing (not to be confused with 
interactive-fiction writing) in modern generative AIs is the context window.

Firstly, and most obviously, it's finite. If you fill it up, the AI will start "forgetting" things.

Probably more importantly, now we have context windows that can fit several novels, the signal-to-noise 
ratio is terrible. If you put the entire chat history in the context, you progressively confound the AI 
with irrelevant detail, while it self-reinforces on repeated phrases andresponse structures.

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

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) package manager
- [just](https://github.com/casey/just) (optional) for cli shortcuts
- API key for one of the supported LLM providers

## Default models:

Chosen to balance capability and cost for each provider. Newer, more expensive
models tend to produce better stories, but where the cheaper model for a given
provider is "good enough", it's preferred.

Claude 3.5-haiku doesn't reliably return correct JSON for structured queries, so
use it at your own risk.

- OpenAI: gpt-4.1-mini
- Anthropic: claude-4.0-sonnet
- XAI: grok-3-latest
- Google: gemini-2.5-flash
- Ollama: (no default)

## Documentation

- [CLI Chatbot](docs/chatbot.md) - Main interactive CLI interface
- [Quickrun Tool](docs/quickrun.md) - Utility for quick prompts and chat sessions
- [Web Service](docs/webservice.md) - HTTP API for story creation and management
- [Discord Bot](docs/discordbot.md) - Discord bot version with multi-channel support
