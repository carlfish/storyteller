import re
from typing import List
from langchain.chat_models import init_chat_model
from dotenv import load_dotenv
from storyteller.models import *
from storyteller.engine import FileStoryRepository, StoryEngine, Chains
from storyteller.commands import *
import os
import logging
import asyncio
load_dotenv()

DEBUG = os.getenv("DEBUG", "false").lower() == "true"
STORYTELLER_CLI_STORY = os.getenv("STORYTELLER_CLI_STORY", "floop")
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

class StdoutResponse(Response):
    async def send_message(self, msg: str):
        print(msg)

    async def start_stream(self):
        pass

    async def end_stream(self):
        print()

    async def append(self, msg: str):
        print(msg, end="", flush=True)

def main():    
    prompt_dir = "../prompts/default2"
    story_dir = "../prompts/default2"

    if os.getenv("OPENAI_API_KEY", None):
        model = init_chat_model(model=os.getenv("OPENAPI_MODEL", "gpt-4.1-mini"), model_provider="openai")
    elif os.getenv("ANTHROPIC_API_KEY", None):
        model = init_chat_model(model=os.getenv("ANTHROPIC_MODEL", "claude-3-5-haiku-latest"), model_provider="anthropic")
    elif os.getenv("XAI_API_KEY", None):
        model = init_chat_model(model=os.getenv("XAI_MODEL", "grok-3-latest"), model_provider="xai")
    else:
        raise ValueError("No API key found")

    # model = init_chat_model(model="chatty2", model_provider="ollama")

    context = init_context(prompt_dir)
    chains = Chains(model=model, prompts=context.prompts)
    repo = FileStoryRepository(repo_dir=os.path.expanduser("~/story_repo"))

    if not repo.story_exists(STORYTELLER_CLI_STORY):
        init_chars = load_file(f"{story_dir}/chargen.md")
        context.story.characters = make_characters(chains.character_create_chain, descriptions=init_chars)
        repo.save(STORYTELLER_CLI_STORY, context.story)

    engine = StoryEngine(story_repository=repo)

    preview_story = repo.load(STORYTELLER_CLI_STORY)
    story_id = STORYTELLER_CLI_STORY
    if (len(preview_story.current_messages) > 0):
        print(f"Last message:\n\n{preview_story.current_messages[-1].content}\n\n")

    response = StdoutResponse()

    print("Chatbot initialized. Type 'quit' to exit.")
    print("You can start chatting now!")
        
    while True:    
        try:
            user_input = input("\nYou: ")
            print()
            if user_input.lower() == 'quit':
                print("\nGoodbye!")
                break
            elif user_input.lower() == "retry":
                cmd = RetryCommand(chains, response=response)
            elif user_input.lower() == "rewind":
                cmd = RewindCommand(chains, response=response)
            elif user_input.startswith("fix"):
                instruction = re.sub("^fix:?", "", user_input).strip()
                cmd = FixCommand(chains, response=response, instruction=instruction)
            elif user_input.startswith("rewrite"):
                text = re.sub("^rewrite:?", "", user_input).strip()
                cmd = RewriteCommand(response=response, text=text)
            elif user_input.startswith("chapter"):
                title = re.sub("^chapter:?", "", user_input).strip()
                cmd = CloseChapterCommand(chains, summary_response=response, chapter_response=response, chapter_title=title)
            else:
                cmd = ChatCommand(chains, response=response, user_input=user_input)
                
            # summarize after running command so that we don't accidentally summarize something that
            # needs replaying/rewriting.
            try:
                asyncio.run(engine.run_command(story_id, cmd))
                asyncio.run(engine.run_command(story_id, SummarizeCommand(chains, response=response, min_tokens=HISTORY_MIN_TOKENS, max_tokens=HISTORY_MAX_TOKENS)))
            except Exception as e:
                print(f"Something went wrong: {e}")
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break

if __name__ == "__main__":
    main()