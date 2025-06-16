import os
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from storyteller.engine import *
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
import argparse

load_dotenv()

default_models = {
    'openai': 'gpt-4.1-mini',
    'anthropic': 'claude-3-5-haiku-latest',
    'xai': 'grok-3-latest'
}

def load_file(filename: str) -> str:
    with open(filename, "r") as f:
        return f.read().strip()

def make_chat_chain(llm: BaseLanguageModel, base_prompt: str):
    history = InMemoryChatMessageHistory()

    def get_chat_history(session_id: str):
        return history

    # Create a prompt template
    prompt = ChatPromptTemplate.from_messages([
        ("system", base_prompt),
        MessagesPlaceholder(variable_name="messages"),
        ("human", "{input}")
    ])

    chain = prompt | llm
    
    return RunnableWithMessageHistory(chain, get_chat_history, history_messages_key="messages")

def single_prompt(model: BaseLanguageModel, prompt: str):
    chain = make_basic_chain(model, prompt)
    for chunk in chain.stream({}):
        print(chunk.content, end="", flush=True)

def chat_session(model: BaseLanguageModel, prompt: str):
    config = {"configurable": {"session_id": "abc11"}}

    chain = make_chat_chain(model, prompt)
    while True:
        user_input = input("\n\nYou: ")
        if user_input == "exit":
            break
        print()
        for chunk in chain.stream({"input": [HumanMessage(content=user_input)]}, config=config):
            print(chunk.content, end="", flush=True)

def parse_args():
    parser = argparse.ArgumentParser(description='Run a quick prompt or chat session')
    parser.add_argument('-m', '--mode', choices=['chat', 'single'], default='single',
                      help='Type of interaction: single prompt or chat session (default: single)')
    parser.add_argument('-f', '--file', type=str, default='prompts/quickrun.md',
                        help='Path to prompt file')
    parser.add_argument('--model', type=str,
                        help='Override the default model for the provider')
    parser.add_argument('-p', '--provider', type=str, required=True, choices=['openai', 'anthropic', 'xai', 'ollama'],
                        default='openai', help='AI Provider to use')
    parser.add_argument('-t', '--temperature', type=float, default=1.2,
                        help='Temperature for model generation (default: 1.2)')
    return parser.parse_args()

def main():
    args = parse_args()

    if not args.model and args.provider in default_models:
        args.model = default_models[args.provider]

    model = init_chat_model(model=args.model, model_provider=args.provider, temperature=args.temperature)
    prompt = load_file(args.file)

    if args.mode == 'chat':        
        chat_session(model, prompt)
    else:
        single_prompt(model, prompt)

if __name__ == "__main__":
    main()