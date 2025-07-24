import re
from dotenv import load_dotenv
from storyteller.models import Context, Story, Character
from storyteller.engine import FileStoryRepository, StoryEngine, Chains, create_prompts
from storyteller.commands import (
    Response,
    RetryCommand,
    RewindCommand,
    FixCommand,
    ReplaceCommand,
    CloseChapterCommand,
    ChatCommand,
    SummarizeCommand,
    SuggestOpeningCommand,
)
from storyteller.common import load_file, add_standard_model_args, init_model
import os
import logging
import asyncio
import argparse

load_dotenv()

DEBUG = os.getenv("DEBUG", "false").lower() == "true"
STORYTELLER_CLI_STORY = os.getenv("STORYTELLER_CLI_STORY", "floop-{provider}")
HISTORY_MIN_TOKENS = int(os.getenv("HISTORY_MIN_TOKENS", "1024"))
HISTORY_MAX_TOKENS = int(os.getenv("HISTORY_MAX_TOKENS", "4096"))

logger = logging.getLogger(__name__)
if DEBUG:
    logging.basicConfig(level=logging.DEBUG)
else:
    logging.basicConfig(level=logging.WARN)


def init_context(prompt_dir: str):
    return Context(
        prompts=create_prompts(prompt_dir),
        story=Story(
            characters=[], chapters=[], scenes=[], current_messages=[], old_messages=[]
        ),
    )


def make_characters(chain, descriptions: str) -> list[Character]:
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Tell a story")
    add_standard_model_args(parser)
    return parser.parse_args()


async def main():
    prompt_dir = os.getenv("PROMPT_DIR", "prompts/storyteller/prompts")
    story_dir = os.getenv("STORY_DIR", "prompts/storyteller/stories/genfantasy")

    args = parse_args()
    model = init_model(args)

    context = init_context(prompt_dir)
    chains = Chains(model=model, prompts=context.prompts)
    repo = FileStoryRepository(repo_dir=os.path.expanduser("~/story_repo"))
    story_name = STORYTELLER_CLI_STORY.format(provider=args.provider)
    response = StdoutResponse()

    if not repo.story_exists(story_name):
        init_chars = load_file(story_dir, story_dir, "chargen.md")
        context.story.characters = make_characters(
            chains.character_create_chain, descriptions=init_chars
        )
        repo.save(story_name, context.story)

        await SuggestOpeningCommand(
            chains, response, context.prompts.opening_suggestions_prompt
        ).run(context.story)

    engine = StoryEngine(story_repository=repo)

    preview_story = repo.load(story_name)
    story_id = story_name
    if len(preview_story.current_messages) > 0:
        print(f"Last message:\n\n{preview_story.current_messages[-1].content}\n\n")

    print("Chatbot initialized. Type 'quit' to exit.")
    print("You can start chatting now!")

    while True:
        try:
            user_input = input("\nYou: ")
            print()
            if user_input.lower() == "quit":
                print("\nGoodbye!")
                break
            elif user_input.lower() == "retry":
                cmd = RetryCommand(chains, response=response)
            elif user_input.lower() == "rewind":
                cmd = RewindCommand(chains, response=response)
            elif user_input.startswith("fix"):
                instruction = re.sub("^fix:?", "", user_input).strip()
                cmd = FixCommand(
                    chains,
                    fix_prompt=context.prompts.fix_prompt,
                    response=response,
                    instruction=instruction,
                )
            elif user_input.startswith("replace"):
                text = re.sub("^replace:?", "", user_input).strip()
                cmd = ReplaceCommand(response=response, text=text)
            elif user_input.startswith("chapter"):
                title = re.sub("^chapter:?", "", user_input).strip()
                cmd = CloseChapterCommand(
                    chains,
                    summary_response=response,
                    chapter_response=response,
                    chapter_title=title,
                )
            else:
                cmd = ChatCommand(chains, response=response, user_input=user_input)

            # summarize after running command so that we don't accidentally summarize something that
            # needs replaying/rewriting.
            try:
                await engine.run_command(story_id, cmd)
                await engine.run_command(
                    story_id,
                    SummarizeCommand(
                        chains,
                        response=response,
                        min_tokens=HISTORY_MIN_TOKENS,
                        max_tokens=HISTORY_MAX_TOKENS,
                    ),
                )

            except Exception as e:
                print(f"Something went wrong: {e}")
                raise e
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break


if __name__ == "__main__":
    asyncio.run(main())
