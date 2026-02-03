# Static Website Deployment Guide

This guide explains how to deploy the CookBook Chatbot as a static website on S3 with CloudFront, replacing the expensive ECS + ALB infrastructure.

## Cost Savings

**Old Architecture**: ~$80-120/month + Bedrock usage
**New Architecture**: ~$1.50-7/month + Bedrock usage
**Savings**: ~$75-115/month (90%+ reduction)

## Prerequisites

- AWS Account with appropriate permissions
- AWS CLI configured with credentials
- Terraform >= 1.5

## Deployment Steps

### 1. Configure Terraform Variables

```bash
cd terraform
cp terraform.tfvars.example-static terraform.tfvars
```

Edit `terraform.tfvars` and update:
- `cognito_domain_prefix`: Must be globally unique (e.g., `cookbook-chatbot-yourname-12345`)
- `mcp_server_url`: Leave empty unless you have an MCP server deployed elsewhere
- Other variables as needed for your environment

### 2. Initialize Terraform

```bash
terraform init
```

### 3. Review the Deployment Plan

```bash
terraform plan
```

### 4. Deploy Infrastructure

```bash
terraform apply
```

The deployment takes approximately 15-20 minutes (longer than ECS because OpenSearch Serverless takes time to provision).

### 5. Get the Website URL

After deployment completes:

```bash
terraform output website_url
```

This will give you a CloudFront URL like: `https://d1234567890abc.cloudfront.net`

### 6. Upload Recipe Documents

Upload your recipe documents to the S3 bucket:

```bash
# Get the bucket name from Terraform output
BUCKET_NAME=$(terraform output -raw recipes_s3_bucket)

# Upload recipes
aws s3 cp /path/to/your/recipes/ s3://${BUCKET_NAME}/ --recursive
```

### 7. Sync Knowledge Base

After uploading documents, trigger a sync of the Knowledge Base:

```bash
# Get the Knowledge Base ID and Data Source ID
KB_ID=$(terraform output -raw knowledge_base_id)
DATA_SOURCE_ID=$(terraform output -raw data_source_id)

# Start ingestion job
aws bedrock-agent start-ingestion-job \
  --knowledge-base-id ${KB_ID} \
  --data-source-id ${DATA_SOURCE_ID}
```

Wait for the ingestion job to complete. You can check status with:

```bash
aws bedrock-agent list-ingestion-jobs \
  --knowledge-base-id ${KB_ID} \
  --data-source-id ${DATA_SOURCE_ID}
```

### 8. Create a Cognito User

Open the website URL in your browser. You'll see a login page. Click "Sign In with AWS Cognito" to be redirected to the Cognito Hosted UI.

Click "Sign up" and create a new account with:
- Email address
- Password (must meet requirements: 8+ chars, uppercase, lowercase, number, symbol)

You'll receive a verification email. Click the link to verify your account.

### 9. Access the Chatbot

After verification, sign in with your email and password. You should now see the chatbot interface!

## Updating the Website

If you make changes to the static website files (HTML, CSS, JavaScript):

```bash
# Re-apply Terraform to upload new files
cd terraform
terraform apply

# Invalidate CloudFront cache to see changes immediately
DISTRIBUTION_ID=$(terraform output -raw cloudfront_distribution_id)
aws cloudfront create-invalidation \
  --distribution-id ${DISTRIBUTION_ID} \
  --paths "/*"
```

## Adding More Recipes

Simply upload new documents to S3 and trigger a Knowledge Base sync:

```bash
# Upload new recipe
aws s3 cp new-recipe.pdf s3://${BUCKET_NAME}/

# Trigger sync
aws bedrock-agent start-ingestion-job \
  --knowledge-base-id ${KB_ID} \
  --data-source-id ${DATA_SOURCE_ID}
```

## Monitoring

- **CloudFront Logs**: Enable in CloudFront settings if needed
- **Bedrock Usage**: Check AWS Cost Explorer
- **S3 Costs**: Monitor in AWS Cost Explorer
- **Cognito Users**: View in AWS Cognito console

## Troubleshooting

### Issue: Can't access the website

- Check CloudFront distribution is deployed (status: Deployed)
- Verify the URL is using HTTPS
- Check browser console for errors

### Issue: Login doesn't work

- Verify Cognito user is confirmed (check email for verification link)
- Check that callback URLs in Cognito include your CloudFront URL
- Clear browser cache and cookies

### Issue: Chatbot returns errors

- Check browser console for detailed error messages
- Verify Knowledge Base has completed ingestion
- Ensure Cognito Identity Pool has proper IAM permissions for Bedrock
- Check that you're using a Bedrock-supported region

### Issue: Knowledge Base returns no results

- Verify documents are uploaded to S3
- Check ingestion job completed successfully
- Ensure documents are in supported format (PDF, TXT, MD, etc.)
- Try re-syncing the Knowledge Base

## Cleanup

To destroy all resources:

```bash
cd terraform
terraform destroy
```

**Note**: This will delete all resources including the S3 buckets and their contents.

## Migration from ECS/ALB

If you're migrating from the old ECS/ALB infrastructure:

1. **Keep both environments running** during migration to test
2. **Export Cognito users** if you want to preserve them (see AWS Cognito docs)
3. **Test thoroughly** before destroying old infrastructure
4. **Update any bookmarks** or links to use the new CloudFront URL
5. **Destroy old infrastructure** to stop costs:

```bash
# If using the old main.tf, rename it first
mv terraform/main.tf terraform/main-ecs.tf.backup
mv terraform/main-static.tf terraform/main.tf

# Apply to create new infrastructure
terraform apply

# After testing, destroy old ECS resources manually if needed
```

## Architecture

The new static website architecture:

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│   Internet  │────▶│  CloudFront  │────▶│   S3 Bucket     │
│   Users     │     │   (HTTPS)    │     │  (Static Site)  │
└─────────────┘     └──────────────┘     └─────────────────┘
                            │
                            ▼
                    ┌──────────────┐
                    │   Cognito    │
                    │   (Auth)     │
                    └──────┬───────┘
                           │
        ┌──────────────────┼─────────────────┐
        │                  │                 │
        ▼                  ▼                 ▼
┌─────────────┐    ┌──────────────┐  ┌─────────────┐
│  Bedrock    │    │      S3      │  │ OpenSearch  │
│  Runtime    │    │  (Recipes)   │  │ Serverless  │
│  (Browser)  │    └──────────────┘  │  (Vectors)  │
└─────────────┘                      └─────────────┘
```

Key differences from ECS/ALB architecture:
- ❌ No VPC, NAT Gateway, or private subnets
- ❌ No ECS cluster or Fargate tasks
- ❌ No Application Load Balancer
- ✅ Static files on S3
- ✅ CloudFront for HTTPS and CDN
- ✅ Bedrock calls from browser (client-side)
- ✅ Cognito for authentication
- ✅ Same Knowledge Base functionality

## Security Considerations

- All traffic over HTTPS via CloudFront
- Cognito authentication required for access
- AWS credentials obtained via Cognito Identity Pool
- IAM policies restrict Bedrock access to authenticated users only
- S3 bucket not publicly accessible (CloudFront OAI only)
- No secrets or credentials in client-side code

## Optional: Custom Domain

To use a custom domain (e.g., cookbook.yourdomain.com):

1. Create an ACM certificate in `us-east-1` for your domain
2. Update `terraform/main-static.tf` CloudFront resource to use custom domain
3. Add Route53 alias record pointing to CloudFront distribution
4. Update Cognito callback URLs to include custom domain

See [AWS CloudFront Custom Domain Documentation](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/CNAMEs.html) for details.
