# LangChain Ollama Chatbot

A simple chatbot implementation using LangChain and Ollama.

## Prerequisites

- Python 3.9+
- [Ollama](https://ollama.ai/) installed and running locally
- [uv](https://github.com/astral-sh/uv) package manager

## Setup

1. Make sure Ollama is running on your system
2. Install dependencies using uv:
   ```bash
   uv sync
   ```
3. Run the chatbot:
   ```bash
   uv run python chatbot.py
   ```

## Usage

- Start a conversation by typing your message
- Type 'quit' to exit the chatbot
- The chatbot maintains conversation memory, so it can remember previous interactions

## Notes

- This implementation uses the llama2 model by default. You can modify the model in the code if you want to use a different one.
- Make sure you have enough system resources to run the LLM model locally. 