# MCP Server Quick Start Guide

This guide will help you get the Recipe MCP Server up and running in minutes.

## Prerequisites

- Python 3.11 or higher
- Docker (optional, for containerized deployment)
- GitHub Personal Access Token with repository access

## Option 1: Local Development (Python)

### Step 1: Install Dependencies

```bash
cd mcp-server
pip install -r requirements.txt
```

### Step 2: Configure Environment

Create a `.env` file from the example:

```bash
cp .env.example .env
```

Edit `.env` and add your GitHub token:

```bash
GITHUB_TOKEN=your_github_personal_access_token_here
GITHUB_REPO=malekmaciej/przepisy
RECIPES_PATH=
```

### Step 3: Run the Server

```bash
python server.py
```

The server will start on `http://localhost:8000/mcp`

### Step 4: Test the Server

You can test the server is running by accessing the endpoint:

```bash
curl http://localhost:8000/mcp
```

## Option 2: Docker Deployment

### Step 1: Configure Environment

Create a `.env` file as described above.

### Step 2: Run with Docker Compose

```bash
cd mcp-server
docker-compose up
```

Or build and run manually:

```bash
docker build -t recipe-mcp-server:latest .
docker run -d \
  -p 8000:8000 \
  -e GITHUB_TOKEN="your_token_here" \
  -e GITHUB_REPO="malekmaciej/przepisy" \
  --name recipe-mcp-server \
  recipe-mcp-server:latest
```

### Step 3: Check Logs

```bash
docker logs -f recipe-mcp-server
```

## Option 3: AWS ECS Deployment

### Prerequisites
- AWS CLI configured
- ECR repository created
- Existing ECS cluster (or create a new one)

### Step 1: Build and Push to ECR

```bash
# Get your AWS account ID
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Login to ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin \
  ${AWS_ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com

# Create ECR repository (if not exists)
aws ecr create-repository \
  --repository-name recipe-mcp-server \
  --region us-east-1

# Build and push
cd mcp-server
docker build -t recipe-mcp-server:latest .
docker tag recipe-mcp-server:latest \
  ${AWS_ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/recipe-mcp-server:latest
docker push ${AWS_ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/recipe-mcp-server:latest
```

### Step 2: Create ECS Task Definition

Create a file `task-definition.json`:

```json
{
  "family": "recipe-mcp-server",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "256",
  "memory": "512",
  "containerDefinitions": [
    {
      "name": "recipe-mcp-server",
      "image": "<AWS_ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/recipe-mcp-server:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "GITHUB_REPO",
          "value": "malekmaciej/przepisy"
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
      ],
      "secrets": [
        {
          "name": "GITHUB_TOKEN",
          "valueFrom": "arn:aws:secretsmanager:us-east-1:<ACCOUNT_ID>:secret:github-token"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/recipe-mcp-server",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ],
  "executionRoleArn": "arn:aws:iam::<ACCOUNT_ID>:role/ecsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::<ACCOUNT_ID>:role/ecsTaskRole"
}
```

Register the task definition:

```bash
aws ecs register-task-definition --cli-input-json file://task-definition.json
```

### Step 3: Create ECS Service

```bash
aws ecs create-service \
  --cluster your-cluster-name \
  --service-name recipe-mcp-server \
  --task-definition recipe-mcp-server \
  --desired-count 1 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-xxx],securityGroups=[sg-xxx],assignPublicIp=ENABLED}"
```

## Using the MCP Server

Once the server is running, you can connect to it using any MCP-compatible client.

### Available Tools

1. **list_recipes()** - Get all recipes
2. **search_recipes(query)** - Search for recipes
3. **get_recipe(path)** - Get a specific recipe
4. **create_recipe(name, content, path?)** - Create a new recipe
5. **update_recipe(path, content, message?)** - Update a recipe

### Available Resources

1. **recipe://list** - List of all recipes
2. **recipe://{path}** - Content of a specific recipe

### Example: Using with Claude Desktop

Add to your Claude Desktop config:

```json
{
  "mcpServers": {
    "recipes": {
      "url": "http://localhost:8000/mcp",
      "transport": "streamable-http"
    }
  }
}
```

## Troubleshooting

### Server won't start

**Error**: `GITHUB_TOKEN environment variable not set`

**Solution**: Make sure you've set the `GITHUB_TOKEN` in your `.env` file or environment.

### Connection refused

**Error**: Cannot connect to `http://localhost:8000/mcp`

**Solution**: Check that the server is running and the port is not blocked by firewall.

### GitHub API rate limiting

**Error**: API rate limit exceeded

**Solution**: The server implements rate limiting protection. Wait a few minutes before retrying. For production, consider implementing caching.

### Import errors

**Error**: `ModuleNotFoundError: No module named 'fastmcp'`

**Solution**: Install dependencies:
```bash
pip install -r requirements.txt
```

## Next Steps

- Read the [full documentation](README.md)
- Explore the [sample recipes](../sample-recipes/)
- Configure for production deployment
- Set up monitoring and logging

## Getting Help

- Check the [README](README.md) for detailed documentation
- Review [GitHub Issues](https://github.com/malekmaciej/cookbook/issues)
- See the [main documentation](../README.md)
