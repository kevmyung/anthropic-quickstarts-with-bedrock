import asyncio
import base64
import os
import boto3
import subprocess
import traceback
from botocore.exceptions import BotoCoreError, ClientError

from datetime import datetime, timedelta
from enum import StrEnum
from functools import partial
from pathlib import PosixPath
from typing import cast, Dict, Any, List, Union

import httpx
import streamlit as st

from streamlit.delta_generator import DeltaGenerator

from computer_use_demo.loop import sampling_loop
from computer_use_demo.tools import ToolResult

DEFAULT_MODEL_NAME = "anthropic.claude-3-5-sonnet-20241022-v2:0"

CONFIG_DIR = PosixPath("~/.anthropic").expanduser()
API_KEY_FILE = CONFIG_DIR / "api_key"
STREAMLIT_STYLE = """
<style>
    /* Hide chat input while agent loop is running */
    .stApp[data-teststate=running] .stChatInput textarea,
    .stApp[data-test-script-state=running] .stChatInput textarea {
        display: none;
    }
     /* Hide the streamlit deploy button */
    .stAppDeployButton {
        visibility: hidden;
    }
</style>
"""

WARNING_TEXT = "⚠️ Security Alert: Never provide access to sensitive accounts or data, as malicious web content can hijack Claude's behavior"

class Sender(StrEnum):
    USER = "user"
    BOT = "assistant"
    TOOL = "tool"


def setup_state():
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "model" not in st.session_state:
        st.session_state.model = DEFAULT_MODEL_NAME
    if "auth_validated" not in st.session_state:
        st.session_state.auth_validated = False
    if "responses" not in st.session_state:
        st.session_state.responses = {}
    if "tools" not in st.session_state:
        st.session_state.tools = {}
    if "only_n_most_recent_images" not in st.session_state:
        st.session_state.only_n_most_recent_images = 10
    if "custom_system_prompt" not in st.session_state:
        st.session_state.custom_system_prompt = load_from_storage("system_prompt") or ""
    if "hide_images" not in st.session_state:
        st.session_state.hide_images = False


def _reset_model():
    st.session_state.model = DEFAULT_MODEL_NAME

async def main():
    """Render loop for streamlit"""
    setup_state()

    st.markdown(STREAMLIT_STYLE, unsafe_allow_html=True)

    st.title("Bedrock - Computer Use")

    if not os.getenv("HIDE_WARNING", False):
        st.warning(WARNING_TEXT)

    with st.sidebar:
        st.text_input("Model", key="model")

        st.number_input(
            "Only send N most recent images",
            min_value=0,
            key="only_n_most_recent_images",
            help="To decrease the total tokens sent, remove older screenshots from the conversation",
        )
        st.text_area(
            "Custom System Prompt Suffix",
            key="custom_system_prompt",
            help="Additional instructions to append to the system prompt. see computer_use_demo/loop.py for the base system prompt.",
            on_change=lambda: save_to_storage(
                "system_prompt", st.session_state.custom_system_prompt
            ),
        )
        st.checkbox("Hide screenshots", key="hide_images")

        if st.button("Reset", type="primary"):
            with st.spinner("Resetting..."):
                st.session_state.clear()
                setup_state()

                subprocess.run("pkill Xvfb; pkill tint2", shell=True)  # noqa: ASYNC221
                await asyncio.sleep(1)
                subprocess.run("./start_all.sh", shell=True)  # noqa: ASYNC221

    chat, http_logs = st.tabs(["Chat", "HTTP Exchange Logs"])
    new_message = st.chat_input(
        "Type a message to send to Claude to control the computer..."
    )

    with chat:
        # render past chats
        for message in st.session_state.messages:
            if isinstance(message["content"], str):
                _render_message(message["role"], message["content"])
            elif isinstance(message["content"], list):
                for block in message["content"]:
                    if isinstance(block, dict):
                        if "text" in block:
                            _render_message(message["role"], block["text"])
                        elif "image" in block:
                            _render_message(message["role"], block["image"])
                    else:
                        _render_message(message["role"], str(block))

        # render past http exchanges
        for identity, (request, response) in st.session_state.responses.items():
            _render_api_response(request, response, identity, http_logs)

        # render past chats
        if new_message:
            st.session_state.messages.append(
                {
                    "role": Sender.USER,
                    "content": [{"type": "text", "text": new_message}],
                }
            )
            _render_message(Sender.USER, {"type": "text", "text": new_message})

        try:
            most_recent_message = st.session_state["messages"][-1]
        except IndexError:
            return

        if most_recent_message["role"] is not Sender.USER:
            # we don't have a user message to respond to, exit early
            return

        with st.spinner("Running Agent..."):
            # run the agent sampling loop with the newest message
            st.session_state.messages = await sampling_loop(
                system_prompt_suffix=st.session_state.custom_system_prompt,
                model=st.session_state.model,
                messages=st.session_state.messages,
                output_callback=partial(_render_message, Sender.BOT),
                tool_output_callback=partial(
                    _tool_output_callback, tool_state=st.session_state.tools
                ),
                api_response_callback=partial(
                    _api_response_callback,
                    tab=http_logs,
                    response_state=st.session_state.responses,
                ),
                only_n_most_recent_images=st.session_state.only_n_most_recent_images,
            )


def load_from_storage(filename: str) -> str | None:
    """Load data from a file in the storage directory."""
    try:
        file_path = CONFIG_DIR / filename
        if file_path.exists():
            data = file_path.read_text().strip()
            if data:
                return data
    except Exception as e:
        st.write(f"Debug: Error loading {filename}: {e}")
    return None


def save_to_storage(filename: str, data: str) -> None:
    """Save data to a file in the storage directory."""
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        file_path = CONFIG_DIR / filename
        file_path.write_text(data)
        # Ensure only user can read/write the file
        file_path.chmod(0o600)
    except Exception as e:
        st.write(f"Debug: Error saving {filename}: {e}")


def _api_response_callback(
    request: Union[httpx.Request, List],
    response: Union[httpx.Response, object, None],
    error: Exception | None,
    tab: DeltaGenerator,
    response_state: dict[str, tuple[Union[httpx.Request, List], Union[httpx.Response, object, None]]],
):
    """
    Handle an API response by storing it to state and rendering it.
    """
    response_id = datetime.now().isoformat()
    response_state[response_id] = (request, response)
    if error:
        _render_error(error)
    _render_api_response(request, response, response_id, tab)



def _tool_output_callback(
    tool_output: ToolResult, tool_id: str, tool_state: dict[str, ToolResult]
):
    """Handle a tool output by storing it to state and rendering it."""
    tool_state[tool_id] = tool_output
    _render_message(Sender.TOOL, tool_output)


def _render_api_response(
    request: Union[httpx.Request, List],
    response: Union[httpx.Response, object, None],
    response_id: str,
    tab: DeltaGenerator,
):
    """Render an API response to a streamlit tab"""
    with tab:
        with st.expander(f"Request/Response ({response_id})"):
            newline = "\n\n"
            if isinstance(request, httpx.Request):
                st.markdown(
                    f"`{request.method} {request.url}`{newline}{newline.join(f'`{k}: {v}`' for k, v in request.headers.items())}"
                )
                st.json(request.read().decode())
            else:
                st.json(request)  # Assuming request is now a list or dict
            st.markdown("---")
            if isinstance(response, httpx.Response):
                st.markdown(
                    f"`{response.status_code}`{newline}{newline.join(f'`{k}: {v}`' for k, v in response.headers.items())}"
                )
                st.json(response.text)
            else:
                st.write(response)


def _render_error(error: Exception):
    if isinstance(error, (BotoCoreError, ClientError)):
        error_code = error.response['Error']['Code'] if hasattr(error, 'response') else 'Unknown'
        error_message = error.response['Error']['Message'] if hasattr(error, 'response') else str(error)
        body = f"AWS Bedrock API Error: {error_code}\n\n{error_message}"

        if error_code == 'ThrottlingException':
            retry_after = error.response.get('RetryAfter')
            if retry_after:
                body += f"\n\nRetry after: {retry_after} seconds"
    else:
        body = str(error)

    body += "\n\n**Traceback:**"
    lines = "\n".join(traceback.format_exception(type(error), error, error.__traceback__))
    body += f"\n\n```{lines}```"

    save_to_storage(f"error_{datetime.now().timestamp()}.md", body)
    st.error(f"**{error.__class__.__name__}**\n\n{body}", icon="🚨")


def _render_message(
    sender: Sender,
    message: str | Dict[str, Any] | ToolResult,
):
    """Convert input from the user or output from the agent to a streamlit message."""
    if not message:
        return

    with st.chat_message(sender):
        if isinstance(message, str):
            st.markdown(message)
        elif isinstance(message, dict):
            if message.get("type") == "text":
                st.write(message["text"])
            elif message.get("type") == "tool_use":
                st.code(f'Tool Use: {message["name"]}\nInput: {json.dumps(message["input"], indent=2)}')
            elif message.get("type") == "image":
                if not st.session_state.hide_images:
                    image_data = message["image"]["source"]["bytes"]
                    st.image(base64.b64decode(image_data))
            else:
                st.json(message)
        elif isinstance(message, ToolResult):
            if message.output:
                if message.__class__.__name__ == "CLIResult":
                    st.code(message.output)
                else:
                    st.markdown(message.output)
            if message.error:
                st.error(message.error)
            if message.base64_image and not st.session_state.hide_images:
                st.image(base64.b64decode(message.base64_image))
        else:
            st.write(f"Unexpected message type: {type(message)}")
            st.json(message)


if __name__ == "__main__":
    asyncio.run(main())
