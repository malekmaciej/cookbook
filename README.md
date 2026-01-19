# CookBook Chatbot 👨‍🍳

An AI-powered cooking assistant chatbot for your recipe collection, built with AWS Bedrock, Knowledge Bases, and Chainlit.

## 🆕 MCP Server

This repository now includes an **MCP (Model Context Protocol) Server** built with FastMCP 2.0 that provides programmatic access to recipes stored in a GitHub repository. The MCP server exposes tools and resources for listing, searching, getting, creating, and updating recipes via the standardized MCP protocol.

👉 **[See MCP Server Documentation](mcp-server/README.md)** for setup and usage instructions.

## Architecture

This project implements a serverless, scalable chatbot solution with the following AWS services:

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐     ┌─────────────────────┐
│   Internet  │────▶│  ALB + WAF   │────▶│   Cognito   │────▶│   ECS Fargate       │
│   Users     │     │  (Port 80)   │     │  (Auth)     │     │  - Chainlit App     │
└─────────────┘     └──────────────┘     └─────────────┘     │  - MCP Server (opt) │
                                                               └──────────┬──────────┘
                                                                          │
                                              ┌───────────────────────────┼────────────┐
                                              │                           │            │
                                              ▼                           ▼            ▼
                                    ┌─────────────────┐        ┌─────────────────┐   │
                                    │  AWS Bedrock    │        │   GitHub API    │   │
                                    │  - Claude Model │        │   (Recipes)     │   │
                                    │  - Knowledge    │        └─────────────────┘   │
                                    │    Base         │                              │
                                    └────────┬────────┘                              │
                                             │                                       │
                          ┌──────────────────┴──────────────┐                       │
                          ▼                                 ▼                       │
                    ┌──────────┐                    ┌──────────────┐               │
                    │    S3    │◀───────────────────│      S3      │◀──────────────┘
                    │ (Recipes)│                    │   (Vectors)  │
                    └──────────┘                    └──────────────┘
```

### Components

- **Application Load Balancer (ALB)**: Entry point for HTTPS traffic with SSL termination
- **AWS Cognito**: User authentication and authorization with AWS SSO integration
- **ECS Fargate**: Serverless container hosting for the Chainlit frontend
- **MCP Server** (Optional): Model Context Protocol server for programmatic recipe access via GitHub
  - Deployed as a separate ECS service in the same cluster
  - Registered with AWS Cloud Map for service discovery at `mcp-server.cookbook-chatbot.local`
- **AWS Cloud Map**: Service discovery for internal communication between ECS services
- **AWS Bedrock**: AI model (Claude 3) for natural language processing
- **Bedrock Knowledge Base**: RAG (Retrieval-Augmented Generation) system for recipe queries
- **Amazon S3**: Storage for recipe documents
- **Amazon S3 Vectors**: Vector storage and semantic search for embeddings
- **VPC**: Isolated network with public and private subnets
- **AWS Secrets Manager**: Secure storage for GitHub token used by MCP server

## Prerequisites

- AWS Account with appropriate permissions
- AWS CLI configured with credentials
- Terraform >= 1.5
- Docker installed locally
- Python 3.11+

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/malekmaciej/cookbook.git
cd cookbook
```

### 2. Prepare Your Recipe Documents

Place your recipe documents (PDF, TXT, MD, etc.) in a local folder. These will be uploaded to S3 after infrastructure deployment.

### 3. Configure Terraform Variables

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars` and update:
- `cognito_domain_prefix`: Must be globally unique (e.g., `cookbook-chatbot-yourname-12345`)
- `container_image`: Will be updated after building and pushing the Docker image
- `mcp_container_image`: Will be updated if deploying the MCP server
- `github_token`: Required for MCP server deployment (leave empty to skip MCP server)
- Other variables as needed for your environment

**Note**: The MCP server is optional. If you don't set `github_token`, only the Chainlit app will be deployed.

See [MCP Server Deployment Guide](terraform/MCP_SERVER_DEPLOYMENT.md) for detailed MCP server setup instructions.

### 4. Build and Push Docker Image

First, create an ECR repository:

```bash
aws ecr create-repository --repository-name cookbook-chatbot --region us-east-1
```

Build and push the Docker image:

```bash
cd ../app

# Get your AWS account ID
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Login to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin ${AWS_ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com

# Build the image
docker build -t cookbook-chatbot:latest .

# Tag the image
docker tag cookbook-chatbot:latest ${AWS_ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/cookbook-chatbot:latest

# Push the image
docker push ${AWS_ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/cookbook-chatbot:latest
```

Update `terraform.tfvars` with the ECR image URI:
```hcl
container_image = "<AWS_ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/cookbook-chatbot:latest"
```

**Optional: Build and Push MCP Server Image**

If you want to deploy the MCP server, also build and push its image:

```bash
cd ../mcp-server

# Get your AWS account ID
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Create ECR repository for MCP server
aws ecr create-repository --repository-name recipe-mcp-server --region us-east-1

# Build the MCP server image for ARM64 architecture
docker buildx build --platform linux/arm64 -t recipe-mcp-server:latest .

# Tag the image
docker tag recipe-mcp-server:latest ${AWS_ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/recipe-mcp-server:latest

# Push the image
docker push ${AWS_ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/recipe-mcp-server:latest
```

**Note**: Use `docker buildx build --platform linux/arm64` for ARM64 architecture. On ARM64 Mac/Linux, regular `docker build` works.

Update `terraform.tfvars` with the MCP server image URI and your GitHub token:
```hcl
mcp_container_image = "<AWS_ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/recipe-mcp-server:latest"
github_token = "ghp_your_github_token_here"
```

### 5. Deploy Infrastructure

```bash
cd ../terraform

# Initialize Terraform
terraform init

# Review the plan
terraform plan

# Apply the configuration
terraform apply
```

The deployment takes approximately 10-15 minutes.

### 6. Upload Recipe Documents

After deployment, upload your recipe documents to the S3 bucket:

```bash
# Get the bucket name from Terraform output
BUCKET_NAME=$(terraform output -raw s3_bucket_name)

# Upload recipes
aws s3 cp /path/to/your/recipes/ s3://${BUCKET_NAME}/ --recursive
```

### 7. Sync Knowledge Base

After uploading documents, trigger a sync of the Knowledge Base:

```bash
# Get the Knowledge Base ID and Data Source ID
KB_ID=$(terraform output -raw knowledge_base_id)

# Get the data source ID
DATA_SOURCE_ID=$(aws bedrock-agent list-data-sources \
  --knowledge-base-id ${KB_ID} \
  --query 'dataSourceSummaries[0].dataSourceId' \
  --output text)

# Start ingestion job
aws bedrock-agent start-ingestion-job \
  --knowledge-base-id ${KB_ID} \
  --data-source-id ${DATA_SOURCE_ID}
```

### 8. Access the Application

Get the ALB DNS name:

```bash
terraform output alb_dns_name
```

Open the URL in your browser. You'll be prompted to:
1. Create a Cognito user account
2. Verify your email
3. Login to access the chatbot

## Configuration

### Environment Variables

The Chainlit application uses the following environment variables (automatically configured by Terraform):

- `KNOWLEDGE_BASE_ID`: Bedrock Knowledge Base ID
- `AWS_REGION`: AWS region
- `BEDROCK_MODEL_ID`: Bedrock model to use

### Terraform Variables

See `terraform/variables.tf` for all configurable options:

- **aws_region**: AWS region (default: us-east-1)
- **environment**: Environment name (dev/staging/prod)
- **container_cpu**: CPU units for ECS task (default: 1024)
- **container_memory**: Memory in MB for ECS task (default: 2048)
- **desired_count**: Number of ECS tasks (default: 2)
- **bedrock_model_id**: Bedrock model ID

## Cost Estimation

Approximate monthly costs (us-east-1):

**Base Infrastructure:**
- **ECS Fargate (Chainlit)**: ~$30-50 (2 tasks, 1 vCPU, 2GB RAM)
- **ECS Fargate (MCP Server)**: ~$10-15 (1 task, 0.5 vCPU, 1GB RAM) - Optional
- **Application Load Balancer**: ~$20-25
- **NAT Gateway**: ~$30-40 (per AZ)
- **Bedrock**: Pay per request (varies with usage)
- **S3**: ~$1-5 (based on storage and vector operations)
- **AWS Secrets Manager**: ~$0.40/month - If MCP server deployed
- **AWS Cloud Map**: ~$1/month - If MCP server deployed

**Total**: 
- Without MCP Server: ~$80-120/month base cost + Bedrock usage
- With MCP Server: ~$92-138/month base cost + Bedrock usage

## Security Features

- ✅ VPC with public/private subnet isolation
- ✅ ECS tasks run in private subnets
- ✅ AWS Cognito authentication required
- ✅ ALB security groups restrict traffic
- ✅ S3 bucket encryption enabled
- ✅ IAM roles with least privilege
- ✅ CloudWatch logging enabled
- ✅ GitHub tokens stored in AWS Secrets Manager
- ✅ Service discovery for internal communication

## Maintenance

### Updating the Application

1. Make changes to `app/app.py`
2. Rebuild and push the Docker image
3. Update ECS service:

```bash
aws ecs update-service \
  --cluster cookbook-chatbot-cluster \
  --service cookbook-chatbot-service \
  --force-new-deployment
```

### Updating the MCP Server

If you have the MCP server deployed:

1. Make changes to `mcp-server/server.py`
2. Rebuild and push the Docker image
3. Update ECS service:

```bash
aws ecs update-service \
  --cluster cookbook-chatbot-cluster \
  --service cookbook-chatbot-mcp-server-service \
  --force-new-deployment
```

### Adding More Recipes

Simply upload new documents to S3 and trigger a Knowledge Base sync:

```bash
aws s3 cp new-recipe.pdf s3://${BUCKET_NAME}/
aws bedrock-agent start-ingestion-job \
  --knowledge-base-id ${KB_ID} \
  --data-source-id ${DATA_SOURCE_ID}
```

### Monitoring

- **ECS Logs**: Check CloudWatch Logs at `/ecs/cookbook-chatbot`
- **MCP Server Logs**: Check CloudWatch Logs at `/ecs/cookbook-chatbot-mcp-server` (if deployed)
- **ALB Metrics**: Monitor in CloudWatch under Application Load Balancer
- **Bedrock Usage**: Check AWS Cost Explorer
- **Service Discovery**: View registered services in AWS Cloud Map console

## MCP Server

The MCP (Model Context Protocol) Server provides programmatic access to recipes stored in a GitHub repository using the standardized MCP protocol. This enables chatbots and AI assistants to interact with recipes through well-defined tools and resources.

### Features

- **List Recipes**: Get all available recipes with metadata
- **Search Recipes**: Find recipes by name or content
- **Get Recipe**: Retrieve full recipe details
- **Create Recipe**: Add new recipes to the repository
- **Update Recipe**: Modify existing recipes
- **Resources**: Access recipe content via URI-based resources

### Quick Start

The MCP server can be deployed to ECS alongside the Chainlit chatbot application using Terraform.

**For ECS Deployment**:
1. Build and push the MCP server Docker image to ECR (see step 4 below)
2. Set the `github_token` variable in your `terraform.tfvars`
3. Run `terraform apply`

The MCP server will be deployed as a separate ECS service and registered with AWS Cloud Map for service discovery at `mcp-server.cookbook-chatbot.local:8000/mcp`.

See the [MCP Server Deployment Guide](terraform/MCP_SERVER_DEPLOYMENT.md) for complete deployment instructions.

**For Local Development**:
See the [MCP Server README](mcp-server/README.md) for detailed instructions on:
- Local development setup
- Docker deployment
- API usage examples

### Local Testing

```bash
cd mcp-server

# Set up environment
cp .env.example .env
# Edit .env with your GitHub token

# Run with Docker Compose
docker-compose up
```

The MCP server will be available at `http://localhost:8000/mcp`.

## Cleanup

To destroy all resources:

```bash
cd terraform
terraform destroy
```

**Note**: Manually delete the ECR repository if no longer needed:

```bash
aws ecr delete-repository --repository-name cookbook-chatbot --force
```

## Troubleshooting

### Issue: Can't access the application

- Verify ALB is healthy: Check target group health in AWS Console
- Check security groups allow traffic on port 80
- Verify Cognito user is confirmed

### Issue: Chatbot returns errors

- Check ECS logs in CloudWatch
- Verify Knowledge Base has completed ingestion
- Ensure IAM roles have proper Bedrock permissions

### Issue: Terraform apply fails

- Verify AWS credentials are configured
- Check you have necessary IAM permissions
- Ensure `cognito_domain_prefix` is globally unique

## Development

### Local Testing

Run the Chainlit app locally (requires AWS credentials):

```bash
cd app
pip install -r requirements.txt

# Set environment variables
export KNOWLEDGE_BASE_ID="your-kb-id"
export AWS_REGION="us-east-1"
export BEDROCK_MODEL_ID="anthropic.claude-3-sonnet-20240229-v1:0"

# Run the app
chainlit run app.py
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

See [LICENSE](LICENSE) file for details.

## Support

For issues and questions:
- Open an issue in this repository
- Check AWS Bedrock documentation
- Review Chainlit documentation

## Acknowledgments

- Built with [Chainlit](https://chainlit.io/)
- Powered by [AWS Bedrock](https://aws.amazon.com/bedrock/)
- Infrastructure as Code with [Terraform](https://www.terraform.io/)
