from dotenv import load_dotenv
from storyteller.engine import make_basic_chain
from langchain_core.language_models.base import BaseLanguageModel
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from storyteller.common import init_model, add_standard_model_args
import argparse

load_dotenv()


def load_file(filename: str) -> str:
    with open(filename, "r") as f:
        return f.read().strip()


def make_chat_chain(llm: BaseLanguageModel, base_prompt: str):
    history = InMemoryChatMessageHistory()

    def get_chat_history(session_id: str):
        return history

    # Create a prompt template
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", base_prompt),
            MessagesPlaceholder(variable_name="messages"),
            ("human", "{input}"),
        ]
    )

    chain = prompt | llm

    return RunnableWithMessageHistory(
        chain, get_chat_history, history_messages_key="messages"
    )


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
        for chunk in chain.stream(
            {"input": [HumanMessage(content=user_input)]}, config=config
        ):
            print(chunk.content, end="", flush=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a quick prompt or chat session")
    parser.add_argument(
        "-m",
        "--mode",
        choices=["chat", "single"],
        default="single",
        help="Type of interaction: single prompt or chat session (default: single)",
    )
    parser.add_argument(
        "-f",
        "--file",
        type=str,
        default="prompts/quickrun.md",
        help="Path to prompt file",
    )
    add_standard_model_args(parser)
    return parser.parse_args()


def main() -> None:
    args: argparse.Namespace = parse_args()
    model = init_model(args)
    prompt = load_file(args.file)

    if args.mode == "chat":
        chat_session(model, prompt)
    else:
        single_prompt(model, prompt)


if __name__ == "__main__":
    main()
