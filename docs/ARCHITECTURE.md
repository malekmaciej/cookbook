# Architecture Documentation

## Overview

The CookBook Chatbot is a cloud-native, serverless application that provides an AI-powered conversational interface for cooking recipes. It leverages AWS managed services to provide a scalable, secure, and cost-effective solution.

## Architecture Diagram

```
                                    ┌─────────────────────────────────────┐
                                    │         AWS Cloud                   │
                                    │                                     │
┌──────────┐                       │  ┌────────────────────────────┐    │
│          │                       │  │    Application Load         │    │
│  Users   │──────HTTPS───────────▶│  │    Balancer (ALB)          │    │
│          │                       │  │  - Public Subnets          │    │
└──────────┘                       │  │  - Port 80/443             │    │
                                    │  └──────────┬─────────────────┘    │
                                    │             │                      │
                                    │             ▼                      │
                                    │  ┌────────────────────────────┐    │
                                    │  │   AWS Cognito User Pool    │    │
                                    │  │  - Authentication          │    │
                                    │  │  - AWS SSO Integration     │    │
                                    │  └──────────┬─────────────────┘    │
                                    │             │                      │
                                    │             ▼                      │
                                    │  ┌────────────────────────────┐    │
                                    │  │      ECS Fargate           │    │
                                    │  │  - Private Subnets         │    │
                                    │  │  - Chainlit App            │    │
                                    │  │  - Auto Scaling            │    │
                                    │  └──────────┬─────────────────┘    │
                                    │             │                      │
                                    │   ┌─────────┴──────────┐           │
                                    │   │                    │           │
                                    │   ▼                    ▼           │
                                    │  ┌──────────┐   ┌──────────────┐  │
                                    │  │   AWS    │   │   Bedrock    │  │
                                    │  │  Bedrock │   │   Knowledge  │  │
                                    │  │  Runtime │   │   Base       │  │
                                    │  │ (Claude) │   │   (RAG)      │  │
                                    │  └──────────┘   └──────┬───────┘  │
                                    │                        │          │
                                    │          ┌─────────────┴──────┐   │
                                    │          │                    │   │
                                    │          ▼                    ▼   │
                                    │  ┌────────────┐      ┌────────────┐
                                    │  │ Amazon S3  │      │ Amazon S3  │
                                    │  │  Bucket    │      │  Vectors   │
                                    │  │ (Recipes)  │      │ (Vectors)  │
                                    │  └────────────┘      └────────────┘
                                    │                                     │
                                    └─────────────────────────────────────┘
```

## Components

### 1. Network Layer

#### VPC (Virtual Private Cloud)
- **CIDR**: 10.0.0.0/16
- **Subnets**:
  - 2 Public subnets (for ALB)
  - 2 Private subnets (for ECS tasks)
- **Availability Zones**: Multi-AZ deployment for high availability

#### Internet Gateway
- Provides internet access to resources in public subnets
- Attached to VPC for outbound internet traffic

#### NAT Gateways
- One per availability zone
- Enables private subnet resources to access internet
- Deployed in public subnets

#### Route Tables
- Public route table: Routes 0.0.0.0/0 → Internet Gateway
- Private route tables: Routes 0.0.0.0/0 → NAT Gateway

#### Security Groups

**ALB Security Group:**
- Ingress: Port 80, 443 from 0.0.0.0/0
- Egress: All traffic

**ECS Tasks Security Group:**
- Ingress: Port 8000 from ALB security group
- Egress: All traffic

### 2. Application Load Balancer (ALB)

**Purpose**: 
- Entry point for all HTTP/HTTPS traffic
- SSL/TLS termination
- Health checking
- Integration with Cognito for authentication

**Configuration**:
- Type: Application Load Balancer
- Scheme: Internet-facing
- Subnets: Public subnets
- Listeners:
  - Port 80 (HTTP) - with Cognito authentication
  - Port 443 (HTTPS) - optional, with ACM certificate

**Target Group**:
- Target type: IP (for Fargate tasks)
- Port: 8000
- Protocol: HTTP
- Health check: GET / (every 30s)

### 3. AWS Cognito

**Purpose**: User authentication and authorization

**Components**:

**User Pool**:
- Email verification required
- Password policy enforced
- Schema: email (required, unique)

**User Pool Domain**:
- Hosted UI for login/signup
- Format: `<prefix>.auth.<region>.amazoncognito.com`

**User Pool Client**:
- OAuth 2.0 flows: Authorization code
- Scopes: openid, email, profile
- Callback URL: ALB endpoint

**Integration**:
- ALB listener rules use `authenticate-cognito` action
- Redirects unauthenticated users to Cognito
- Sets authentication cookies after successful login

### 4. Amazon ECS (Elastic Container Service)

**Purpose**: Container orchestration for Chainlit application

**ECS Cluster**:
- Launch type: Fargate (serverless)
- Container Insights enabled for monitoring

**Task Definition**:
- CPU: 1024 (1 vCPU)
- Memory: 2048 MB
- Network mode: awsvpc
- Container:
  - Name: chainlit-app
  - Port: 8000
  - Environment variables:
    - KNOWLEDGE_BASE_ID
    - AWS_REGION
    - BEDROCK_MODEL_ID

**ECS Service**:
- Desired count: 2 (for high availability)
- Deployment: Rolling update
- Network: Private subnets, no public IP
- Load balancer integration: ALB target group

**IAM Roles**:
- **Task Execution Role**: Pull images, write logs
- **Task Role**: Access Bedrock, S3, Knowledge Base

### 5. AWS Bedrock

**Purpose**: Large Language Model (LLM) inference

**Model**: Anthropic Claude 3 Sonnet
- Model ID: `anthropic.claude-3-sonnet-20240229-v1:0`
- Capabilities: Text generation, conversation, reasoning

**API Integration**:
- `bedrock-runtime:InvokeModel` - Direct model calls
- `bedrock-runtime:InvokeModelWithResponseStream` - Streaming responses

### 6. AWS Bedrock Knowledge Base

**Purpose**: Retrieval-Augmented Generation (RAG) for recipes

**Components**:

**Knowledge Base Resource**:
- Type: VECTOR
- Embedding model: Amazon Titan Embeddings v2
- Vector dimensions: 1024 (for v2 model)

**Data Source**:
- Type: S3
- Source: Recipe bucket
- Supported formats: PDF, TXT, MD, DOCX, HTML

**Vector Store**:
- Backend: Amazon S3
- Storage: Vectors stored in S3 managed by Bedrock
- Index: Managed automatically by Bedrock

**Ingestion Process**:
1. Documents uploaded to S3
2. Ingestion job triggered
3. Documents parsed and chunked
4. Chunks embedded using Titan v2
5. Vectors stored in S3 (managed by Bedrock)
6. Metadata indexed for retrieval

**Query Process**:
1. User query received
2. Query embedded using Titan v2
3. Semantic search in S3 vector store
4. Top-K documents retrieved
5. Retrieved context + query sent to Claude
6. Generated response with citations

### 7. Amazon S3

**Purpose**: Storage for recipe documents

**Bucket Configuration**:
- Versioning: Enabled
- Encryption: AES256
- Public access: Blocked
- Lifecycle: Optional (configure as needed)

**Supported Content**:
- Recipe documents (PDF, TXT, MD, DOCX)
- Vector embeddings (managed by Bedrock)
- Images (optional, for future use)
- Metadata files

### 9. CloudWatch

**Purpose**: Logging and monitoring

**Log Groups**:
- `/ecs/cookbook-chatbot`: Application logs
  - Retention: 7 days
  - Contains: Application output, errors, access logs

**Metrics** (automatic):
- ECS: CPU, Memory utilization
- ALB: Request count, latency, target health
- Bedrock: API calls, latency, errors

### 10. IAM (Identity and Access Management)

**Roles and Policies**:

**Bedrock Knowledge Base Role**:
- Trust: bedrock.amazonaws.com
- Permissions:
  - s3:GetObject, s3:ListBucket (recipe bucket)
  - bedrock:InvokeModel (for embeddings)

**ECS Task Execution Role**:
- Trust: ecs-tasks.amazonaws.com
- Permissions:
  - ecr:GetAuthorizationToken
  - ecr:BatchCheckLayerAvailability
  - ecr:GetDownloadUrlForLayer
  - ecr:BatchGetImage
  - logs:CreateLogStream, logs:PutLogEvents

**ECS Task Role**:
- Trust: ecs-tasks.amazonaws.com
- Permissions:
  - bedrock:InvokeModel (Claude)
  - bedrock:Retrieve, bedrock:RetrieveAndGenerate (KB)
  - s3:GetObject (recipe bucket)

## Data Flow

### User Authentication Flow

```
1. User → ALB (HTTP request)
2. ALB → Check authentication cookie
3. If not authenticated:
   - ALB → Redirect to Cognito Hosted UI
   - User → Enter credentials
   - Cognito → Verify credentials
   - Cognito → Redirect to ALB with auth code
   - ALB → Exchange code for tokens
   - ALB → Set authentication cookie
4. ALB → Forward request to ECS task
```

### Chat Message Flow

```
1. User → Chainlit UI: Send message
2. Chainlit → Bedrock Agent Runtime:
   - API: retrieve_and_generate
   - Parameters: user query, KB ID, model ARN
3. Bedrock → Knowledge Base: Retrieve relevant docs
4. Knowledge Base → S3: Vector search
5. S3 → Knowledge Base: Return top-K results
6. Knowledge Base → Bedrock: Return documents + metadata
7. Bedrock → Claude: Generate response with context
8. Claude → Bedrock: Generated response
9. Bedrock → Chainlit: Response + citations
10. Chainlit → User: Display message with sources
```

### Document Ingestion Flow

```
1. Admin → S3: Upload recipe document
2. Admin → Bedrock Agent: Start ingestion job
3. Bedrock Agent → S3: Fetch document
4. Bedrock Agent → Parse and chunk document
5. Bedrock Agent → Titan v2: Generate embeddings
6. Titan → Bedrock Agent: Return vectors
7. Bedrock Agent → S3: Store vectors + metadata
8. S3 → Bedrock Agent: Confirm storage
9. Bedrock Agent → Admin: Ingestion complete
```

## Scalability

### Horizontal Scaling
- **ECS**: Increase desired task count
- **ALB**: Automatically scales to handle traffic
- **S3**: Serverless, scales automatically
- **Bedrock**: Serverless, auto-scales

### Vertical Scaling
- **ECS**: Increase CPU/memory per task
- **RDS**: N/A (not used)

### Auto Scaling (Future Enhancement)
```hcl
resource "aws_appautoscaling_target" "ecs" {
  max_capacity       = 10
  min_capacity       = 2
  resource_id        = "service/${cluster}/${service}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

resource "aws_appautoscaling_policy" "ecs_cpu" {
  name               = "cpu-autoscaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.ecs.resource_id
  scalable_dimension = aws_appautoscaling_target.ecs.scalable_dimension
  service_namespace  = aws_appautoscaling_target.ecs.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    target_value = 70.0
  }
}
```

## High Availability

- **Multi-AZ**: All components deployed across 2 AZs
- **ECS**: Multiple tasks across AZs
- **ALB**: Cross-zone load balancing enabled
- **NAT Gateway**: One per AZ for redundancy
- **S3**: Automatic replication and durability (11 9's)

## Security

### Network Security
- Private subnets for compute resources
- Security groups with least privilege
- No public IPs on ECS tasks
- VPC Flow Logs (optional, can be enabled)

### Data Security
- S3 bucket encryption at rest
- HTTPS for data in transit
- Cognito for authentication
- IAM roles with least privilege
- No hardcoded credentials

### Access Control
- Cognito user pool for application access
- IAM roles for service-to-service auth
- S3 bucket policies
- Security groups

### Compliance
- VPC isolation
- Encryption at rest and in transit
- Audit logging via CloudTrail (not configured, but available)
- Password policies enforced

## Monitoring and Observability

### Metrics
- ECS: Task CPU/memory, running count
- ALB: Request rate, latency, 5xx errors
- Bedrock: API calls, throttling, latency
- S3: Request rate, storage metrics

### Logs
- Application logs: CloudWatch Logs
- ALB access logs: S3 (optional)
- VPC Flow Logs: CloudWatch or S3 (optional)

### Alarms (Recommended)
- ECS task count < desired
- ALB unhealthy target count > 0
- Bedrock throttling errors
- High ALB 5xx error rate

## Cost Optimization

### Current Configuration Costs
- ECS Fargate: ~$30-50/month (2 tasks)
- ALB: ~$20-25/month
- NAT Gateway: ~$60-80/month (2 AZs)
- Bedrock: Variable, pay per request
- S3: ~$1-5/month (storage and vector operations)

### Optimization Strategies
1. **Reduce NAT Gateways**: Use 1 NAT for dev environments
2. **Spot Instances**: Not available for Fargate
3. **Reserved Capacity**: Not applicable for serverless
4. **Right-size ECS tasks**: Monitor and adjust CPU/memory
5. **S3**: Use Intelligent-Tiering for old recipes
6. **Bedrock**: Monitor and optimize query patterns

## Disaster Recovery

### Backup Strategy
- **S3**: Versioning enabled for recipe documents and vectors
- **Terraform State**: Store in S3 with versioning

### Recovery Procedures
1. **Application Failure**: ECS auto-restarts tasks
2. **AZ Failure**: Traffic routed to healthy AZ
3. **Region Failure**: Deploy to new region using Terraform
4. **Data Loss**: Restore from S3 versions

### RTO/RPO
- RTO: ~30 minutes (redeploy with Terraform)
- RPO: Near-zero (S3 versioning, real-time replication)

## Future Enhancements

1. **Auto Scaling**: CPU/memory-based auto scaling for ECS
2. **HTTPS**: Add ACM certificate and HTTPS listener
3. **Custom Domain**: Route 53 with custom domain
4. **CDN**: CloudFront for static assets
5. **Multi-Region**: Active-passive DR configuration
6. **CI/CD**: GitHub Actions or CodePipeline
7. **Advanced Monitoring**: X-Ray tracing, custom dashboards
8. **Cost Alerts**: Budget alerts and anomaly detection
9. **Backup Automation**: Scheduled snapshots
10. **WAF**: Web Application Firewall for ALB
