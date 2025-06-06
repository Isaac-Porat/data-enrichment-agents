import os
import anthropic
from anthropic.types.message import Message
from dotenv import load_dotenv

from tools.ask_user import ask_user
from tools.tools import (
    create_column_schema,
    write_column_schema,
    read_column_schema,
    research_schema,
    use_tool
)

load_dotenv()

ANTHROPIC_KEY = os.getenv("ANTHROPIC_KEY")

client = anthropic.Anthropic()

def send_message_block(new_message_block: dict, messages_history: list[dict] = []):
    """Main function to send a message block to Claude and receive a response."""
    messages = messages_history.copy()
    messages.append(new_message_block)
    response = client.messages.create(
        model="claude-3-5-sonnet-20240620",
        max_tokens=1000,
        temperature=0.9,
        system="""You are a chat bot assisting with research for a company spreadsheet. Keep engaging the user until
        either research has been made, or the user decides to stop. Keep using the 'ask_user' tool until user says 'STOP'.""",
        tools=[
            create_column_schema,
            write_column_schema,
            read_column_schema,
            research_schema,
        ],
        messages=messages,
    )

    # Print the response.
    response_text = response.content[0].text
    print(f"System Response: {response_text}\n")

    # Append the message to the history.
    response_block = {
        "role": "assistant",
        "content": response.content,
    }
    messages.append(response_block)

    # Check if a tool is used and process the tool result.
    messages = check_and_use_tool(messages, response)
    return messages


def send_message(new_message: str, messages_history: list[dict] = []):
    """Wrapper function to send a new (text) message to Claude."""
    new_message_block = {
        "role": "user",
        "content": [{"type": "text", "text": new_message}],
    }
    return send_message_block(
        new_message_block=new_message_block, messages_history=messages_history
    )


def send_tool_result(
    tool_result: str, tool_use_id: str, messages_history: list[dict] = []
):
    """Wrapper function to send a tool result (output) back to Claude."""
    tool_response_block = {
        "role": "user",
        "content": [
            {
                "type": "tool_result",
                "tool_use_id": tool_use_id,
                "content": tool_result,
            }
        ],
    }

    return send_message_block(
        new_message_block=tool_response_block, messages_history=messages_history
    )

def check_and_use_tool(messages: list[dict], response: Message):
    if response.stop_reason == "tool_use":
        tool_use_content = next(
            block for block in response.content if block.type == "tool_use"
        )
        tool_result = use_tool(tool_use_content)

        # Print the tool result (highlighted in green for visibility).
        print(f"Using Tool [{tool_use_content.name}]: \033[32m{tool_result}\033[0m\n")

        # Send the tool result back to the API.
        send_tool_result(tool_result, tool_use_content.id, messages)

    return messages

if __name__ == "__main__":
    first_message = ask_user("Research?")
    messages_history = send_message(first_message)
