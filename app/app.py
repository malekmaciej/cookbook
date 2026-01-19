import os
import chainlit as cl
import boto3
import httpx
import re
import json
from typing import Optional

# Initialize AWS clients
bedrock_agent_runtime = boto3.client(
    "bedrock-agent-runtime", region_name=os.environ.get("AWS_REGION", "us-east-1")
)

bedrock_runtime = boto3.client(
    "bedrock-runtime", region_name=os.environ.get("AWS_REGION", "us-east-1")
)

KNOWLEDGE_BASE_ID = os.environ.get("KNOWLEDGE_BASE_ID")
MODEL_ID = "us.anthropic.claude-sonnet-4-20250514-v1:0"
MCP_SERVER_URL = os.environ.get("MCP_SERVER_URL", "http://mcp-server.cookbook-chatbot.local:8000/mcp")


def is_add_recipe_request(user_message: str) -> bool:
    """
    Determine if the user message is a request to add a new recipe.
    
    Args:
        user_message: The user's message
        
    Returns:
        True if the message appears to be requesting to add a recipe
    """
    add_patterns = [
        r'\b(add|create|save|store|new)\s+(a\s+)?(recipe|przepis)',
        r'\b(dodaj|zapisz|nowy)\s+(przepis)',
        r'(want to|would like to|can I|please)\s+(add|create|save)',
        r'(save|store)\s+(this|my)\s+recipe',
    ]
    
    message_lower = user_message.lower()
    for pattern in add_patterns:
        if re.search(pattern, message_lower):
            return True
    return False


async def create_recipe_via_mcp(recipe_name: str, recipe_content: str) -> dict:
    """
    Create a new recipe using the MCP server's create_recipe tool.
    
    Args:
        recipe_name: Name of the recipe
        recipe_content: Full content of the recipe in Markdown format
        
    Returns:
        Response from the MCP server
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
                    "arguments": {
                        "name": recipe_name,
                        "content": recipe_content
                    }
                }
            }
            
            response = await client.post(
                MCP_SERVER_URL,
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            return response.json()
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
        # Check if this is a request to add a new recipe
        if is_add_recipe_request(user_message):
            # Check if MCP server is available
            if not MCP_SERVER_URL or MCP_SERVER_URL == "":
                msg.content = "⚠️ I'd love to help you add a recipe, but the recipe creation feature is not currently enabled. Please contact your administrator to enable the MCP server."
                await msg.update()
                return
            
            # Ask the user to provide recipe details if not already provided
            # Use Bedrock to extract or guide recipe creation
            system_prompt = """You are a helpful cooking assistant helping users add recipes to the cookbook.

When a user wants to add a recipe, guide them through the process:
1. If they haven't provided the recipe yet, ask them to provide the recipe name and full details
2. If they provide recipe details, format it properly in this structure:

# Recipe Name

## Opis
Brief description of the dish

**Porcje:** [number of servings]
**Czas przygotowania:** [preparation time]
**Temperatura pieczenia:** [temperature if applicable]

## Składniki
- List all ingredients with measurements

## Sposób przygotowania
1. Step-by-step instructions

Then indicate you're ready to save it by saying "I'll save this recipe to the cookbook now."

Always ensure recipes are complete with ALL ingredients and ALL preparation steps before saving."""

            # Use Bedrock to help format the recipe or guide the user
            response = bedrock_agent_runtime.retrieve_and_generate(
                input={"text": user_message},
                retrieveAndGenerateConfiguration={
                    "type": "KNOWLEDGE_BASE",
                    "knowledgeBaseConfiguration": {
                        "knowledgeBaseId": KNOWLEDGE_BASE_ID,
                        "modelArn": MODEL_ID,
                        "retrievalConfiguration": {
                            "vectorSearchConfiguration": {"numberOfResults": 3}
                        },
                        "generationConfiguration": {
                            "promptTemplate": {
                                "textPromptTemplate": f"{system_prompt}\n\nUser request: $query$\n\nExisting recipes for reference: $search_results$\n\nResponse:"
                            }
                        },
                    },
                },
            )

            generated_text = response["output"]["text"]
            
            # Check if the response contains a properly formatted recipe
            # If it does, try to save it to MCP server
            if "# " in generated_text and "## Składniki" in generated_text and "## Sposób przygotowania" in generated_text:
                # Extract recipe name from the first line
                lines = generated_text.split('\n')
                recipe_name = lines[0].lstrip('#').strip() if lines else "Unnamed Recipe"
                
                # Try to save the recipe via MCP
                result = await create_recipe_via_mcp(recipe_name, generated_text)
                
                if result.get("success", False) or (isinstance(result, dict) and result.get("result", {}).get("success", False)):
                    msg.content = f"✅ **Recipe Added Successfully!**\n\n{generated_text}\n\n📝 The recipe '{recipe_name}' has been saved to the cookbook and will be available after the next Knowledge Base sync."
                else:
                    error_msg = result.get("error", "Unknown error")
                    msg.content = f"⚠️ I formatted the recipe, but couldn't save it automatically:\n\n{generated_text}\n\n❌ Error: {error_msg}\n\nPlease try again or contact support."
            else:
                # Just guide the user
                msg.content = generated_text

            await msg.update()
            return

        # Normal recipe query flow
        # System prompt with formatting instructions
        system_prompt = """You are a helpful cooking assistant. When providing recipes, always format them in a clear, well-structured Markdown format with the following sections:

# Recipe Name

## Opis
Brief description of the dish

**Porcje:** [number of servings]
**Czas przygotowania:** [preparation time]
**Temperatura pieczenia:** [temperature if applicable]

## Składniki
- List all ingredients with measurements
- Group by category if applicable (e.g., "Ciasto", "Nadzienie")

## Sposób przygotowania
1. Step-by-step instructions
2. Each step on a new numbered line
3. Clear and concise directions

Include any tips, variations, or notes at the end if relevant.
Always provide the COMPLETE recipe with ALL ingredients and ALL steps, never summarize or skip parts."""

        # Query the Knowledge Base using Retrieve and Generate
        response = bedrock_agent_runtime.retrieve_and_generate(
            input={"text": user_message},
            retrieveAndGenerateConfiguration={
                "type": "KNOWLEDGE_BASE",
                "knowledgeBaseConfiguration": {
                    "knowledgeBaseId": KNOWLEDGE_BASE_ID,
                    "modelArn": MODEL_ID,
                    "retrievalConfiguration": {
                        "vectorSearchConfiguration": {"numberOfResults": 5}
                    },
                    "generationConfiguration": {
                        "promptTemplate": {
                            "textPromptTemplate": f"{system_prompt}\n\nUser question: $query$\n\nSearch results: $search_results$\n\nProvide a complete, well-formatted response:"
                        }
                    },
                },
            },
        )

        # Extract the generated response
        generated_text = response["output"]["text"]

        # Get citations if available
        citations = response.get("citations", [])

        # Format the response with citations
        response_text = generated_text

        if citations:
            response_text += "\n\n📚 **Sources:**\n"
            for idx, citation in enumerate(citations, 1):
                retrieved_references = citation.get("retrievedReferences", [])
                for ref in retrieved_references:
                    location = ref.get("location", {})
                    s3_location = location.get("s3Location", {})
                    uri = s3_location.get("uri", "Unknown")
                    response_text += f"{idx}. {uri}\n"

        msg.content = response_text
        await msg.update()

    except Exception as e:
        error_message = f"❌ Sorry, I encountered an error: {str(e)}\n\n"
        error_message += "Please make sure the Knowledge Base is properly set up and contains recipe documents."
        msg.content = error_message
        await msg.update()


if __name__ == "__main__":
    # This is useful for local testing
    pass
