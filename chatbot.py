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
import os
import re
import logging
import json

# Load environment variables
load_dotenv()

_BM = TypeVar("_BM", bound=BaseModel)

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

class Chapter(BaseModel):
    title: str
    summary: str
class Prompts(BaseModel):
    base_prompt: str
    summary_prompt: str
    chapter_summary_prompt: str
    character_creation_prompt: str = ""
    character_summary_prompt: str
    fix_prompt: str

class Story(BaseModel):
    characters: str
    chapters: List[Chapter]
    summary: str
    old_messages: List[BaseMessage]
    chat_history: InMemoryChatMessageHistory

class Context(BaseModel):
    prompts: Prompts
    story: Story
    
class Character(BaseModel):
    name: str
    role: str
    bio: str
class Characters(BaseModel):
    characters: List[Character]

class Scene(BaseModel):
    time_and_location: str
    events: str
class Scenes(BaseModel):
    scenes: List[Scene]

def save_context(context: Context, filename: str):
    """Save the Context object to a JSON file."""
    # Convert chat history to list of messages before saving
    history_messages = context.story.chat_history.messages
    old_messages = context.story.old_messages
    
    # Create dict representation without the chat_history object
    context_dict = context.model_dump()
    context_dict["story"]["chat_history"] = [
        {
            "type": msg.__class__.__name__,
            "content": msg.content
        }
        for msg in history_messages
    ]
    
    context_dict["story"]["old_messages"] = [
        {
            "type": msg.__class__.__name__,
            "content": msg.content
        }
        for msg in old_messages
    ]

    with open(filename, "w") as f:
        json.dump(context_dict, f, indent=2)

def to_message(data):
        if data["type"] == "HumanMessage":
            return HumanMessage(data["content"])
        elif data["type"] == "AIMessage":
            return AIMessage(data["content"])
        elif data["type"] == "AIMessageChunk":
            return AIMessageChunk(data["content"])

def load_context_from_file(filename: str) -> Context:
    """Load a Context object from a JSON file."""
    with open(filename, "r") as f:
        data = json.load(f)
    
    # Create new chat history
    chat_history = InMemoryChatMessageHistory()
    
    chat_history.add_messages([to_message(msg) for msg in data["story"]["chat_history"]])    
    # Replace chat history data with actual object
    data["story"]["chat_history"] = chat_history
    data["story"]["old_messages"] = [to_message(msg) for msg in data["story"]["old_messages"]]
    
    return Context.model_validate(data)


def load_file(filename: str) -> str:
    with open(filename, "r") as f:
        return f.read().strip()

def init_context(prompt_dir: str, story_dir: str):
    return Context(
        prompts=Prompts(
            base_prompt=load_file(f"{prompt_dir}/base_prompt.md"),
            fix_prompt=load_file(f"{prompt_dir}/fix_prompt.md"),
            summary_prompt=load_file(f"{prompt_dir}/summary_prompt.md"),
            chapter_summary_prompt=load_file(f"{prompt_dir}/chapter_summary_prompt.md"),
            character_summary_prompt=load_file(f"{prompt_dir}/character_summary_prompt.md"),
            character_creation_prompt=load_file(f"{prompt_dir}/character_create_prompt.md")
        ),
        story=Story(
            characters=load_file(f"{story_dir}/characters.md"),
            chapters=[],
            summary=load_file(f"{story_dir}/start.md"),
            chat_history=InMemoryChatMessageHistory(),
            old_messages=[]
        )
    )


def make_chat_chain(llm: BaseLanguageModel, context: Context):
    # Create a prompt template
    prompt = ChatPromptTemplate.from_messages([
        ("system", context.prompts.base_prompt),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}")
    ])
    
    # Create the chain
    chain = prompt | llm
        
    def get_session_history():
        return context.story.chat_history
    
    # Create the chain with message history
    return RunnableWithMessageHistory(
        chain,
        get_session_history,
        input_messages_key="input",
        history_messages_key="chat_history",
    )

def make_chapters(chapters: List[Chapter]):
    summary = ""
    for (idx, chapter) in enumerate(chapters):
        summary = summary + f"## Chapter {idx + 1}: {chapter.title}\n\n {chapter.summary}\n\n"

    return summary

def make_basic_chain(llm: BaseLanguageModel, prompt: str):
    return PromptTemplate.from_template(prompt) | llm

def make_structured_chain(llm: BaseLanguageModel, prompt: str, output_format: type[_BM]):    
    return PromptTemplate.from_template(prompt) | llm.with_structured_output(output_format, method="json_schema")

def to_summary_line(message: BaseMessage):
    if message.type.lower().startswith("ai") and AI_NAME:
        return f"<{AI_NAME}> {message.text()}"
    elif message.type.lower().startswith("human") and USER_NAME:
        return f"<{USER_NAME}> {message.text()}"
    else:
        return message.text()

def update_summary(summary_chain, old_summary, messages):
    logger.info("[Summarizing…]")

    message_dump = "\n\n".join([to_summary_line(message) for message in messages])

    response = summary_chain.invoke({
        "previous_summary": old_summary,
        "message_dump": message_dump
    })

    new_summary = re.sub('<think>.*</think>', '', response.content, flags=re.DOTALL).strip()

    logger.info("[Summarized]")
    logger.debug("Summary: " + new_summary)

    return new_summary

def update_characters(chain, characters, messages):
    logger.info("[Characters…]")

    message_dump = "\n\n".join([to_summary_line(message) for message in messages])

    response = chain.invoke({
        "characters": characters,
        "story": message_dump
    })

    new_characters = re.sub('<think>.*</think>', '', response.content, flags=re.DOTALL).strip()

    logger.info("[Characters…]")
    logger.debug("Characters: " + new_characters)

    return new_characters

def close_chapter(chapter_chain, chapter_title, final_summary):   
    logger.info(f"[Closing chapter: {chapter_title}]")

    response = chapter_chain.invoke({
        "summary": final_summary
    })

    logger.info(f"[Chapter closed: {chapter_title}]\n\n{response.content}")

    return Chapter(title=chapter_title, summary=response.content)

def fix_message(fix_chain, message, context, instruction):
    if instruction:
        instruction = "The author has included the following additional instruction: " + instruction
    
    print("\n[Fixing…] " + instruction)    

    response = fix_chain.invoke({
        "prose": message.text(),
        "instruction": instruction,
        "context": context.text()
    })

    print("\n[Fixed]\n" + response.content)
    return AIMessage(response.content)
        
def make_characters(chain, descriptions: str) -> Characters:
    return chain.invoke({"characters": descriptions})

def trim(messages: List[BaseMessage]):
    old = []
    remaining = messages.copy()

    if count_tokens_approximately(remaining) > HISTORY_MAX_TOKENS:
        while count_tokens_approximately(remaining) > HISTORY_MIN_TOKENS:
            old.append(remaining.pop(0))

    return (old, remaining)

def main():    
    # chatllm = ChatOllama(
    #     model="chatty2",
    #     num_predict=MAX_RESPONSE_TOKENS,
    #     temperature=0.6,
    # )

    # summaryllm = ChatOllama(
    #     model="chatty2",
    #     num_predict=MAX_RESPONSE_TOKENS,
    #     temperature=0.4,
    # )

    prompt_dir = "prompts/storyteller/prompts"
    story_dir = "prompts/storyteller/stories/genfantasy"

    # model = init_chat_model("claude-3-5-haiku-20241022", model_provider="anthropic")
    model = init_chat_model(model="grok-3-latest", model_provider="xai")
    # model = init_chat_model("gpt-4.1", model_provider="openai")
    chatllm = model
    summaryllm = model


    # Expand the dumpfile path
    dumpfile = os.path.expanduser(DUMPFILE_NAME)
    
    # Try to load context from dump file, fall back to init if it doesn't exist
    try:
        context = load_context_from_file(dumpfile)
        print(f"Loaded context from {dumpfile}\n")
        if (len(context.story.chat_history.messages) > 0):
            print(context.story.chat_history.messages[-1].text())
    except FileNotFoundError:
        context = init_context(prompt_dir, story_dir)
        print("Initialized new context")

    context.prompts = init_context(prompt_dir, story_dir).prompts

    # Create the chain with message history
    chat_chain = make_chat_chain(chatllm, context)
    summary_chain = make_basic_chain(summaryllm, context.prompts.summary_prompt)
    fix_chain = make_basic_chain(chatllm, context.prompts.fix_prompt)
    chapter_chain = make_basic_chain(summaryllm, context.prompts.chapter_summary_prompt)
    character_chain = make_basic_chain(summaryllm, context.prompts.character_summary_prompt)
    character_creation_chain = make_structured_chain(summaryllm, context.prompts.character_creation_prompt, Characters)

    print("Chatbot initialized. Type 'quit' to exit.")
    print("You can start chatting now!")
        
    while True:
        save_context(context, dumpfile)
        session_history = context.story.chat_history
    
        user_input = input("\nYou: ")
        if user_input.lower() == 'quit':
            # Save context before exiting
            save_context(context, dumpfile)
            print(f"\nContext saved to {dumpfile}")
            break

        if user_input.lower() == "retry" or user_input.lower() == "replay":
            print("\nRetrying…")
            user_input = session_history.messages[-2]
            session_history.messages = session_history.messages[0:-2]
        elif user_input.lower() == "rewind":
            print("\nRewinding")
            session_history.messages = session_history.messages[0:-2]
            continue
        elif user_input.startswith("fix"):
            instruction = re.sub("^fix:?", "", user_input).strip()
            last_response = session_history.messages[-1]
            previous_response = session_history.messages[-2]
            new_response = fix_message(fix_chain, last_response, previous_response, instruction)
            session_history.messages[-1] = new_response
            continue
        elif user_input.startswith("rewrite"):
            fixed = re.sub("^rewrite:?", "", user_input).strip()
            session_history.messages[-1] = AIMessage(fixed)
            continue
        elif user_input.startswith("chapter"):
            chapter_title = re.sub("^chapter:?", "", user_input).strip()
            final_summary = update_summary(summary_chain, context.story.summary, session_history.messages)
            if (context.prompts.chapter_summary_prompt):
                context.story.characters = update_characters(character_chain, context.story.characters, session_history.messages)

            if (context.prompts.chapter_summary_prompt):
                context.story.chapters.append(close_chapter(chapter_chain, chapter_title, final_summary))
            else:
                context.story.chapters.append(Chapter(title=chapter_title, summary=final_summary))
            session_history.messages = []
            context.story.summary = ""
            continue
        elif user_input.startswith("test"):
            struct_chars = make_characters(character_creation_chain, context.story.characters)
            print(struct_chars.model_dump_json())
            continue
        
        token_count = count_tokens_approximately(session_history.messages)
        print(token_count)
        if (token_count > HISTORY_MAX_TOKENS):
            pruned_messages, remaining_messages = trim(session_history.messages)
            messages_pruned = len(pruned_messages)
            print(f"\n* Pruned {messages_pruned} messages")
            if (messages_pruned > 0):
                session_history.messages = remaining_messages
                context.story.old_messages.extend(pruned_messages)
                context.story.summary = update_summary(summary_chain, context.story.summary, pruned_messages)
                if (context.prompts.chapter_summary_prompt):
                    context.story.characters = update_characters(character_chain, context.story.characters, pruned_messages)

        for chunk in chat_chain.stream({
            "system": context.prompts.base_prompt, 
            "input": user_input, 
            "characters": context.story.characters, 
            "summary": f"## Chapter {len(context.story.chapters) + 1}\n\n {context.story.summary}",
            "chapters": make_chapters(context.story.chapters)
        }):
            print(chunk.content, end="", flush=True)
            
if __name__ == "__main__":
    main()