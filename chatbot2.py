from typing import List, TypeVar
from langchain_ollama import ChatOllama
from langchain_core.language_models.base import BaseLanguageModel
from langchain_core.messages import BaseMessage, AIMessage, AIMessageChunk, HumanMessage, trim_messages
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory, InMemoryChatMessageHistory
from langchain_core.messages.utils import count_tokens_approximately
from langchain.chat_models import init_chat_model
from dotenv import load_dotenv
from pydantic import BaseModel
from storyteller.models import *
from storyteller.engine import FakeStoryRepository, StoryEngine, Chains
from storyteller.commands import ChatCommand
import os
import logging

# Load environment variables
load_dotenv()

DEBUG = os.getenv("DEBUG", "false").lower() == "true"

logger = logging.getLogger(__name__)
if DEBUG:
    logging.basicConfig(level=logging.DEBUG)
else:
    logging.basicConfig(level=logging.WARN)


HISTORY_MIN_TOKENS = int(os.getenv("HISTORY_MIN_TOKENS", "1024"))
HISTORY_MAX_TOKENS = int(os.getenv("HISTORY_MAX_TOKENS", "4096"))
MAX_RESPONSE_TOKENS = int(os.getenv("MAX_RESPONSE_TOKENS", "1024"))
DUMPFILE_NAME = os.getenv("DUMPFILE_NAME", "~/last-chat-dump.json")

USER_NAME = os.getenv("CHAT_USER_NAME", "")
AI_NAME = os.getenv("CHAT_AI_NAME", "")

def load_file(filename: str) -> str:
    with open(filename, "r") as f:
        return f.read().strip()

def init_context(prompt_dir: str):
    return Context(
        prompts=Prompts(
            base_prompt=load_file(f"{prompt_dir}/base_prompt.md"),
            fix_prompt=load_file(f"{prompt_dir}/fix_prompt.md"),
            scene_summary_prompt=load_file(f"{prompt_dir}/summary_prompt.md"),
            chapter_summary_prompt=load_file(f"{prompt_dir}/chapter_summary_prompt.md"),
            character_summary_prompt=load_file(f"{prompt_dir}/character_summary_prompt.md"),
            character_creation_prompt=load_file(f"{prompt_dir}/character_create_prompt.md")
        ),
        story=Story(
            characters=[],
            chapters=[],
            scenes=[],
            current_messages=[],
            old_messages=[]
        )
    )

def make_characters(chain, descriptions: str) -> List[Character]:
    return chain.invoke({"characters": descriptions}).characters


def main():    
    prompt_dir = "prompts/storyteller/prompts2"
    story_dir = "prompts/storyteller/stories/genfantasy"

    # model = init_chat_model("claude-3-5-haiku-20241022", model_provider="anthropic")
    model = init_chat_model(model="grok-3-latest", model_provider="xai")
    # model = init_chat_model("gpt-4.1", model_provider="openai")

    context = init_context(prompt_dir)
    chains = Chains(model=model, prompts=context.prompts)
    repo = FakeStoryRepository()

    if not os.path.exists(repo.repofile):
        init_chars = load_file(f"{story_dir}/characters.md")
        context.story.characters = make_characters(chains.character_create_chain, descriptions=init_chars)
        repo.save("blah", context.story)

    engine = StoryEngine(story_repository=repo)

    preview_story = repo.load("blah")
    if (len(preview_story.current_messages) > 0):
        print(f"Last message:\n\n{preview_story.current_messages[-1].content}\n\n")

    print("Chatbot initialized. Type 'quit' to exit.")
    print("You can start chatting now!")
        
    while True:    
        user_input = input("\nYou: ")
        if user_input.lower() == 'quit':
            break
        else:
            cmd = ChatCommand(chains, sink=lambda x: print(x, end="", flush=True), user_input=user_input)
            engine.run_command("boing", cmd)
            
if __name__ == "__main__":
    main()