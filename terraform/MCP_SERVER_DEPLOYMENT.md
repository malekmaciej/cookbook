# MCP Server Deployment Guide

This guide explains how to deploy the MCP server alongside the Chainlit chatbot application using the Terraform configuration.

## Overview

The MCP (Model Context Protocol) server has been added to the Terraform configuration as an additional ECS service. It runs in the same ECS cluster as the Chainlit app and is registered with AWS Cloud Map for service discovery.

## Architecture

- **ECS Cluster**: Both the Chainlit app and MCP server run in the same ECS cluster
- **Service Discovery**: The MCP server is registered with AWS Cloud Map, making it discoverable at `mcp-server.cookbook-chatbot.local`
- **Networking**: The MCP server runs in private subnets and can communicate with other ECS tasks via internal service discovery
- **Security**: GitHub token is stored securely in AWS Secrets Manager
- **Logging**: MCP server logs are sent to CloudWatch Logs at `/ecs/cookbook-chatbot-mcp-server`

## Prerequisites

Before deploying the MCP server:

1. **GitHub Token**: Create a GitHub personal access token with repository access
2. **Docker Image**: Build and push the MCP server Docker image to ECR

## Building and Pushing the MCP Server Image

```bash
# Navigate to the mcp-server directory
cd mcp-server

# Get your AWS account ID
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

## Configuration Variables

Add these variables to your `terraform.tfvars` file:

```hcl
# Required: GitHub token for MCP server to access recipe repository
github_token = "ghp_your_github_token_here"

# Required: MCP server container image
mcp_container_image = "<AWS_ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/recipe-mcp-server:latest"

# Optional: Customize GitHub repository (default: malekmaciej/przepisy)
github_repo = "malekmaciej/przepisy"

# Optional: Path within the repository for recipes (default: "")
recipes_path = ""

# Optional: MCP server resources (defaults shown)
mcp_container_cpu    = 512   # 0.5 vCPU
mcp_container_memory = 1024  # 1 GB RAM
mcp_desired_count    = 1     # Number of MCP server tasks
```

## Deployment

1. Update your `terraform.tfvars` with the required variables (see above)

2. Deploy the infrastructure:
```bash
cd terraform
terraform init
terraform plan
terraform apply
```

The MCP server will only be deployed if `github_token` is provided. If `github_token` is empty, only the Chainlit app will be deployed.

## Accessing the MCP Server

### From within the VPC (ECS Tasks)

The MCP server is accessible via service discovery:

- **DNS Name**: `mcp-server.cookbook-chatbot.local`
- **Port**: 8000
- **Endpoint**: `/mcp`
- **Full URL**: `http://mcp-server.cookbook-chatbot.local:8000/mcp`

### From the Chainlit App

The Chainlit app can connect to the MCP server using the internal DNS name:

```python
import httpx

# Connect to MCP server via service discovery
mcp_url = "http://mcp-server.cookbook-chatbot.local:8000/mcp"
response = httpx.get(mcp_url)
```

## Outputs

After deployment, you can view the MCP server information:

```bash
# Get MCP server service name
terraform output mcp_server_service_name

# Get MCP server task name
terraform output mcp_server_task_name

# Get service discovery namespace
terraform output service_discovery_namespace

# Get MCP server DNS name
terraform output mcp_server_dns
```

## Monitoring

### CloudWatch Logs

View MCP server logs in CloudWatch:

```bash
aws logs tail /ecs/cookbook-chatbot-mcp-server --follow
```

### ECS Service Status

Check the MCP server service status:

```bash
aws ecs describe-services \
  --cluster cookbook-chatbot-cluster \
  --services cookbook-chatbot-mcp-server-service
```

### Service Discovery

Check service discovery registrations:

```bash
aws servicediscovery list-services \
  --filters Name=NAMESPACE_ID,Values=$(terraform output -raw service_discovery_namespace | cut -d. -f1)
```

## Updating the MCP Server

To update the MCP server:

1. Build and push a new Docker image to ECR
2. Update the ECS service:

```bash
aws ecs update-service \
  --cluster cookbook-chatbot-cluster \
  --service cookbook-chatbot-mcp-server-service \
  --force-new-deployment
```

## Disabling the MCP Server

To disable the MCP server deployment without destroying other resources:

1. Remove or set `github_token = ""` in `terraform.tfvars`
2. Run `terraform apply`

This will remove the MCP server resources while keeping the Chainlit app and other infrastructure intact.

## Security Considerations

1. **GitHub Token**: The token is stored in AWS Secrets Manager and never exposed in logs
2. **Network Isolation**: The MCP server runs in private subnets with no direct internet access
3. **IAM Permissions**: The ECS task execution role has minimal permissions to read the secret
4. **Logging**: All MCP server activity is logged to CloudWatch

## Troubleshooting

### MCP Server Not Starting

1. Check CloudWatch logs for errors:
   ```bash
   aws logs tail /ecs/cookbook-chatbot-mcp-server --follow
   ```

2. Verify the GitHub token is valid and has repository access

3. Check ECS task status:
   ```bash
   aws ecs describe-tasks \
     --cluster cookbook-chatbot-cluster \
     --tasks $(aws ecs list-tasks --cluster cookbook-chatbot-cluster --service-name cookbook-chatbot-mcp-server-service --query 'taskArns[0]' --output text)
   ```

### Service Discovery Not Working

1. Verify the Cloud Map namespace exists:
   ```bash
   aws servicediscovery list-namespaces
   ```

2. Check service registration:
   ```bash
   aws servicediscovery discover-instances \
     --namespace-name cookbook-chatbot.local \
     --service-name mcp-server
   ```

3. Verify security group allows internal traffic between ECS tasks

### Cannot Access MCP Server from Chainlit App

1. Ensure both services are in the same VPC
2. Verify security group rules allow traffic on port 8000
3. Check that the MCP server is healthy and running
4. Test DNS resolution from within the VPC

## Cost Considerations

The MCP server adds minimal cost to the infrastructure:

- **ECS Fargate**: ~$10-15/month (1 task, 0.5 vCPU, 1GB RAM)
- **AWS Secrets Manager**: ~$0.40/month
- **CloudWatch Logs**: ~$0.50-1/month (based on log volume)
- **Cloud Map**: ~$1/month (1 namespace + 1 service)

**Total Additional Cost**: ~$12-18/month
