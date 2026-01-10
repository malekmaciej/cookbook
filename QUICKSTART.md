# CookBook Chatbot - Quick Start Guide

This is a quick reference for deploying the CookBook Chatbot infrastructure.

## What You Have

A complete Infrastructure-as-Code (IaC) solution for a cooking recipe chatbot with:

- **Frontend**: Chainlit web application
- **Backend**: AWS Bedrock with Claude 3 model
- **Knowledge Base**: AWS Bedrock Knowledge Base with RAG
- **Storage**: S3 for recipes, OpenSearch Serverless for vectors
- **Auth**: AWS Cognito with SSO support
- **Hosting**: ECS Fargate with Application Load Balancer
- **Network**: VPC with public/private subnets, NAT Gateways

## File Structure

```
cookbook/
├── app/                          # Chainlit application
│   ├── app.py                   # Main application code
│   ├── Dockerfile               # Container image definition
│   ├── requirements.txt         # Python dependencies
│   ├── chainlit.md             # Welcome message
│   ├── .chainlit/
│   │   └── config.toml         # Chainlit configuration
│   └── .dockerignore           # Docker build exclusions
├── terraform/                   # Infrastructure as Code
│   ├── main.tf                 # Main infrastructure resources
│   ├── variables.tf            # Input variables
│   ├── outputs.tf              # Output values
│   ├── versions.tf             # Provider versions
│   └── terraform.tfvars.example # Example configuration
├── docs/                        # Documentation
│   ├── ARCHITECTURE.md         # Architecture details
│   ├── DEPLOYMENT.md           # Step-by-step deployment
│   └── BUILD.md                # Build and CI/CD guide
└── README.md                    # Project overview
```

## Prerequisites

- [ ] AWS Account with admin access
- [ ] AWS CLI installed and configured
- [ ] Terraform >= 1.5 installed
- [ ] Docker installed
- [ ] Python 3.11+ (for local testing)

## Quick Deployment (5 Steps)

### 1. Enable Bedrock Models

Go to AWS Console → Bedrock → Model access:
- Enable **Anthropic Claude 3 Sonnet**
- Enable **Amazon Titan Embeddings G1 - Text**

### 2. Build and Push Docker Image

```bash
cd app
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export AWS_REGION=us-east-1

# Create ECR repository
aws ecr create-repository --repository-name cookbook-chatbot --region $AWS_REGION

# Login to ECR
aws ecr get-login-password --region $AWS_REGION | \
  docker login --username AWS --password-stdin \
  ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com

# Build and push
docker build -t cookbook-chatbot:latest .
docker tag cookbook-chatbot:latest \
  ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/cookbook-chatbot:latest
docker push ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/cookbook-chatbot:latest
```

### 3. Configure Terraform

```bash
cd ../terraform
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars`:
```hcl
aws_region = "us-east-1"
container_image = "<AWS_ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/cookbook-chatbot:latest"
cognito_domain_prefix = "cookbook-chatbot-yourname-12345"  # Must be globally unique!
```

### 4. Deploy Infrastructure

```bash
terraform init
terraform validate
terraform apply
# Type 'yes' when prompted (takes ~10-15 minutes)
```

### 5. Upload Recipes and Test

```bash
# Get outputs
BUCKET_NAME=$(terraform output -raw s3_bucket_name)
KB_ID=$(terraform output -raw knowledge_base_id)
ALB_DNS=$(terraform output -raw alb_dns_name)

# Upload sample recipes
aws s3 cp /path/to/recipes/ s3://${BUCKET_NAME}/ --recursive

# Start Knowledge Base ingestion
DATA_SOURCE_ID=$(aws bedrock-agent list-data-sources \
  --knowledge-base-id ${KB_ID} \
  --query 'dataSourceSummaries[0].dataSourceId' --output text)
aws bedrock-agent start-ingestion-job \
  --knowledge-base-id ${KB_ID} \
  --data-source-id ${DATA_SOURCE_ID}

# Wait 2-5 minutes for ingestion to complete

# Access application
echo "Application URL: http://${ALB_DNS}"
```

Open the URL, sign up with Cognito, and start chatting!

## What Gets Created

### AWS Resources (Approximate Costs)

| Resource | Purpose | Monthly Cost |
|----------|---------|--------------|
| ECS Fargate (2 tasks) | Run Chainlit app | $30-50 |
| Application Load Balancer | Traffic routing | $20-25 |
| NAT Gateway (2 AZs) | Internet for private subnets | $60-80 |
| OpenSearch Serverless | Vector storage | $50-100 |
| Cognito | Authentication | Free tier |
| S3 | Recipe storage | $1-5 |
| Bedrock | AI model usage | Pay per request |
| CloudWatch Logs | Application logs | $1-5 |
| **Total Base Cost** | | **~$160-265/month** |

### Network Architecture

- **VPC**: 10.0.0.0/16
- **Public Subnets**: 2 (for ALB)
- **Private Subnets**: 2 (for ECS tasks)
- **Availability Zones**: 2 (Multi-AZ)

### Security Features

- ✅ Cognito authentication required
- ✅ ECS tasks in private subnets
- ✅ Security groups with least privilege
- ✅ S3 bucket encryption enabled
- ✅ IAM roles with minimal permissions

## Testing the Chatbot

Try these sample queries after deployment:

1. "Show me a chocolate chip cookie recipe"
2. "How do I make pasta carbonara?"
3. "What ingredients do I need for baking bread?"
4. "Give me a quick dinner recipe"
5. "How do I substitute butter in baking?"

## Monitoring

### View Application Logs
```bash
aws logs tail /ecs/cookbook-chatbot --follow
```

### Check ECS Service Health
```bash
aws ecs describe-services \
  --cluster cookbook-chatbot-cluster \
  --services cookbook-chatbot-service \
  --query 'services[0].{Status:status,Running:runningCount,Desired:desiredCount}'
```

### Check ALB Health
Go to: AWS Console → EC2 → Load Balancers → Select ALB → Target Groups

## Common Issues

### ECS Tasks Not Starting
- Check CloudWatch logs: `aws logs tail /ecs/cookbook-chatbot --follow`
- Verify ECR image exists and is accessible
- Check task IAM role permissions

### Can't Access Application
- Verify ALB is in public subnets
- Check security group allows port 80
- Ensure ECS tasks are healthy

### Cognito Login Not Working
- Verify Cognito domain prefix is unique
- Check Cognito user pool is active
- Ensure callback URLs are correct

### Knowledge Base Returns No Results
- Verify ingestion job completed successfully
- Check S3 bucket has documents
- Ensure documents are in supported format (PDF, TXT, MD, etc.)

## Updating the Application

### Update Application Code
```bash
cd app
docker build -t cookbook-chatbot:latest .
docker tag cookbook-chatbot:latest ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/cookbook-chatbot:latest
docker push ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/cookbook-chatbot:latest

aws ecs update-service \
  --cluster cookbook-chatbot-cluster \
  --service cookbook-chatbot-service \
  --force-new-deployment
```

### Update Infrastructure
```bash
cd terraform
# Make changes to .tf files
terraform plan
terraform apply
```

### Add More Recipes
```bash
aws s3 cp new-recipe.pdf s3://${BUCKET_NAME}/
aws bedrock-agent start-ingestion-job \
  --knowledge-base-id ${KB_ID} \
  --data-source-id ${DATA_SOURCE_ID}
```

## Cleanup

To destroy all resources and stop incurring costs:

```bash
cd terraform
terraform destroy
# Type 'yes' when prompted

# Optional: Delete ECR repository
aws ecr delete-repository --repository-name cookbook-chatbot --force
```

⚠️ **Warning**: This permanently deletes all data including recipes!

## Next Steps

- [ ] Add custom domain with Route 53
- [ ] Enable HTTPS with ACM certificate
- [ ] Set up CloudWatch alarms for monitoring
- [ ] Configure auto-scaling for ECS tasks
- [ ] Implement CI/CD pipeline
- [ ] Add more recipe documents
- [ ] Customize Chainlit UI theme

## Documentation

- **Full Details**: See [README.md](../README.md)
- **Architecture**: See [docs/ARCHITECTURE.md](ARCHITECTURE.md)
- **Deployment Guide**: See [docs/DEPLOYMENT.md](DEPLOYMENT.md)
- **Build Guide**: See [docs/BUILD.md](BUILD.md)

## Support

For issues:
1. Check CloudWatch logs
2. Review documentation
3. Verify AWS resource status
4. Check Terraform state

## Security Notes

⚠️ **Important**:
- Never commit `terraform.tfvars` (contains secrets)
- Never commit AWS credentials
- Regularly review IAM permissions
- Enable MFA for AWS console access
- Monitor AWS billing for unexpected costs

## Cost Optimization Tips

For dev/test environments:
- Reduce ECS task count to 1
- Use single NAT Gateway (less redundancy)
- Delete resources when not in use
- Set up AWS Budgets alerts

## License

See [LICENSE](../LICENSE) file for details.
