import os
import chainlit as cl
import boto3
import httpx
import re
import json
from typing import Optional, List, Dict, Any

# Initialize AWS clients
bedrock_agent_runtime = boto3.client(
    "bedrock-agent-runtime", region_name=os.environ.get("AWS_REGION", "us-east-1")
)

bedrock_runtime = boto3.client(
    "bedrock-runtime", region_name=os.environ.get("AWS_REGION", "us-east-1")
)

KNOWLEDGE_BASE_ID = os.environ.get("KNOWLEDGE_BASE_ID")
MODEL_ID = "us.anthropic.claude-sonnet-4-20250514-v1:0"
MCP_SERVER_URL = os.environ.get("MCP_SERVER_URL", "")

# Cache for MCP tools
_mcp_tools_cache = None


async def discover_mcp_tools() -> List[Dict[str, Any]]:
    """
    Discover available tools from the MCP server.

    Returns:
        List of tools in Bedrock tool specification format
    """
    global _mcp_tools_cache

    # Return cached tools if available
    if _mcp_tools_cache is not None:
        return _mcp_tools_cache

    if not MCP_SERVER_URL or MCP_SERVER_URL == "":
        return []

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Call MCP tools/list method
            payload = {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}

            response = await client.post(
                MCP_SERVER_URL,
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            result = response.json()

            # Extract tools from response
            tools = result.get("result", {}).get("tools", [])

            # Convert MCP tool format to Bedrock tool specification
            bedrock_tools = []
            for tool in tools:
                bedrock_tool = {
                    "toolSpec": {
                        "name": tool.get("name"),
                        "description": tool.get("description", ""),
                        "inputSchema": {"json": tool.get("inputSchema", {})},
                    }
                }
                bedrock_tools.append(bedrock_tool)

            # Cache the tools
            _mcp_tools_cache = bedrock_tools
            return bedrock_tools

    except Exception as e:
        cl.logger.error(f"Failed to discover MCP tools: {e}")
        return []


async def call_mcp_tool(tool_name: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
    """
    Call an MCP tool.

    Args:
        tool_name: Name of the tool to call
        tool_input: Input parameters for the tool

    Returns:
        Tool execution result
    """
    if not MCP_SERVER_URL or MCP_SERVER_URL == "":
        return {"error": "MCP server is not configured"}

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {"name": tool_name, "arguments": tool_input},
            }

            response = await client.post(
                MCP_SERVER_URL,
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            result = response.json()

            return result.get("result", {})

    except Exception as e:
        return {"error": str(e)}


def is_valid_recipe_format(text: str) -> bool:
    """
    Check if the text contains a properly formatted recipe.
    A valid recipe should have a title (starting with #) and required sections.

    Args:
        text: The text to validate

    Returns:
        True if the text appears to be a properly formatted recipe
    """
    # Check for title
    if not text.startswith("#"):
        return False

    # Check for ingredient section (supports both English and Polish)
    has_ingredients = bool(
        re.search(r"##\s*(Składniki|Ingredients)", text, re.IGNORECASE)
    )

    # Check for preparation section (supports both English and Polish)
    has_preparation = bool(
        re.search(
            r"##\s*(Sposób przygotowania|Preparation|Instructions|Steps)",
            text,
            re.IGNORECASE,
        )
    )

    return has_ingredients and has_preparation


async def create_recipe_via_mcp(recipe_name: str, recipe_content: str) -> dict:
    """
    Create a new recipe using the MCP server's create_recipe tool.

    Args:
        recipe_name: Name of the recipe
        recipe_content: Full content of the recipe in Markdown format

    Returns:
        Response from the MCP server with 'success' field at top level
    """
    # Check if MCP server is configured
    if not MCP_SERVER_URL or MCP_SERVER_URL == "":
        return {"error": "MCP server is not configured", "success": False}

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # MCP protocol requires calling tools via JSON-RPC
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": "create_recipe",
                    "arguments": {"name": recipe_name, "content": recipe_content},
                },
            }

            response = await client.post(
                MCP_SERVER_URL,
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            result = response.json()

            # Normalize response format - extract success from nested result if present
            if isinstance(result, dict) and "result" in result:
                nested_result = result["result"]
                if isinstance(nested_result, dict):
                    return {
                        "success": nested_result.get("success", False),
                        "error": nested_result.get("error"),
                        "path": nested_result.get("path"),
                    }

            return result
    except Exception as e:
        return {"error": str(e), "success": False}


@cl.on_chat_start
async def start():
    """Initialize the chat session."""
    welcome_message = (
        "👨‍🍳 Welcome to CookBook Chatbot! I'm your AI cooking assistant powered by AWS Bedrock.\n\n"
        "I can help you with:\n"
        "- Finding recipes from the cookbook\n"
        "- Answering cooking questions\n"
        "- Providing ingredient substitutions\n"
        "- Explaining cooking techniques\n"
    )

    # Add recipe creation feature only if MCP server is configured
    if MCP_SERVER_URL and MCP_SERVER_URL != "":
        welcome_message += "- Adding new recipes to the cookbook 📝\n"

    welcome_message += "\nWhat would you like to cook today?"

    await cl.Message(content=welcome_message).send()


@cl.on_message
async def main(message: cl.Message):
    """Handle incoming messages."""
    user_message = message.content

    # Send a temporary message while processing
    msg = cl.Message(content="")
    await msg.send()

    try:
        # Discover MCP tools
        mcp_tools = await discover_mcp_tools()

        # First, retrieve relevant context from Knowledge Base
        kb_context = ""
        try:
            kb_response = bedrock_agent_runtime.retrieve(
                knowledgeBaseId=KNOWLEDGE_BASE_ID,
                retrievalQuery={"text": user_message},
                retrievalConfiguration={
                    "vectorSearchConfiguration": {"numberOfResults": 5}
                },
            )

            # Extract retrieved content
            retrieved_results = kb_response.get("retrievalResults", [])
            if retrieved_results:
                kb_context = "\n\n".join(
                    [
                        f"Recipe context {i+1}:\n{result.get('content', {}).get('text', '')}"
                        for i, result in enumerate(retrieved_results)
                    ]
                )
        except Exception as e:
            cl.logger.warning(f"Knowledge Base retrieval failed: {e}")

        # System prompt
        system_prompt = [
            {
                "text": """You are a helpful cooking assistant with access to a cookbook knowledge base and recipe management tools.

Your capabilities:
1. Search and provide recipes from the cookbook
2. Answer cooking questions and provide advice
3. Use available tools to manage recipes (list, search, create, update)

When providing recipes, always format them clearly:

# Recipe Name

## Opis
Brief description

**Porcje:** [servings]
**Czas przygotowania:** [time]

## Składniki
- Ingredient list

## Sposób przygotowania
1. Step-by-step instructions

Always provide COMPLETE recipes with ALL ingredients and ALL steps.

If you have tools available, use them when appropriate:
- Use list_recipes or search_recipes to find recipes
- Use create_recipe to save new recipes the user wants to add
- Use update_recipe to modify existing recipes"""
            }
        ]

        # Prepare messages
        messages = [{"role": "user", "content": [{"text": user_message}]}]

        # Add KB context if available
        if kb_context:
            messages[0]["content"].insert(
                0, {"text": f"Relevant cookbook context:\n{kb_context}\n\n"}
            )

        # Prepare tool configuration
        tool_config = {}
        if mcp_tools:
            tool_config = {"tools": mcp_tools}

        # Call Bedrock Converse API with tool use
        max_iterations = 5
        iteration = 0

        while iteration < max_iterations:
            iteration += 1

            response = bedrock_runtime.converse(
                modelId=MODEL_ID,
                messages=messages,
                system=system_prompt,
                toolConfig=tool_config if tool_config else None,
            )

            # Extract response
            stop_reason = response.get("stopReason")
            output_message = response.get("output", {}).get("message", {})

            # Add assistant response to messages
            messages.append(output_message)

            # Check if tool use is requested
            if stop_reason == "tool_use":
                # Process tool calls
                tool_results = []

                for content_block in output_message.get("content", []):
                    if "toolUse" in content_block:
                        tool_use = content_block["toolUse"]
                        tool_name = tool_use.get("name")
                        tool_input = tool_use.get("input", {})
                        tool_use_id = tool_use.get("toolUseId")

                        cl.logger.info(
                            f"Calling tool: {tool_name} with input: {tool_input}"
                        )

                        # Call the MCP tool
                        tool_result = await call_mcp_tool(tool_name, tool_input)

                        # Format tool result
                        tool_results.append(
                            {
                                "toolResult": {
                                    "toolUseId": tool_use_id,
                                    "content": [{"json": tool_result}],
                                }
                            }
                        )

                # Add tool results to messages
                messages.append({"role": "user", "content": tool_results})

                # Continue the loop to get next response
                continue

            # If stop reason is end_turn or max_tokens, extract final response
            else:
                final_text = ""
                for content_block in output_message.get("content", []):
                    if "text" in content_block:
                        final_text += content_block["text"]

                msg.content = final_text
                await msg.update()
                break

        if iteration >= max_iterations:
            msg.content += "\n\n⚠️ Maximum tool iterations reached."
            await msg.update()

    except Exception as e:
        error_message = f"❌ Sorry, I encountered an error: {str(e)}\n\n"
        error_message += "Please make sure the Knowledge Base is properly set up and contains recipe documents."
        msg.content = error_message
        await msg.update()


if __name__ == "__main__":
    # This is useful for local testing
    pass
