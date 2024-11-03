"""
Agentic sampling loop that calls the Anthropic API and local implementation of anthropic-defined computer use tools.
"""
import boto3
import platform
from collections.abc import Callable
from datetime import datetime
from enum import StrEnum
from typing import Any, Callable, List, Dict, Union
import streamlit as st
import httpx
import ast

from .tools import BashTool, ComputerTool, EditTool, ToolCollection, ToolResult

COMPUTER_USE_BETA_FLAG = "computer-use-2024-10-22"
# PROMPT_CACHING_BETA_FLAG = "prompt-caching-2024-07-31"


# This system prompt is optimized for the Docker environment in this repository and
# specific tool combinations enabled.
# We encourage modifying this system prompt to ensure the model has context for the
# environment it is running in, and to provide any additional information that may be
# helpful for the task at hand.
SYSTEM_PROMPT = f"""<SYSTEM_CAPABILITY>
* You are utilising an Ubuntu virtual machine using {platform.machine()} architecture with internet access.
* You can feel free to install Ubuntu applications with your bash tool. Use curl instead of wget.
* To open firefox, please just click on the firefox icon.  Note, firefox-esr is what is installed on your system.
* Using bash tool you can start GUI applications, but you need to set export DISPLAY=:1 and use a subshell. For example "(DISPLAY=:1 xterm &)". GUI apps run with bash tool will appear within your desktop environment, but they may take some time to appear. Take a screenshot to confirm it did.
* When using your bash tool with commands that are expected to output very large quantities of text, redirect into a tmp file and use str_replace_editor or `grep -n -B <lines before> -A <lines after> <query> <filename>` to confirm output.
* When viewing a page it can be helpful to zoom out so that you can see everything on the page.  Either that, or make sure you scroll down to see everything before deciding something isn't available.
* When using your computer function calls, they take a while to run and send back to you.  Where possible/feasible, try to chain multiple of these calls all into one function calls request.
* The current date is {datetime.today().strftime('%A, %B %-d, %Y')}.
</SYSTEM_CAPABILITY>

<IMPORTANT>
* When using Firefox, if a startup wizard appears, IGNORE IT.  Do not even click "skip this step".  Instead, click on the address bar where it says "Search or enter address", and enter the appropriate search term or URL there.
* If the item you are looking at is a pdf, if after taking a single screenshot of the pdf it seems that you want to read the entire document instead of trying to continue to read the pdf from your screenshots + navigation, determine the URL, use curl to download the pdf, install and use pdftotext to convert it to a text file, and then read that text file directly with your StrReplaceEditTool.
</IMPORTANT>"""

async def sampling_loop(
    *,
    model: str,
    system_prompt_suffix: str,
    messages: List[Dict[str, Any]],
    output_callback: Callable[[Dict[str, Any]], None],
    tool_output_callback: Callable[[Any, str], None],
    api_response_callback: Callable[[Any, Any, Exception | None], None],
    only_n_most_recent_images: int | None = None,
    max_tokens: int = 4096,
    temperature: float = 0.7,
    top_p: float = 1.0,
):
    """
    Agentic sampling loop for the assistant/tool interaction of computer use.
    """

    bedrock_client = boto3.client('bedrock-runtime', region_name='us-west-2')
    tool_collection = ToolCollection(
        ComputerTool(),
        BashTool(),
        EditTool(),
    )
    system = f"{SYSTEM_PROMPT}{' ' + system_prompt_suffix if system_prompt_suffix else ''}"


    while True: 
        if only_n_most_recent_images:
            _maybe_filter_to_n_most_recent_images(
                messages,
                only_n_most_recent_images,
                min_removal_threshold=10,
            )

        bedrock_messages = _prepare_bedrock_messages(messages)

        try:
            response = bedrock_client.converse(
                modelId=model,
                messages=bedrock_messages,
                system=[{"text": system}],
                inferenceConfig={
                    "maxTokens": max_tokens,
                    "temperature": temperature,
                    "topP": top_p,
                },
                additionalModelRequestFields={
                    "tools": [
                        {
                            "type": "computer_20241022",
                            "name": "computer",
                            "display_height_px": 768,
                            "display_width_px": 1024,
                            "display_number": 0
                        },
                        {
                            "type": "bash_20241022",
                            "name": "bash",

                        },
                        {
                            "type": "text_editor_20241022",
                            "name": "str_replace_editor",
                        }
                    ],
                    "anthropic_beta": ["computer-use-2024-10-22"]
                },
                toolConfig={
                    'tools': [
                        {
                            'toolSpec': {
                                'name': 'dummy_tool',
                                "description": "Never use this tool.",
                                'inputSchema': {
                                    'json': {
                                        'type': 'object'
                                    }
                                }
                            }
                        }
                    ]
                }
            )
        except Exception as e:
            api_response_callback(bedrock_messages, None, e)
            return messages

        api_response_callback(bedrock_messages, response, None)

        response_content = response['output']['message']['content']
        messages.append({"role": "assistant", "content": response_content})
        
        tool_result_content = []
        for content_block in response_content:
            output_callback(content_block)
            if content_block.get("toolUse"):
                result = await tool_collection.run(
                    name=content_block["toolUse"]["name"],
                    tool_input=content_block["toolUse"]["input"],
                )
                tool_result = _make_api_tool_result(result, content_block["toolUse"]["toolUseId"])
                tool_result_content.append(tool_result)
                tool_output_callback(result, content_block["toolUse"]["toolUseId"])

        if not tool_result_content:
            return messages

        messages.append({"role": "user", "content": tool_result_content})


def _prepare_bedrock_messages(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    bedrock_messages = []
    for msg in messages:
        bedrock_msg = {"role": msg["role"], "content": []}
        if isinstance(msg["content"], list):
            for content in msg["content"]:
                if isinstance(content, dict):
                    if "toolResult" in content:
                        tool_result = content["toolResult"]
                        processed_content = _process_tool_result_content(tool_result["content"])
                        bedrock_msg["content"].append({
                            "toolResult": {
                                "toolUseId": tool_result["toolUseId"],
                                "content": processed_content,
                                "status": tool_result.get("status", "success")
                            }
                        })
                    elif "text" in content:
                        bedrock_msg["content"].append({"text": content["text"]})
                    elif "image" in content:
                        image_data = content["image"]
                        if isinstance(image_data, str) and image_data.startswith("data:image/"):
                            _, base64_data = image_data.split(',', 1)
                        elif isinstance(image_data, dict) and "source" in image_data:
                            base64_data = image_data["source"].get("bytes")
                        else:
                            base64_data = base64.b64encode(image_data).decode('utf-8')

                        bedrock_msg["content"].append({
                            "image": {
                                "format": 'png',
                                "source": {"bytes": base64_data}
                            }
                        })       
                    elif "toolUse" in content:
                        bedrock_msg["content"].append({
                            "toolUse": {
                                "toolUseId": content["toolUse"]["toolUseId"],
                                "name": content["toolUse"]["name"],
                                "input": content["toolUse"]["input"]
                            }
                        })
                    else:
                        bedrock_msg["content"].append(content)
                else:
                    bedrock_msg["content"].append({"text": str(content)})
        elif isinstance(msg["content"], str):
            bedrock_msg["content"].append({"text": msg["content"]})

        bedrock_messages.append(bedrock_msg)
    return bedrock_messages


def _process_image_bytes(image_bytes):
    if isinstance(image_bytes, str):
        if image_bytes.startswith("b'") or image_bytes.startswith('b"'):
            return ast.literal_eval(image_bytes)
        return image_bytes.encode('utf-8')
    return image_bytes

def _process_tool_result_content(content):
    processed_content = []
    for item in content:
        if isinstance(item, dict):
            if "json" in item:
                processed_content.append({"text": json.dumps(item["json"])})
            elif "text" in item:
                processed_content.append({"text": item["text"]})
            elif "base64_image" in item:
                image_bytes = base64.b64decode(item["base64_image"])
                processed_content.append({
                    "image": {
                        "format": 'png'|'jpeg', 
                        "source": {"bytes": image_bytes}
                    }
                })
    return processed_content


def _maybe_filter_to_n_most_recent_images(
    messages: List[Dict[str, Any]],
    images_to_keep: int,
    min_removal_threshold: int,
):
    """
    With the assumption that images are screenshots that are of diminishing value as
    the conversation progresses, remove all but the final `images_to_keep` tool_result
    images in place, with a chunk of min_removal_threshold to reduce the amount we
    break the implicit prompt cache.
    """
    if images_to_keep is None:
        return messages

    tool_result_blocks = [
        item
        for message in messages
        for item in (
            message["content"] if isinstance(message["content"], list) else []
        )
        if isinstance(item, dict) and item.get("type") == "tool_result"
    ]

    total_images = sum(
        1
        for tool_result in tool_result_blocks
        for content in tool_result.get("content", [])
        if isinstance(content, dict) and content.get("type") == "image"
    )

    images_to_remove = total_images - images_to_keep
    # for better cache behavior, we want to remove in chunks
    images_to_remove -= images_to_remove % min_removal_threshold

    for tool_result in tool_result_blocks:
        if isinstance(tool_result.get("content"), list):
            new_content = []
            for content in tool_result.get("content", []):
                if isinstance(content, dict) and content.get("type") == "image":
                    if images_to_remove > 0:
                        images_to_remove -= 1
                        continue
                new_content.append(content)
            tool_result["content"] = new_content


def _response_to_params(
    response: Dict[str, Any]
) -> List[Dict[str, Any]]:
    res = []
    for block in response.get("content", []):
        if block["type"] == "text":
            res.append({"type": "text", "text": block["text"]})
        elif block["type"] == "tool_use":
            res.append({
                "type": "tool_use",
                "id": block["id"],
                "name": block["name"],
                "input": block["input"]
            })
    return res


def _make_api_tool_result(result: Any, tool_use_id: str) -> Dict[str, Any]:
    tool_result_content = []
    status = "success"
    if result.error:
        status = "error"
        tool_result_content.append({"text": _maybe_prepend_system_tool_result(result, result.error)})
    else:
        if result.output:
            tool_result_content.append({"text": _maybe_prepend_system_tool_result(result, result.output)})
        if result.base64_image:
            tool_result_content.append({
                "image": {
                    "format": "png",
                    "source": {
                        "bytes": result.base64_image#.encode()
                    }
                }
            })
    return {
        "toolResult": {
            "toolUseId": tool_use_id,
            "content": tool_result_content,
            "status": status
        }
    }

def _maybe_prepend_system_tool_result(result: Any, result_text: str):
    if result.system:
        result_text = f"<system>{result.system}</system>\n{result_text}"
    return result_text
