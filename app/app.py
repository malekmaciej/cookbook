import os
import chainlit as cl
import boto3
from typing import Optional

# Initialize AWS clients
bedrock_agent_runtime = boto3.client(
    'bedrock-agent-runtime',
    region_name=os.environ.get('AWS_REGION', 'us-east-1')
)

bedrock_runtime = boto3.client(
    'bedrock-runtime',
    region_name=os.environ.get('AWS_REGION', 'us-east-1')
)

KNOWLEDGE_BASE_ID = os.environ.get('KNOWLEDGE_BASE_ID')
MODEL_ID = os.environ.get('BEDROCK_MODEL_ID', 'anthropic.claude-3-sonnet-20240229-v1:0')


@cl.on_chat_start
async def start():
    """Initialize the chat session."""
    await cl.Message(
        content="👨‍🍳 Welcome to CookBook Chatbot! I'm your AI cooking assistant powered by AWS Bedrock.\n\n"
                "I can help you with:\n"
                "- Finding recipes from the cookbook\n"
                "- Answering cooking questions\n"
                "- Providing ingredient substitutions\n"
                "- Explaining cooking techniques\n\n"
                "What would you like to cook today?"
    ).send()


@cl.on_message
async def main(message: cl.Message):
    """Handle incoming messages."""
    user_message = message.content
    
    # Send a temporary message while processing
    msg = cl.Message(content="")
    await msg.send()
    
    try:
        # Query the Knowledge Base using Retrieve and Generate
        response = bedrock_agent_runtime.retrieve_and_generate(
            input={
                'text': user_message
            },
            retrieveAndGenerateConfiguration={
                'type': 'KNOWLEDGE_BASE',
                'knowledgeBaseConfiguration': {
                    'knowledgeBaseId': KNOWLEDGE_BASE_ID,
                    'modelArn': f'arn:aws:bedrock:{os.environ.get("AWS_REGION", "us-east-1")}::foundation-model/{MODEL_ID}'
                }
            }
        )
        
        # Extract the generated response
        generated_text = response['output']['text']
        
        # Get citations if available
        citations = response.get('citations', [])
        
        # Format the response with citations
        response_text = generated_text
        
        if citations:
            response_text += "\n\n📚 **Sources:**\n"
            for idx, citation in enumerate(citations, 1):
                retrieved_references = citation.get('retrievedReferences', [])
                for ref in retrieved_references:
                    location = ref.get('location', {})
                    s3_location = location.get('s3Location', {})
                    uri = s3_location.get('uri', 'Unknown')
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
