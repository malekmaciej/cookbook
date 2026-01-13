# Build and Deployment Notes

## Docker Build

The Docker image for the Chainlit application can be built and pushed to AWS ECR.

### Prerequisites

1. AWS CLI configured with credentials
2. Docker installed and running
3. ECR repository created

### Build Steps

```bash
# Navigate to app directory
cd app

# Get AWS account ID
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export AWS_REGION=us-east-1

# Create ECR repository (one-time)
aws ecr create-repository \
  --repository-name cookbook-chatbot \
  --region ${AWS_REGION} \
  --image-scanning-configuration scanOnPush=true

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

### SSL Certificate Issues in Build Environment

If you encounter SSL certificate errors during Docker build (like in some CI/CD environments), you can:

1. **Option 1**: Build in a different environment (local machine, EC2, CodeBuild)
2. **Option 2**: Temporarily disable SSL verification (not recommended for production):
   ```dockerfile
   RUN pip install --no-cache-dir --trusted-host pypi.org --trusted-host files.pythonhosted.org -r requirements.txt
   ```

Note: This is a build-time issue only and won't affect the running container.

## Terraform Deployment

### Prerequisites

1. Terraform >= 1.5 installed
2. AWS CLI configured
3. Docker image pushed to ECR
4. Bedrock model access enabled

### Deployment Steps

```bash
cd terraform

# Copy and edit variables
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your values

# Initialize Terraform
terraform init

# Validate configuration
terraform validate

# Preview changes
terraform plan

# Apply configuration
terraform apply
```

### Important Configuration

Before running `terraform apply`, ensure:

1. **Cognito Domain Prefix**: Must be globally unique
   ```hcl
   cognito_domain_prefix = "cookbook-chatbot-yourname-12345"
   ```

2. **Container Image**: Update with your ECR URI
   ```hcl
   container_image = "<AWS_ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/cookbook-chatbot:latest"
   ```

3. **Bedrock Access**: Enable model access in AWS Console
   - Go to Bedrock → Model access
   - Enable: Anthropic Claude 3 Sonnet
   - Enable: Titan Embeddings G1 - Text

## Post-Deployment Steps

### 1. Upload Recipe Documents

```bash
# Get bucket name
BUCKET_NAME=$(terraform output -raw s3_bucket_name)

# Upload recipes
aws s3 cp /path/to/recipes/ s3://${BUCKET_NAME}/ --recursive
```

### 2. Sync Knowledge Base

```bash
# Get IDs
KB_ID=$(terraform output -raw knowledge_base_id)
DATA_SOURCE_ID=$(aws bedrock-agent list-data-sources \
  --knowledge-base-id ${KB_ID} \
  --query 'dataSourceSummaries[0].dataSourceId' \
  --output text)

# Start ingestion
aws bedrock-agent start-ingestion-job \
  --knowledge-base-id ${KB_ID} \
  --data-source-id ${DATA_SOURCE_ID}

# Check status
aws bedrock-agent list-ingestion-jobs \
  --knowledge-base-id ${KB_ID} \
  --data-source-id ${DATA_SOURCE_ID}
```

### 3. Access Application

```bash
# Get ALB URL
ALB_DNS=$(terraform output -raw alb_dns_name)
echo "Application URL: http://${ALB_DNS}"
```

## Updating the Application

### Update Code Only

```bash
cd app

# Build and push new image
docker build -t cookbook-chatbot:latest .
docker tag cookbook-chatbot:latest \
  ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/cookbook-chatbot:latest
docker push ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/cookbook-chatbot:latest

# Force ECS to redeploy
aws ecs update-service \
  --cluster cookbook-chatbot-cluster \
  --service cookbook-chatbot-service \
  --force-new-deployment \
  --region ${AWS_REGION}
```

### Update Infrastructure

```bash
cd terraform

# Make changes to .tf files
# Then apply
terraform plan
terraform apply
```

## Troubleshooting

### Docker Build Fails

- Check Python version compatibility (requires 3.11+)
- Verify requirements.txt syntax
- Check network connectivity

### Terraform Apply Fails

- Verify AWS credentials
- Check IAM permissions
- Ensure Cognito domain is unique
- Verify Bedrock model access is enabled

### ECS Tasks Not Starting

```bash
# Check task logs
aws logs tail /ecs/cookbook-chatbot --follow

# Check service events
aws ecs describe-services \
  --cluster cookbook-chatbot-cluster \
  --services cookbook-chatbot-service \
  --query 'services[0].events[:5]'
```

### Application Not Accessible

- Verify ECS tasks are healthy
- Check ALB target group health
- Verify security group rules
- Check NAT Gateway configuration

## Monitoring

### View Application Logs

```bash
aws logs tail /ecs/cookbook-chatbot --follow
```

### Check ECS Service Status

```bash
aws ecs describe-services \
  --cluster cookbook-chatbot-cluster \
  --services cookbook-chatbot-service
```

### Check ALB Target Health

```bash
aws elbv2 describe-target-health \
  --target-group-arn $(terraform output -raw target_group_arn)
```

## Cleanup

### Destroy All Resources

```bash
cd terraform
terraform destroy

# Delete ECR repository
aws ecr delete-repository \
  --repository-name cookbook-chatbot \
  --force \
  --region ${AWS_REGION}
```

**Warning**: This will delete all resources including:
- S3 bucket with recipes and vectors (if not protected)
- CloudWatch logs
- All networking resources

Make sure to backup any important data before destroying!

## CI/CD Integration

### GitHub Actions Example

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy CookBook Chatbot

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1
      
      - name: Login to Amazon ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v1
      
      - name: Build and push Docker image
        env:
          ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
          ECR_REPOSITORY: cookbook-chatbot
          IMAGE_TAG: ${{ github.sha }}
        run: |
          cd app
          docker build -t $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG .
          docker push $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG
      
      - name: Setup Terraform
        uses: hashicorp/setup-terraform@v2
        with:
          terraform_version: 1.7.0
      
      - name: Terraform Init
        run: |
          cd terraform
          terraform init
      
      - name: Terraform Apply
        run: |
          cd terraform
          terraform apply -auto-approve
```

## Security Best Practices

1. **Secrets Management**: Never commit secrets to git
   - Use AWS Secrets Manager or Parameter Store
   - Use environment variables for sensitive data

2. **Network Security**: 
   - Keep ECS tasks in private subnets
   - Use security groups to restrict access
   - Enable VPC Flow Logs for audit

3. **IAM**: 
   - Use least privilege principles
   - Regularly review IAM policies
   - Enable MFA for console access

4. **Monitoring**:
   - Enable CloudWatch alarms
   - Monitor Bedrock API usage
   - Track costs with AWS Budgets

5. **Backups**:
   - Enable S3 versioning for recipes
   - Regular Terraform state backups
   - Document recovery procedures
