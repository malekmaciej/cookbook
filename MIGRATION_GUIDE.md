# Migration Guide: ECS/ALB to Static Website

This guide helps you migrate from the expensive ECS + ALB architecture to the cost-optimized S3 + CloudFront static website.

## Why Migrate?

**Cost Savings**: Reduce infrastructure costs by 90%+
- From: ~$80-120/month
- To: ~$1.50-7/month
- **Savings**: ~$75-115/month

**Benefits**:
- ✅ Same chatbot functionality
- ✅ Simpler architecture (no VPC, ECS, ALB, NAT Gateway)
- ✅ Faster deployment and updates
- ✅ Better global performance with CloudFront CDN
- ✅ No Docker/containers to manage
- ✅ Auto-scaling built into S3/CloudFront

## Migration Strategy

We recommend a **parallel deployment** approach:
1. Deploy the new static website alongside existing ECS infrastructure
2. Test the static website thoroughly
3. Update bookmarks and links to use the new URL
4. Destroy the old ECS infrastructure

## Step-by-Step Migration

### Step 1: Backup Current Configuration

Before starting, document your current setup:

```bash
# Save current Terraform outputs
cd terraform
terraform output > ../backup-outputs.txt

# Save your current terraform.tfvars
cp terraform.tfvars ../backup-terraform.tfvars
```

### Step 2: Prepare for Static Site Deployment

The static website uses a different Terraform configuration. You have two options:

#### Option A: Separate Terraform State (Recommended for Testing)

Keep both infrastructures separate during testing:

```bash
# Create a new directory for static site
mkdir -p terraform-static
cd terraform-static

# Copy the static terraform files
cp ../terraform/main-static.tf main.tf
cp ../terraform/variables.tf .
cp ../terraform/variables-static.tf .
cp ../terraform/outputs-static.tf outputs.tf
cp ../terraform/versions.tf .

# Create new terraform.tfvars
cp ../terraform/terraform.tfvars.example-static terraform.tfvars
```

Edit `terraform.tfvars`:
- Use the **same** `cognito_domain_prefix` if you want to reuse users
- Or use a **different** prefix to keep auth completely separate
- Set other variables as needed

```bash
# Initialize Terraform in new directory
terraform init
```

#### Option B: Replace Existing Infrastructure (After Testing)

After testing the static site, you can replace the old infrastructure:

```bash
cd terraform

# Backup old main.tf
mv main.tf main-ecs-backup.tf

# Use static configuration
mv main-static.tf main.tf
mv outputs.tf outputs-ecs-backup.tf
mv outputs-static.tf outputs.tf

# Update terraform.tfvars with static site settings
```

### Step 3: Deploy Static Website

```bash
# If using Option A (separate directory)
cd terraform-static

# If using Option B (replaced files)
cd terraform

# Review the plan
terraform plan

# Deploy
terraform apply
```

This will create:
- S3 bucket for static website
- CloudFront distribution
- Cognito resources (new or reused)
- OpenSearch Serverless collection for vectors
- Bedrock Knowledge Base
- S3 bucket for recipes

**Note**: Deployment takes ~15-20 minutes due to OpenSearch Serverless.

### Step 4: Get the New Website URL

```bash
terraform output website_url
```

This will give you a CloudFront URL like: `https://d1234567890abc.cloudfront.net`

### Step 5: Migrate Recipe Data

If you deployed with Option A (separate state), you need to copy recipes:

```bash
# Get old and new bucket names
OLD_BUCKET=$(cd ../terraform && terraform output -raw s3_bucket_name)
NEW_BUCKET=$(terraform output -raw recipes_s3_bucket)

# Copy recipes from old to new bucket
aws s3 sync s3://${OLD_BUCKET}/ s3://${NEW_BUCKET}/
```

If using Option B (replaced infrastructure), Terraform should preserve the existing S3 bucket.

### Step 6: Sync Knowledge Base

Trigger ingestion in the new Knowledge Base:

```bash
KB_ID=$(terraform output -raw knowledge_base_id)
DATA_SOURCE_ID=$(terraform output -raw data_source_id)

aws bedrock-agent start-ingestion-job \
  --knowledge-base-id ${KB_ID} \
  --data-source-id ${DATA_SOURCE_ID}

# Check status
aws bedrock-agent list-ingestion-jobs \
  --knowledge-base-id ${KB_ID} \
  --data-source-id ${DATA_SOURCE_ID}
```

Wait for ingestion to complete (status: COMPLETE).

### Step 7: Test the New Website

Open the CloudFront URL in your browser:

1. **Test Authentication**:
   - Sign in with existing Cognito user (if reusing domain)
   - Or create a new user account
   - Verify email confirmation works

2. **Test Chatbot Functionality**:
   - Ask about recipes
   - Verify Knowledge Base returns results
   - Test various cooking questions

3. **Test Recipe Quality**:
   - Compare answers with old ECS chatbot
   - Verify formatting is correct
   - Check that all features work

4. **Test MCP Integration** (if applicable):
   - If you have MCP server, test recipe creation
   - Verify tool use functionality

### Step 8: Migrate Users (if needed)

If you used a different Cognito domain for the static site:

#### Option 1: Keep Both Active
- Users can use either the old or new URL
- Both share Bedrock resources
- Gradually transition users to new URL

#### Option 2: Migrate Users
Unfortunately, AWS Cognito doesn't support user migration between pools. You'll need to:
- Ask users to create new accounts on the new site
- Or use the same `cognito_domain_prefix` to reuse the user pool

### Step 9: Update Bookmarks and Links

Update any:
- Browser bookmarks
- Documentation links
- Shared URLs
- Email signatures
- README files

From: Old ALB URL
To: New CloudFront URL

### Step 10: Monitor Both Systems

For 1-2 weeks, monitor both deployments:

```bash
# Check CloudWatch metrics
- CloudFront requests and errors
- Cognito sign-ins
- Bedrock API calls
- S3 storage and requests

# Compare costs
- Check AWS Cost Explorer
- Compare week-over-week costs
- Verify savings are realized
```

### Step 11: Destroy Old Infrastructure

After confirming the static website works correctly and users have migrated:

```bash
# If using Option A (separate states)
cd terraform  # The old ECS directory
terraform destroy

# If using Option B (replaced config)
# The old infrastructure was already destroyed when you ran terraform apply
```

**Important**: Before destroying, verify:
- ✅ Static website is working correctly
- ✅ All users have access to new site
- ✅ Knowledge Base has all recipes
- ✅ No critical data is lost
- ✅ MCP server is deployed elsewhere if needed

**Cleanup**:
```bash
# Delete old ECR repositories
aws ecr delete-repository --repository-name cookbook-chatbot --force
aws ecr delete-repository --repository-name recipe-mcp-server --force  # if used

# Verify all old resources are deleted
# Check AWS Console for any remaining resources
```

## Handling MCP Server

The MCP server requires a running service (can't be static). You have options:

### Option 1: Don't Use MCP Server
If you don't need recipe creation via chatbot, simply don't deploy it.

### Option 2: Deploy MCP Server Separately
Deploy MCP server on a small EC2 instance or ECS (single task):
- Cost: ~$5-15/month (t3.micro or small ECS task)
- Update `mcp_server_url` in terraform.tfvars to point to it
- Configure CORS to allow CloudFront domain

### Option 3: Serverless MCP with Lambda
Convert MCP server to AWS Lambda + API Gateway:
- Cost: ~$0-2/month (within free tier for light usage)
- Requires code modification
- More complex deployment

## Rollback Plan

If you need to rollback to the ECS infrastructure:

### If Using Option A (Separate State)
Simply switch back to using the old ALB URL. Both systems are still running.

### If Using Option B (Replaced Infrastructure)
1. Restore the old terraform files:
```bash
cd terraform
mv main.tf main-static-backup.tf
mv main-ecs-backup.tf main.tf
mv outputs.tf outputs-static-backup.tf
mv outputs-ecs-backup.tf outputs.tf
```

2. Restore your old terraform.tfvars:
```bash
cp ../backup-terraform.tfvars terraform.tfvars
```

3. Re-deploy:
```bash
terraform init
terraform apply
```

## Troubleshooting

### Issue: CloudFront returns 403 errors
- Check S3 bucket policy allows CloudFront OAI
- Verify files are uploaded to S3
- Check CloudFront distribution is deployed

### Issue: Cognito login fails
- Verify callback URLs include CloudFront domain
- Check Cognito user pool client settings
- Ensure Identity Pool is configured correctly

### Issue: Bedrock returns permission errors
- Check IAM role for authenticated users
- Verify Bedrock permissions in policy
- Ensure Cognito Identity Pool role attachment

### Issue: Knowledge Base returns no results
- Verify ingestion job completed
- Check recipes are in S3 bucket
- Ensure OpenSearch collection is active

### Issue: Can't access old ECS chatbot
- If you used Option B, the old infrastructure is destroyed
- Rollback using steps above
- Or redeploy from backup config

## Cost Verification

After migration, verify cost savings:

### Week 1
```bash
# Check AWS Cost Explorer
# Look for:
# - Reduced ECS costs
# - Reduced ALB costs  
# - Reduced NAT Gateway costs
# - New CloudFront costs (minimal)
# - New S3 costs (minimal)
```

### Week 4
Compare full month costs:
- Expected savings: ~$75-115/month
- Actual savings: (check Cost Explorer)

## Post-Migration Checklist

- [ ] Static website is accessible via CloudFront URL
- [ ] Cognito authentication works
- [ ] Chatbot returns correct answers
- [ ] Knowledge Base has all recipes
- [ ] Users can sign in and use the chatbot
- [ ] Costs have decreased significantly
- [ ] All bookmarks/links updated
- [ ] Old ECS infrastructure destroyed (after verification)
- [ ] ECR repositories cleaned up
- [ ] Documentation updated
- [ ] Team notified of new URL

## Getting Help

If you encounter issues during migration:

1. Check the [Static Website Deployment Guide](STATIC_DEPLOYMENT.md)
2. Review Terraform logs: `terraform apply -debug`
3. Check AWS CloudWatch logs
4. Open an issue in the GitHub repository
5. Check AWS Bedrock documentation

## Next Steps

After successful migration:

1. **Monitor Performance**: Use CloudWatch to track performance
2. **Optimize Costs**: Review AWS Cost Explorer monthly
3. **Add Custom Domain**: Consider using Route53 + ACM for custom domain
4. **Enable Logging**: Set up CloudFront access logs if needed
5. **Backup Configuration**: Keep Terraform state backed up
6. **Document Changes**: Update internal documentation

Congratulations on completing the migration and achieving 90%+ cost savings! 🎉
