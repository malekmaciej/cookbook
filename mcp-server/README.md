# Recipe MCP Server

A Model Context Protocol (MCP) server built with FastMCP 2.0 that provides tools and resources to interact with recipes stored in a GitHub repository.

## Overview

This MCP server exposes recipe management functionality via the MCP protocol, allowing chatbots and AI assistants to:
- List all available recipes
- Search for recipes by name or content
- Get full recipe details
- Create new recipes
- Update existing recipes

## Features

### Tools

The server provides the following MCP tools:

1. **list_recipes()** - Get a list of all available recipes with metadata
2. **search_recipes(query)** - Search for recipes by name or content
3. **get_recipe(path)** - Get the full content of a specific recipe
4. **create_recipe(name, content, path?)** - Create a new recipe in the repository
5. **update_recipe(path, content, message?)** - Update an existing recipe

### Resources

The server exposes the following MCP resources:

1. **recipe://list** - A formatted text list of all recipes
2. **recipe://{path}** - The content of a specific recipe by path

## Configuration

The server is configured via environment variables:

### Required

- `GITHUB_TOKEN` - GitHub personal access token with repository access

### Optional

- `GITHUB_REPO` - Target GitHub repository (default: `malekmaciej/przepisy`)
- `RECIPES_PATH` - Root path in the repo for recipes (default: `""` - repository root)
- `MCP_HOST` - Server host (default: `0.0.0.0`)
- `MCP_PORT` - Server port (default: `8000`)
- `MCP_PATH` - MCP endpoint path (default: `/mcp`)

## Local Development

### Prerequisites

- Python 3.11+
- GitHub personal access token

### Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set environment variables:
```bash
export GITHUB_TOKEN="your_github_token"
export GITHUB_REPO="malekmaciej/przepisy"
```

3. Run the server:
```bash
python server.py
```

The server will start on `http://localhost:8000/mcp` by default.

### Testing

You can test the MCP server using the MCP Inspector or by connecting it to a compatible MCP client.

Example using curl to test the endpoint:
```bash
# Health check
curl http://localhost:8000/mcp

# List available methods (once connected via MCP client)
```

## Docker Deployment

### Build the Docker image

```bash
docker build -t recipe-mcp-server:latest .
```

### Run with Docker

```bash
docker run -d \
  -p 8000:8000 \
  -e GITHUB_TOKEN="your_github_token" \
  -e GITHUB_REPO="malekmaciej/przepisy" \
  --name recipe-mcp-server \
  recipe-mcp-server:latest
```

## ECS Deployment

The MCP server is designed to run on AWS ECS Fargate alongside the existing Chainlit chatbot application.

### Environment Variables for ECS

In your ECS task definition, set:

```json
{
  "name": "GITHUB_TOKEN",
  "value": "your_github_token_from_secrets_manager"
},
{
  "name": "GITHUB_REPO",
  "value": "malekmaciej/przepisy"
},
{
  "name": "RECIPES_PATH",
  "value": ""
},
{
  "name": "MCP_HOST",
  "value": "0.0.0.0"
},
{
  "name": "MCP_PORT",
  "value": "8000"
},
{
  "name": "MCP_PATH",
  "value": "/mcp"
}
```

### Deployment Steps

1. **Build and push Docker image to ECR:**
```bash
# Get AWS account ID
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Login to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin ${AWS_ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com

# Create ECR repository (if not exists)
aws ecr create-repository --repository-name recipe-mcp-server --region us-east-1

# Build and tag image
docker build -t recipe-mcp-server:latest .
docker tag recipe-mcp-server:latest ${AWS_ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/recipe-mcp-server:latest

# Push image
docker push ${AWS_ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/recipe-mcp-server:latest
```

2. **Update ECS task definition to include MCP server container**

3. **Configure ALB to route `/mcp` traffic to MCP server**

4. **Deploy to ECS**

## Usage Examples

### Listing Recipes

Call the `list_recipes` tool to get all available recipes:

```python
# Returns a list of recipe metadata
[
  {
    "name": "chocolate-chip-cookies.md",
    "path": "chocolate-chip-cookies.md",
    "size": 1234,
    "sha": "abc123..."
  },
  ...
]
```

### Searching for Recipes

Call the `search_recipes` tool with a query:

```python
search_recipes(query="chocolate")
# Returns recipes containing "chocolate" in name or content
```

### Getting a Recipe

Call the `get_recipe` tool with a recipe path:

```python
get_recipe(path="chocolate-chip-cookies.md")
# Returns:
{
  "name": "Chocolate Chip Cookies",
  "path": "chocolate-chip-cookies.md",
  "content": "# Chocolate Chip Cookies\n\n..."
}
```

### Creating a Recipe

Call the `create_recipe` tool:

```python
create_recipe(
  name="New Recipe",
  content="# New Recipe\n\n## Ingredients\n..."
)
# Creates a new recipe file
```

### Updating a Recipe

Call the `update_recipe` tool:

```python
update_recipe(
  path="chocolate-chip-cookies.md",
  content="# Updated Recipe\n\n...",
  message="Update recipe instructions"
)
# Updates the existing recipe
```

## Architecture

The MCP server is built on:
- **FastMCP 2.0** - High-performance MCP server framework
- **PyGithub** - GitHub API client for Python
- **Streamable HTTP Transport** - Modern HTTP-based MCP protocol

The server runs as a stateless HTTP service, making it ideal for cloud deployment on ECS.

## Security

- GitHub token should be stored securely (e.g., AWS Secrets Manager)
- The server validates all inputs before making GitHub API calls
- Use IAM roles for ECS tasks to manage AWS permissions
- Consider implementing rate limiting for production deployments

## Troubleshooting

### Server won't start
- Check that `GITHUB_TOKEN` is set correctly
- Verify the token has repository access permissions
- Check that `GITHUB_REPO` exists and is accessible

### Tools returning errors
- Verify repository path exists
- Check token permissions for write operations (create/update)
- Review server logs for detailed error messages

### Connection issues
- Ensure port 8000 is accessible
- Check firewall/security group settings
- Verify MCP client is using correct endpoint URL

## License

See [LICENSE](../LICENSE) file for details.
