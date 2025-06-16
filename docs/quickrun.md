# Quickrun Tool

A simple utility for running quick prompts or chat sessions with various LLM providers.

## Usage

```bash
python quickrun.py [options]
```

### Options

- `-m, --mode`: Interaction mode (default: single)
  - `single`: Run a single prompt and exit
  - `chat`: Start an interactive chat session
- `-f, --file`: Path to prompt file (default: prompts/quickrun.md)
- `-p, --provider`: AI Provider to use (required)
  - Choices: openai, anthropic, xai, ollama
  - Default: openai
- `--model`: Override the default model for the provider
- `-t, --temperature`: Temperature for model generation (default: 1.2)

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

Start a chat session with a specific model and temperature:
```bash
python quickrun.py -m chat -p anthropic --model claude-3-opus-latest -t 0.8
``` 