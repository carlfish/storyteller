import argparse
import os
from langchain.chat_models import init_chat_model

default_models = {
    "openai": "gpt-4.1-mini",
    "anthropic": "claude-sonnet-4-0",
    "xai": "grok-3-latest",
    "google": "gemini-2.5-flash",
}


def load_file(directory: str, fallback_directory: str, filename: str) -> str:
    """Load a file from directory, falling back to fallback_directory if not found."""
    primary_path = os.path.join(directory, filename)
    fallback_path = os.path.join(fallback_directory, filename)

    try:
        with open(primary_path, "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        with open(fallback_path, "r") as f:
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
        choices=["openai", "anthropic", "xai", "google", "ollama"],
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

    if args.provider == "google":
        args.provider = "google_genai"

    # Anthropic defaults to 1024 max response tokens, which is only about 800 words so you can hit
    # token limits pretty easily.
    if args.provider == "anthropic":
        return init_chat_model(
            model=args.model,
            model_provider=args.provider,
            temperature=args.temperature,
            max_tokens=4000,
        )
    else:
        return init_chat_model(
            model=args.model, model_provider=args.provider, temperature=args.temperature
        )
