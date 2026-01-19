# MCP Server Integration Summary

## What Was Added

This update adds the MCP (Model Context Protocol) server as an optional additional service to the Terraform ECS infrastructure. The MCP server provides programmatic access to recipes stored in a GitHub repository.

## Key Features

### 1. **Optional Deployment**
- The MCP server is deployed only when `github_token` variable is set
- If `github_token` is empty, only the Chainlit app is deployed (backward compatible)
- No changes required for existing deployments that don't need the MCP server

### 2. **AWS Cloud Map Service Discovery**
- MCP server is registered with AWS Cloud Map for internal service discovery
- DNS name: `mcp-server.cookbook-chatbot.local:8000/mcp`
- Enables easy communication between ECS services without hardcoded IPs

### 3. **Secure Configuration**
- GitHub token stored securely in AWS Secrets Manager
- ECS task execution role granted minimal permissions to read the secret
- Token never exposed in logs or task definitions

### 4. **Separate ECS Service**
- Runs in the same ECS cluster as the Chainlit app
- Independent scaling and updates
- Deployed to private subnets with no direct internet access
- Uses ARM64 architecture for cost efficiency

### 5. **CloudWatch Logging**
- Dedicated log group: `/ecs/cookbook-chatbot-mcp-server`
- 7-day log retention
- Easy troubleshooting and monitoring

## Architecture Changes

```
Before:
ECS Cluster
  └── Chainlit Service (2 tasks)

After:
ECS Cluster
  ├── Chainlit Service (2 tasks)
  └── MCP Server Service (1 task) [Optional]
      └── Registered with Cloud Map for service discovery
```

## Files Modified

1. **terraform/variables.tf**
   - Added MCP server configuration variables
   - Added GitHub token (sensitive) variable
   - Added resource sizing variables (CPU, memory, desired count)

2. **terraform/main.tf**
   - Added AWS Secrets Manager resources for GitHub token
   - Added CloudWatch log group for MCP server
   - Added AWS Cloud Map namespace and service for service discovery
   - Added security group rule for inter-task communication
   - Added ECS task definition for MCP server
   - Added ECS service for MCP server with service discovery registration

3. **terraform/outputs.tf**
   - Added outputs for MCP server service name
   - Added output for MCP server task name
   - Added output for service discovery namespace
   - Added output for MCP server DNS name

## New Files Created

1. **terraform/MCP_SERVER_DEPLOYMENT.md**
   - Complete deployment guide for the MCP server
   - Configuration instructions
   - Troubleshooting tips
   - Cost breakdown

2. **terraform/terraform.tfvars.example**
   - Example configuration file with all variables
   - Includes MCP server configuration options
   - Helpful comments and defaults

## Infrastructure Resources Added (when MCP server is enabled)

- 1 AWS Secrets Manager Secret (GitHub token)
- 1 AWS Secrets Manager Secret Version
- 1 IAM Role Policy (Secrets access)
- 1 CloudWatch Log Group
- 1 AWS Cloud Map Namespace
- 1 AWS Cloud Map Service
- 1 Security Group Rule
- 1 ECS Task Definition
- 1 ECS Service

## Configuration Options

### Required (to enable MCP server):
```hcl
github_token = "ghp_xxxxxxxxxxxx"
mcp_container_image = "<account>.dkr.ecr.us-east-1.amazonaws.com/recipe-mcp-server:latest"
```

### Optional (with defaults):
```hcl
github_repo = "malekmaciej/przepisy"
recipes_path = ""
mcp_container_cpu = 512
mcp_container_memory = 1024
mcp_desired_count = 1
```

## Cost Impact

Additional monthly costs (when MCP server is deployed):
- ECS Fargate: ~$10-15 (1 task, 0.5 vCPU, 1GB RAM)
- Secrets Manager: ~$0.40
- Cloud Map: ~$1
- CloudWatch Logs: ~$0.50-1

**Total Additional Cost**: ~$12-18/month

## Backward Compatibility

✅ **Fully backward compatible!**

- Existing deployments without `github_token` will continue to work unchanged
- No breaking changes to existing resources
- MCP server resources are only created when explicitly enabled

## How to Use

### For New Deployments:
1. Follow the normal deployment process
2. Optionally add `github_token` and `mcp_container_image` to `terraform.tfvars`
3. Run `terraform apply`

### For Existing Deployments:
1. Update your Terraform files (git pull)
2. Optionally add MCP server configuration to `terraform.tfvars`
3. Run `terraform plan` to review changes
4. Run `terraform apply`

### To Disable MCP Server Later:
1. Remove or empty the `github_token` variable
2. Run `terraform apply`
3. MCP server resources will be destroyed, Chainlit app remains intact

## Service Discovery Usage

From within the VPC (e.g., from the Chainlit app):

```python
# Access MCP server via service discovery
import httpx

mcp_url = "http://mcp-server.cookbook-chatbot.local:8000/mcp"
response = httpx.get(mcp_url)
```

## Security Considerations

1. **Secrets Management**: GitHub token is stored in AWS Secrets Manager, not in code
2. **Network Isolation**: MCP server runs in private subnets
3. **Least Privilege**: IAM roles have minimal required permissions
4. **Logging**: All activity is logged to CloudWatch
5. **Service Discovery**: Internal DNS only, not accessible from internet

## Monitoring

### CloudWatch Logs
```bash
aws logs tail /ecs/cookbook-chatbot-mcp-server --follow
```

### Service Status
```bash
aws ecs describe-services \
  --cluster cookbook-chatbot-cluster \
  --services cookbook-chatbot-mcp-server-service
```

### Service Discovery
```bash
terraform output mcp_server_dns
```

## Documentation

- **Main README**: Updated with MCP server deployment steps
- **Deployment Guide**: [terraform/MCP_SERVER_DEPLOYMENT.md](terraform/MCP_SERVER_DEPLOYMENT.md)
- **Example Config**: [terraform/terraform.tfvars.example](terraform/terraform.tfvars.example)

## Next Steps

1. Review the [MCP Server Deployment Guide](terraform/MCP_SERVER_DEPLOYMENT.md)
2. Build and push the MCP server Docker image to ECR
3. Configure `terraform.tfvars` with your settings
4. Deploy with `terraform apply`
5. Access the MCP server via service discovery from within your VPC

## Questions?

- Check the deployment guide for detailed instructions
- Review the troubleshooting section for common issues
- See the example tfvars file for configuration options
