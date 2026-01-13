# Deployment Guide

This guide provides step-by-step instructions for deploying the CookBook Chatbot infrastructure.

## Prerequisites Check

Before starting, ensure you have:

- [ ] AWS Account with admin or sufficient IAM permissions
- [ ] AWS CLI installed and configured (`aws configure`)
- [ ] Terraform >= 1.5 installed
- [ ] Docker installed and running
- [ ] Git installed
- [ ] Python 3.11+ installed

## Step-by-Step Deployment

### Step 1: Verify AWS Access

```bash
# Test AWS credentials
aws sts get-caller-identity

# Expected output should show your AWS account ID
```

### Step 2: Enable Bedrock Model Access

Before deploying, you need to enable model access in AWS Bedrock:

1. Go to AWS Console → Bedrock → Model access
2. Click "Enable specific models"
3. Enable the following models:
   - **Anthropic Claude 3 Sonnet** (for chat)
   - **Titan Embeddings v2** (for Knowledge Base)
4. Wait for access to be granted (usually instant)

### Step 3: Create ECR Repository

```bash
# Set your AWS region
export AWS_REGION=us-east-1

# Create ECR repository
aws ecr create-repository \
  --repository-name cookbook-chatbot \
  --region ${AWS_REGION} \
  --image-scanning-configuration scanOnPush=true

# Note the repositoryUri from the output
# 068167017169.dkr.ecr.us-east-1.amazonaws.com/cookbook-chatbot
```

### Step 4: Build and Push Docker Image

```bash
# Navigate to app directory
cd app

# Get AWS account ID
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Login to ECR
aws ecr get-login-password --region ${AWS_REGION} | \
  docker login --username AWS --password-stdin \
  ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com

# Build Docker image
docker build -t cookbook-chatbot:latest .

# Tag image for ECR
docker tag cookbook-chatbot:latest \
  ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/cookbook-chatbot:latest

# Push to ECR
docker push ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/cookbook-chatbot:latest
```

### Step 5: Configure Terraform Variables

```bash
cd ../terraform

# Copy example variables file
cp terraform.tfvars.example terraform.tfvars

# Edit terraform.tfvars
nano terraform.tfvars
```

Update the following required variables:

```hcl
# AWS Configuration
aws_region = "us-east-1"
environment = "dev"
project_name = "cookbook-chatbot"

# Container image - use your ECR URI from Step 3
container_image = "<AWS_ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/cookbook-chatbot:latest"

# Cognito domain must be globally unique
# Add a random suffix or your name
cognito_domain_prefix = "cookbook-chatbot-yourname-12345"

# Optional: Adjust resources
desired_count = 2  # Number of ECS tasks
container_cpu = 1024  # 1 vCPU
container_memory = 2048  # 2 GB
```

### Step 6: Initialize and Deploy Terraform

```bash
# Initialize Terraform
terraform init

# Validate configuration
terraform validate

# Preview changes
terraform plan

# Apply configuration (takes ~10-15 minutes)
terraform apply

# Type 'yes' when prompted
```

**What's being created:**
- VPC with public/private subnets
- NAT Gateways and Internet Gateway
- Security Groups
- ECS Cluster and Service (Fargate)
- Application Load Balancer
- Cognito User Pool
- S3 Bucket for recipes and vector storage
- Bedrock Knowledge Base (with S3 vector store)
- IAM Roles and Policies
- CloudWatch Log Groups

### Step 7: Save Terraform Outputs

```bash
# Save important outputs
terraform output > ../deployment-info.txt

# Display key outputs
terraform output alb_dns_name
terraform output cognito_user_pool_id
terraform output knowledge_base_id
terraform output s3_bucket_name
```

### Step 8: Prepare Sample Recipes (Optional)

Create some sample recipe files:

```bash
mkdir -p ../sample-recipes

# Create a sample recipe
cat > ../sample-recipes/chocolate-chip-cookies.txt << 'EOF'
Chocolate Chip Cookies

Ingredients:
- 2 1/4 cups all-purpose flour
- 1 tsp baking soda
- 1 tsp salt
- 1 cup (2 sticks) butter, softened
- 3/4 cup granulated sugar
- 3/4 cup packed brown sugar
- 2 large eggs
- 2 tsp vanilla extract
- 2 cups chocolate chips

Instructions:
1. Preheat oven to 375°F (190°C)
2. Combine flour, baking soda, and salt in a bowl
3. Beat butter and sugars until creamy
4. Add eggs and vanilla, beat well
5. Gradually stir in flour mixture
6. Fold in chocolate chips
7. Drop rounded tablespoons onto ungreased baking sheets
8. Bake 9-11 minutes until golden brown
9. Cool on baking sheet for 2 minutes
10. Transfer to wire rack to cool completely

Yield: About 60 cookies
Prep time: 15 minutes
Cook time: 10 minutes
EOF
```

### Step 9: Upload Recipes to S3

```bash
# Get bucket name from Terraform output
export AWS_DEFAULT_REGION=us-east-1
export AWS_DEFAULT_PROFILE=bedrock
BUCKET_NAME=$(terraform output -raw s3_bucket_name)
BUCKET_NAME=cookbook-recipes-068167017169

# Upload sample recipes
cd ~/GitRepos/przepisy
for file in $(ls *.md)   
do
aws --profile bedrock s3 cp ${file} s3://${BUCKET_NAME}/${file}
done

# Verify upload
aws --profile bedrock s3 ls s3://${BUCKET_NAME}/
```

### Step 10: Sync Knowledge Base

```bash
# Get Knowledge Base ID
KB_ID=$(terraform output -raw knowledge_base_id)
KB_ID=XK7TH8KBIF

# List data sources
DATA_SOURCE_ID=$(aws --profile bedrock bedrock-agent list-data-sources \
  --knowledge-base-id ${KB_ID} \
  --query 'dataSourceSummaries[0].dataSourceId' \
  --output text)

# Start ingestion job
aws --profile bedrock bedrock-agent start-ingestion-job --knowledge-base-id XK7TH8KBIF --data-source-id 6L0ICMK6TX

# Check ingestion status (wait until COMPLETE)
aws --profile bedrock bedrock-agent list-ingestion-jobs --knowledge-base-id XK7TH8KBIF --data-source-id 6L0ICMK6TX
```

The ingestion usually takes 2-5 minutes depending on the amount of data.

### Step 11: Create First Cognito User

```bash
# Get User Pool ID
USER_POOL_ID=$(terraform output -raw cognito_user_pool_id)

# Get Cognito domain
COGNITO_DOMAIN=$(terraform output -raw cognito_domain)

# Get ALB DNS
ALB_DNS=$(terraform output -raw alb_dns_name)

echo "Access your application at: http://${ALB_DNS}"
echo "You'll need to create a Cognito user account on first visit"
```

### Step 12: Access the Application

1. Open your browser and navigate to: `http://<ALB_DNS_NAME>`
2. You'll be redirected to Cognito login page
3. Click "Sign up" to create a new account
4. Enter your email and password
5. Check your email for verification code
6. Enter the verification code
7. Login with your credentials
8. You'll be redirected to the CookBook Chatbot!

### Step 13: Test the Chatbot

Try these queries:
- "Show me the chocolate chip cookie recipe"
- "How do I make cookies?"
- "What ingredients do I need for baking?"

## Post-Deployment Configuration

### Add More Users

Option 1: Self-service signup (enabled by default)
- Users can sign up at the login page

Option 2: Admin creates users
```bash
aws cognito-idp admin-create-user \
  --user-pool-id ${USER_POOL_ID} \
  --username user@example.com \
  --user-attributes Name=email,Value=user@example.com Name=email_verified,Value=true \
  --temporary-password TempPassword123!
```

### Enable HTTPS (Recommended for Production)

1. Request an ACM certificate:
```bash
aws acm request-certificate \
  --domain-name yourdomain.com \
  --validation-method DNS
```

2. Complete DNS validation in Route 53 or your DNS provider

3. Update `terraform.tfvars`:
```hcl
certificate_arn = "arn:aws:acm:us-east-1:123456789012:certificate/xxx"
```

4. Modify `terraform/main.tf` to add HTTPS listener (port 443)

5. Apply changes:
```bash
terraform apply
```

### Configure Custom Domain

1. Create Route 53 hosted zone for your domain
2. Create an A record pointing to ALB
3. Update Cognito callback URLs with custom domain

### Set Up Monitoring

1. Create CloudWatch Dashboard for monitoring key metrics

2. Set up alarms for:
   - ECS task health
   - ALB target health
   - Bedrock API errors
   - High costs

## Validation Checklist

- [ ] Terraform apply completed successfully
- [ ] Docker image pushed to ECR
- [ ] ECS tasks are running (check ECS console)
- [ ] ALB target group shows healthy targets
- [ ] Knowledge Base ingestion job completed
- [ ] Can access application via ALB URL
- [ ] Cognito authentication works
- [ ] Chatbot responds to queries
- [ ] Recipe information is retrieved correctly

## Troubleshooting

### ECS Tasks Not Starting

```bash
# Check ECS service events
aws ecs describe-services \
  --cluster cookbook-chatbot-cluster \
  --services cookbook-chatbot-service

# Check task logs
aws logs tail /ecs/cookbook-chatbot --follow
```

### ALB Health Checks Failing

```bash
# Check target group health
aws elbv2 describe-target-health \
  --target-group-arn <target-group-arn>
```

### Knowledge Base Ingestion Failed

```bash
# Check ingestion job details
aws bedrock-agent list-ingestion-jobs \
  --knowledge-base-id ${KB_ID} \
  --data-source-id ${DATA_SOURCE_ID}
```

### Can't Access Application

1. Check security groups
2. Verify ALB is in public subnets
3. Check route tables have IGW route
4. Verify ECS tasks are healthy

## Next Steps

- Add more recipe documents
- Customize Chainlit UI (app/.chainlit/config.toml)
- Set up CloudWatch alarms
- Configure backup policies
- Implement CI/CD pipeline
- Add custom domain with HTTPS

## Rollback

If something goes wrong:

```bash
# Destroy all resources
terraform destroy

# Clean up ECR repository
aws ecr delete-repository \
  --repository-name cookbook-chatbot \
  --force
```
