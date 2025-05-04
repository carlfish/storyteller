import re
from typing import List
from langchain.chat_models import init_chat_model
from dotenv import load_dotenv
from storyteller.models import *
from storyteller.engine import FileStoryRepository, StoryEngine, Chains
from storyteller.commands import *
import os
import logging

# Load environment variables
load_dotenv()

DEBUG = os.getenv("DEBUG", "false").lower() == "true"
HISTORY_MIN_TOKENS = int(os.getenv("HISTORY_MIN_TOKENS", "1024"))
HISTORY_MAX_TOKENS = int(os.getenv("HISTORY_MAX_TOKENS", "4096"))

logger = logging.getLogger(__name__)
if DEBUG:
    logging.basicConfig(level=logging.DEBUG)
else:
    logging.basicConfig(level=logging.WARN)

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
    prompt_dir = "prompts/storyteller/prompts"
    story_dir = "prompts/storyteller/stories/genfantasy"

    if os.getenv("OPENAI_API_KEY", None):
        model = init_chat_model(model=os.getenv("OPENAPI_MODEL", "gpt-4.1-mini"), model_provider="openai")
    elif os.getenv("ANTHROPIC_API_KEY", None):
        model = init_chat_model(model=os.getenv("ANTHROPIC_MODEL", "claude-3-5-haiku-latest"), model_provider="anthropic")
    elif os.getenv("XAI_API_KEY", None):
        model = init_chat_model(model=os.getenv("XAI_MODEL", "grok-3-latest"), model_provider="xai")
    else:
        raise ValueError("No API key found")

    context = init_context(prompt_dir)
    chains = Chains(model=model, prompts=context.prompts)
    repo = FileStoryRepository(repo_dir=os.path.expanduser("~/story_repo"))

    if not repo.story_exists("blah"):
        init_chars = load_file(f"{story_dir}/chargen.md")
        context.story.characters = make_characters(chains.character_create_chain, descriptions=init_chars)
        repo.save("blah", context.story)

    engine = StoryEngine(story_repository=repo)

    preview_story = repo.load("blah")
    story_id = "boing"
    if (len(preview_story.current_messages) > 0):
        print(f"Last message:\n\n{preview_story.current_messages[-1].content}\n\n")

    print("Chatbot initialized. Type 'quit' to exit.")
    print("You can start chatting now!")
        
    while True:    
        user_input = input("\nYou: ")
        if user_input.lower() == 'quit':
            break
        elif user_input.lower() == "retry":
            cmd = RetryCommand(chains, sink=lambda x: print(x, end="", flush=True))
        elif user_input.lower() == "rewind":
            cmd = RewindCommand(chains, sink=lambda x: print(x, end="", flush=True))
        elif user_input.startswith("fix"):
            instruction = re.sub("^fix:?", "", user_input).strip()
            cmd = FixCommand(chains, sink=lambda x: print(x, end="", flush=True), instruction=instruction)
        elif user_input.startswith("rewrite"):
            text = re.sub("^rewrite:?", "", user_input).strip()
            cmd = RewriteCommand(sink=lambda x: print(x, end="", flush=True), text=text)
        elif user_input.startswith("chapter"):
            title = re.sub("^chapter:?", "", user_input).strip()
            cmd = CloseChapterCommand(chains, sink=lambda x: print(x, end="", flush=True), chapter_title=title)
        else:
            cmd = ChatCommand(chains, sink=lambda x: print(x, end="", flush=True), user_input=user_input)
            
        # summarize after running command so that we don't accidentally summarize something that
        # needs replaying/rewriting.
        try:
            engine.run_command(story_id, cmd)
            engine.run_command(story_id, SummarizeCommand(chains, sink=lambda x: print(x, end="", flush=True), min_tokens=HISTORY_MIN_TOKENS, max_tokens=HISTORY_MAX_TOKENS))
        except Exception as e:
            print(f"Something went wrong: {e}")

if __name__ == "__main__":
    main()