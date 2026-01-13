# Migration Guide: OpenSearch Serverless to S3 Vectors

This guide helps you migrate from the old architecture (using OpenSearch Serverless) to the new architecture (using AWS S3 Vectors for vector storage).

## What Changed

### Infrastructure Changes
- **Vector Storage**: Migrated from OpenSearch Serverless to AWS S3 Vectors (dedicated vector bucket and index)
- **Embedding Model**: Upgraded from Titan Embeddings v1 to v2
- **Cost Savings**: Approximately $50-100/month by removing OpenSearch Serverless

### Benefits
- ✅ **Lower costs** - No OpenSearch Serverless charges (~90% reduction vs traditional vector DBs)
- ✅ **Better Polish language support** - Titan v2 has improved multilingual capabilities
- ✅ **Simpler architecture** - Purpose-built S3 Vectors service
- ✅ **Same functionality** - Transparent to the application

## Migration Steps

### ⚠️ Important Notes Before Starting

1. **Backup your data**: The S3 bucket with recipes will remain unchanged, but document your current setup
2. **Downtime**: There will be brief downtime during the migration
3. **Re-ingestion required**: After migration, you'll need to re-ingest your recipe documents
4. **Testing recommended**: Test in a dev environment first if possible

### Step 1: Backup Current State

```bash
# Navigate to terraform directory
cd terraform

# Export current outputs
terraform output > ../pre-migration-outputs.txt

# Note your Knowledge Base ID and Data Source ID
KB_ID=$(terraform output -raw knowledge_base_id)
echo "Current KB ID: ${KB_ID}" >> ../pre-migration-outputs.txt

# List data sources
aws bedrock-agent list-data-sources \
  --knowledge-base-id ${KB_ID} >> ../pre-migration-outputs.txt
```

### Step 2: Pull Latest Code

```bash
# Pull the latest changes
git pull origin main

# Review changes
git log --oneline -5
```

### Step 3: Update Terraform

```bash
cd terraform

# Initialize (in case new providers are needed)
terraform init -upgrade

# Review the planned changes
terraform plan
```

**Expected changes:**
- OpenSearch Serverless resources will be **destroyed**
- Knowledge Base will be **updated in place** (storage type change)
- No changes to S3 bucket, ECS, ALB, or other resources

### Step 4: Apply Changes

```bash
# Apply the changes
terraform apply

# Type 'yes' when prompted
```

**Duration**: Approximately 5-10 minutes
- OpenSearch Serverless collection deletion: ~2-3 minutes
- Knowledge Base update: ~1-2 minutes

### Step 5: Re-ingest Documents

After the migration, the Knowledge Base needs to re-ingest documents with the new embedding model:

```bash
# Get the new Knowledge Base ID (should be the same)
KB_ID=$(terraform output -raw knowledge_base_id)

# Get Data Source ID
DATA_SOURCE_ID=$(aws bedrock-agent list-data-sources \
  --knowledge-base-id ${KB_ID} \
  --query 'dataSourceSummaries[0].dataSourceId' \
  --output text)

# Start ingestion job
aws bedrock-agent start-ingestion-job \
  --knowledge-base-id ${KB_ID} \
  --data-source-id ${DATA_SOURCE_ID}

# Monitor ingestion status
aws bedrock-agent list-ingestion-jobs \
  --knowledge-base-id ${KB_ID} \
  --data-source-id ${DATA_SOURCE_ID}
```

Wait for the ingestion job to complete (status: `COMPLETE`). This typically takes 2-5 minutes depending on the number of documents.

### Step 6: Test the Application

```bash
# Get ALB DNS
ALB_DNS=$(terraform output -raw alb_dns_name)

echo "Access your application at: http://${ALB_DNS}"
```

Test queries:
1. Open the application URL
2. Login with your Cognito credentials
3. Try sample queries about your recipes
4. Verify that responses include proper citations

### Step 7: Verify Cost Savings

After 24-48 hours, check AWS Cost Explorer to verify the cost reduction:

1. Go to AWS Console → Cost Explorer
2. Look at daily costs
3. You should see a reduction of approximately $50-100/month from removing OpenSearch Serverless

## Rollback Procedure

If you need to rollback to the old architecture:

```bash
# Checkout the previous version
git checkout <previous-commit-hash>

# Apply the old configuration
cd terraform
terraform apply
```

**Note**: You'll need to re-ingest documents again after rollback.

## Troubleshooting

### Issue: Terraform fails to destroy OpenSearch resources

**Solution**: Sometimes OpenSearch resources have dependencies. Try these steps in order:

1. First, try refreshing the state:
```bash
terraform refresh
terraform plan
```

2. If that doesn't work, try destroying with a target:
```bash
terraform destroy -target=aws_opensearchserverless_access_policy.main
terraform destroy -target=aws_opensearchserverless_collection.main
terraform destroy -target=aws_opensearchserverless_security_policy.network
terraform destroy -target=aws_opensearchserverless_security_policy.encryption
```

3. **Last resort only**: Remove from state if resources are already deleted manually:
```bash
# ⚠️ CRITICAL WARNING: Only use this if ALL of the following are true:
#    1. Resources are confirmed deleted in AWS Console
#    2. Resources cannot be imported back into Terraform
#    3. Normal Terraform operations have failed
#
# This can lead to orphaned resources if not used carefully!

# First, try to import the resources if they still exist:
# terraform import aws_opensearchserverless_collection.main <collection-id>

# Only if import fails because resources are truly deleted:
terraform state rm aws_opensearchserverless_collection.main
terraform state rm aws_opensearchserverless_access_policy.main
terraform state rm aws_opensearchserverless_security_policy.encryption
terraform state rm aws_opensearchserverless_security_policy.network

# Then apply
terraform apply
```

**Important**: Manually removing resources from state should only be done as a last resort when:
- Resources are confirmed to be already deleted in the AWS Console
- You cannot import them back with `terraform import`
- Normal Terraform operations have failed
This can lead to orphaned resources and state inconsistencies if misused.

### Issue: Knowledge Base ingestion fails

**Solution**: Check IAM permissions and S3 bucket access:

```bash
# Get project name from Terraform
PROJECT_NAME=$(terraform output -raw project_name 2>/dev/null || echo "cookbook-chatbot")

# Verify KB role has S3 permissions
aws iam get-role-policy \
  --role-name ${PROJECT_NAME}-bedrock-kb-role \
  --policy-name ${PROJECT_NAME}-bedrock-kb-s3-policy

# Verify S3 bucket exists and has content
BUCKET_NAME=$(terraform output -raw s3_bucket_name)
aws s3 ls s3://${BUCKET_NAME}/
```

### Issue: Application returns errors

**Solution**: Check ECS logs:

```bash
# View recent logs
aws logs tail /ecs/cookbook-chatbot --follow

# Check Knowledge Base ID is set correctly
aws ecs describe-tasks \
  --cluster cookbook-chatbot-cluster \
  --tasks $(aws ecs list-tasks \
    --cluster cookbook-chatbot-cluster \
    --query 'taskArns[0]' --output text) \
  --query 'tasks[0].overrides.containerOverrides[0].environment'
```

## Post-Migration Checklist

- [ ] Old OpenSearch Serverless resources deleted
- [ ] Knowledge Base successfully updated to S3 storage
- [ ] Document ingestion completed successfully
- [ ] Application accessible via ALB
- [ ] Test queries return correct results with citations
- [ ] Cost Explorer shows reduced costs
- [ ] Documentation updated (if you have custom docs)

## Need Help?

If you encounter issues during migration:

1. Check CloudWatch Logs: `/ecs/cookbook-chatbot`
2. Review Terraform state: `terraform show`
3. Check AWS Console for resource status
4. Refer to [DEPLOYMENT.md](DEPLOYMENT.md) for detailed deployment steps

## Summary

This migration simplifies your infrastructure and reduces costs while maintaining the same functionality. The main changes are transparent to end users, who will continue to interact with the chatbot in the same way.

**Key Benefits:**
- 💰 ~$50-100/month cost savings
- 🌍 Better Polish language support with Titan v2
- 🎯 Simpler architecture with fewer managed resources
- ⚡ Same performance and functionality
