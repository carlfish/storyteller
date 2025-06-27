import os


def load_file(filename: str) -> str:
    with open(filename, "r") as f:
        return f.read().strip()


def pick_model():
    if os.getenv("OPENAI_API_KEY", None):
        model_provider = "openai"
        model_name = os.getenv("OPENAPI_MODEL", "gpt-4.1-mini")
    elif os.getenv("ANTHROPIC_API_KEY", None):
        model_provider = "anthropic"
        model_name = os.getenv("ANTHROPIC_MODEL", "claude-3-5-haiku-latest")
    elif os.getenv("XAI_API_KEY", None):
        model_provider = "xai"
        model_name = os.getenv("XAI_MODEL", "grok-3-latest")
    else:
        raise ValueError("No API key found")

    return model_name, model_provider
