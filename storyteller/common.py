import argparse
from langchain.chat_models import init_chat_model

default_models = {
    "openai": "gpt-4.1-mini",
    "anthropic": "claude-3-5-haiku-latest",
    "xai": "grok-3-latest",
}


def load_file(filename: str) -> str:
    with open(filename, "r") as f:
        return f.read().strip()


def add_standard_model_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--model", type=str, help="Override the default model for the provider"
    )
    parser.add_argument(
        "-p",
        "--provider",
        type=str,
        required=True,
        choices=["openai", "anthropic", "xai", "ollama"],
        default="openai",
        help="AI Provider to use",
    )
    parser.add_argument(
        "-t",
        "--temperature",
        type=float,
        default=1.0,
        help="Temperature for model generation (default: 1.0)",
    )


def init_model(args: argparse.Namespace):
    if not args.model and args.provider in default_models:
        args.model = default_models[args.provider]

    model = init_chat_model(
        model=args.model, model_provider=args.provider, temperature=args.temperature
    )
    return model
