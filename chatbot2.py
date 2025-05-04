import re
from typing import List
from langchain.chat_models import init_chat_model
from dotenv import load_dotenv
from storyteller.models import *
from storyteller.engine import FakeStoryRepository, StoryEngine, Chains
from storyteller.commands import *
import os
import logging

# Load environment variables
load_dotenv()

DEBUG = os.getenv("DEBUG", "false").lower() == "true"
HISTORY_MIN_TOKENS = int(os.getenv("HISTORY_MIN_TOKENS", "750"))
HISTORY_MAX_TOKENS = int(os.getenv("HISTORY_MAX_TOKENS", "1500"))

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
        engine.run_command(story_id, cmd)
        engine.run_command(story_id, SummarizeCommand(chains, sink=lambda x: print(x, end="", flush=True), min_tokens=HISTORY_MIN_TOKENS, max_tokens=HISTORY_MAX_TOKENS))

if __name__ == "__main__":
    main()