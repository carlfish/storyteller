# Quickrun Tool

A simple utility for running quick prompts or chat sessions with various LLM providers.

## Usage

```bash
python quickrun.py [options]
```

### Options

- `-t, --type`: Type of interaction (default: single)
  - `single`: Run a single prompt and exit
  - `chat`: Start an interactive chat session
- `-f, --file`: Path to prompt file (default: prompts/quickrun.md)
- `-m, --model`: Override the default model for the provider
- `-p, --provider`: AI Provider to use (required)
  - Choices: openai, anthropic, xai, ollama
  - Default: openai

### Default Models

If no model is specified, the following defaults are used:
- OpenAI: gpt-4.1-mini
- Anthropic: claude-3-5-haiku-latest
- XAI: grok-3-latest

### Examples

Run a single prompt with default OpenAI model:
```bash
python quickrun.py -p openai -f my_prompt.md
```

Start a chat session with a specific model:
```bash
python quickrun.py -t chat -p anthropic -m claude-3-opus-latest
``` 