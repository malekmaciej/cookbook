# Terraform configuration for S3 + CloudFront static website deployment
# This replaces the expensive ECS + ALB infrastructure

terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# Data sources
data "aws_caller_identity" "current" {}
data "aws_partition" "current" {}

# S3 Bucket for static website hosting
resource "aws_s3_bucket" "website" {
  bucket = "${var.project_name}-website-${data.aws_caller_identity.current.account_id}"

  tags = {
    Name        = "${var.project_name}-website"
    Environment = var.environment
    Purpose     = "Static website hosting"
  }
}

# S3 bucket website configuration
resource "aws_s3_bucket_website_configuration" "website" {
  bucket = aws_s3_bucket.website.id

  index_document {
    suffix = "index.html"
  }

  error_document {
    key = "index.html"
  }
}

# S3 bucket public access block (will allow CloudFront to access)
resource "aws_s3_bucket_public_access_block" "website" {
  bucket = aws_s3_bucket.website.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# S3 bucket versioning
resource "aws_s3_bucket_versioning" "website" {
  bucket = aws_s3_bucket.website.id

  versioning_configuration {
    status = "Enabled"
  }
}

# S3 bucket encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "website" {
  bucket = aws_s3_bucket.website.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# CloudFront Origin Access Identity
resource "aws_cloudfront_origin_access_identity" "website" {
  comment = "OAI for ${var.project_name} website"
}

# S3 bucket policy to allow CloudFront access
resource "aws_s3_bucket_policy" "website" {
  bucket = aws_s3_bucket.website.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowCloudFrontOAI"
        Effect = "Allow"
        Principal = {
          AWS = aws_cloudfront_origin_access_identity.website.iam_arn
        }
        Action   = "s3:GetObject"
        Resource = "${aws_s3_bucket.website.arn}/*"
      }
    ]
  })
}

# CloudFront distribution
resource "aws_cloudfront_distribution" "website" {
  enabled             = true
  is_ipv6_enabled     = true
  default_root_object = "index.html"
  price_class         = "PriceClass_100" # Use only North America and Europe edge locations
  comment             = "${var.project_name} static website"

  origin {
    domain_name = aws_s3_bucket.website.bucket_regional_domain_name
    origin_id   = "S3-${aws_s3_bucket.website.id}"

    s3_origin_config {
      origin_access_identity = aws_cloudfront_origin_access_identity.website.cloudfront_access_identity_path
    }
  }

  default_cache_behavior {
    allowed_methods  = ["GET", "HEAD", "OPTIONS"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "S3-${aws_s3_bucket.website.id}"

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }

    viewer_protocol_policy = "redirect-to-https"
    min_ttl                = 0
    default_ttl            = 3600
    max_ttl                = 86400
    compress               = true
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
  }

  tags = {
    Name        = "${var.project_name}-distribution"
    Environment = var.environment
  }
}

# Cognito User Pool
resource "aws_cognito_user_pool" "main" {
  name = "${var.project_name}-user-pool"

  auto_verified_attributes = ["email"]

  password_policy {
    minimum_length                   = 8
    require_lowercase                = true
    require_numbers                  = true
    require_symbols                  = true
    require_uppercase                = true
    temporary_password_validity_days = 7
  }

  schema {
    name                = "email"
    attribute_data_type = "String"
    mutable             = false
    required            = true

    string_attribute_constraints {
      min_length = 1
      max_length = 256
    }
  }

  tags = {
    Name        = "${var.project_name}-user-pool"
    Environment = var.environment
  }
}

# Cognito User Pool Domain
resource "aws_cognito_user_pool_domain" "main" {
  domain       = var.cognito_domain_prefix
  user_pool_id = aws_cognito_user_pool.main.id
}

# Cognito User Pool Client
resource "aws_cognito_user_pool_client" "main" {
  name         = "${var.project_name}-client"
  user_pool_id = aws_cognito_user_pool.main.id

  generate_secret = false

  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_flows                  = ["code"]
  allowed_oauth_scopes                 = ["openid", "email", "profile"]
  
  callback_urls = [
    "https://${aws_cloudfront_distribution.website.domain_name}/",
    "https://${aws_cloudfront_distribution.website.domain_name}/index.html"
  ]
  
  logout_urls = [
    "https://${aws_cloudfront_distribution.website.domain_name}/",
    "https://${aws_cloudfront_distribution.website.domain_name}/index.html"
  ]

  supported_identity_providers = ["COGNITO"]

  refresh_token_validity = 30
  access_token_validity  = 60
  id_token_validity      = 60

  token_validity_units {
    refresh_token = "days"
    access_token  = "minutes"
    id_token      = "minutes"
  }
}

# Cognito Identity Pool
resource "aws_cognito_identity_pool" "main" {
  identity_pool_name               = "${var.project_name}-identity-pool"
  allow_unauthenticated_identities = false

  cognito_identity_providers {
    client_id               = aws_cognito_user_pool_client.main.id
    provider_name           = aws_cognito_user_pool.main.endpoint
    server_side_token_check = false
  }

  tags = {
    Name        = "${var.project_name}-identity-pool"
    Environment = var.environment
  }
}

# IAM role for authenticated users
resource "aws_iam_role" "cognito_authenticated" {
  name = "${var.project_name}-cognito-authenticated-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Federated = "cognito-identity.amazonaws.com"
        }
        Action = "sts:AssumeRoleWithWebIdentity"
        Condition = {
          StringEquals = {
            "cognito-identity.amazonaws.com:aud" = aws_cognito_identity_pool.main.id
          }
          "ForAnyValue:StringLike" = {
            "cognito-identity.amazonaws.com:amr" = "authenticated"
          }
        }
      }
    ]
  })

  tags = {
    Name        = "${var.project_name}-cognito-authenticated-role"
    Environment = var.environment
  }
}

# IAM policy for authenticated users to access Bedrock
resource "aws_iam_role_policy" "cognito_authenticated_bedrock" {
  name = "${var.project_name}-bedrock-access"
  role = aws_iam_role.cognito_authenticated.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream"
        ]
        Resource = [
          "arn:${data.aws_partition.current.partition}:bedrock:${var.aws_region}::foundation-model/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "bedrock:Retrieve",
          "bedrock:RetrieveAndGenerate"
        ]
        Resource = [
          aws_bedrock_knowledge_base.main.arn
        ]
      }
    ]
  })
}

# Attach the role to the identity pool
resource "aws_cognito_identity_pool_roles_attachment" "main" {
  identity_pool_id = aws_cognito_identity_pool.main.id

  roles = {
    authenticated = aws_iam_role.cognito_authenticated.arn
  }
}

# S3 bucket for recipe documents
resource "aws_s3_bucket" "recipes" {
  bucket = "${var.project_name}-recipes-${data.aws_caller_identity.current.account_id}"

  tags = {
    Name        = "${var.project_name}-recipes"
    Environment = var.environment
  }
}

# S3 bucket encryption for recipes
resource "aws_s3_bucket_server_side_encryption_configuration" "recipes" {
  bucket = aws_s3_bucket.recipes.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# S3 bucket versioning for recipes
resource "aws_s3_bucket_versioning" "recipes" {
  bucket = aws_s3_bucket.recipes.id

  versioning_configuration {
    status = "Enabled"
  }
}

# Bedrock Knowledge Base IAM role
resource "aws_iam_role" "bedrock_kb" {
  name = "${var.project_name}-bedrock-kb-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "bedrock.amazonaws.com"
        }
        Action = "sts:AssumeRole"
        Condition = {
          StringEquals = {
            "aws:SourceAccount" = data.aws_caller_identity.current.account_id
          }
          ArnLike = {
            "aws:SourceArn" = "arn:${data.aws_partition.current.partition}:bedrock:${var.aws_region}:${data.aws_caller_identity.current.account_id}:knowledge-base/*"
          }
        }
      }
    ]
  })

  tags = {
    Name        = "${var.project_name}-bedrock-kb-role"
    Environment = var.environment
  }
}

# IAM policy for Bedrock Knowledge Base to access S3
resource "aws_iam_role_policy" "bedrock_kb_s3" {
  name = "${var.project_name}-bedrock-kb-s3-policy"
  role = aws_iam_role.bedrock_kb.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.recipes.arn,
          "${aws_s3_bucket.recipes.arn}/*"
        ]
      }
    ]
  })
}

# IAM policy for Bedrock Knowledge Base to use models
resource "aws_iam_role_policy" "bedrock_kb_model" {
  name = "${var.project_name}-bedrock-kb-model-policy"
  role = aws_iam_role.bedrock_kb.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel"
        ]
        Resource = [
          "arn:${data.aws_partition.current.partition}:bedrock:${var.aws_region}::foundation-model/*"
        ]
      }
    ]
  })
}

# Bedrock Knowledge Base
resource "aws_bedrock_knowledge_base" "main" {
  name     = var.knowledge_base_name
  role_arn = aws_iam_role.bedrock_kb.arn

  knowledge_base_configuration {
    type = "VECTOR"
    vector_knowledge_base_configuration {
      embedding_model_arn = "arn:${data.aws_partition.current.partition}:bedrock:${var.aws_region}::foundation-model/amazon.titan-embed-text-v1"
    }
  }

  storage_configuration {
    type = "OPENSEARCH_SERVERLESS"
    opensearch_serverless_configuration {
      collection_arn    = aws_opensearchserverless_collection.main.arn
      vector_index_name = "bedrock-knowledge-base-index"
      field_mapping {
        vector_field   = "bedrock-knowledge-base-default-vector"
        text_field     = "AMAZON_BEDROCK_TEXT_CHUNK"
        metadata_field = "AMAZON_BEDROCK_METADATA"
      }
    }
  }

  tags = {
    Name        = var.knowledge_base_name
    Environment = var.environment
  }

  depends_on = [
    aws_opensearchserverless_collection.main,
    aws_iam_role_policy.bedrock_kb_s3,
    aws_iam_role_policy.bedrock_kb_model
  ]
}

# OpenSearch Serverless encryption policy
resource "aws_opensearchserverless_security_policy" "encryption" {
  name = "${var.project_name}-encryption-policy"
  type = "encryption"

  policy = jsonencode({
    Rules = [
      {
        ResourceType = "collection"
        Resource = [
          "collection/${var.project_name}-vectors"
        ]
      }
    ]
    AWSOwnedKey = true
  })
}

# OpenSearch Serverless network policy
resource "aws_opensearchserverless_security_policy" "network" {
  name = "${var.project_name}-network-policy"
  type = "network"

  policy = jsonencode([
    {
      Rules = [
        {
          ResourceType = "collection"
          Resource = [
            "collection/${var.project_name}-vectors"
          ]
        }
      ]
      AllowFromPublic = true
    }
  ])
}

# OpenSearch Serverless data access policy
resource "aws_opensearchserverless_access_policy" "data" {
  name = "${var.project_name}-data-access-policy"
  type = "data"

  policy = jsonencode([
    {
      Rules = [
        {
          ResourceType = "collection"
          Resource = [
            "collection/${var.project_name}-vectors"
          ]
          Permission = [
            "aoss:CreateCollectionItems",
            "aoss:UpdateCollectionItems",
            "aoss:DescribeCollectionItems"
          ]
        },
        {
          ResourceType = "index"
          Resource = [
            "index/${var.project_name}-vectors/*"
          ]
          Permission = [
            "aoss:CreateIndex",
            "aoss:DescribeIndex",
            "aoss:ReadDocument",
            "aoss:WriteDocument",
            "aoss:UpdateIndex",
            "aoss:DeleteIndex"
          ]
        }
      ]
      Principal = [
        aws_iam_role.bedrock_kb.arn,
        data.aws_caller_identity.current.arn
      ]
    }
  ])
}

# OpenSearch Serverless collection
resource "aws_opensearchserverless_collection" "main" {
  name = "${var.project_name}-vectors"
  type = "VECTORSEARCH"

  tags = {
    Name        = "${var.project_name}-vectors"
    Environment = var.environment
  }

  depends_on = [
    aws_opensearchserverless_security_policy.encryption,
    aws_opensearchserverless_security_policy.network,
    aws_opensearchserverless_access_policy.data
  ]
}

# Bedrock Data Source
resource "aws_bedrock_data_source" "main" {
  knowledge_base_id = aws_bedrock_knowledge_base.main.id
  name              = "${var.project_name}-s3-data-source"

  data_source_configuration {
    type = "S3"
    s3_configuration {
      bucket_arn = aws_s3_bucket.recipes.arn
    }
  }

  vector_ingestion_configuration {
    chunking_configuration {
      chunking_strategy = "FIXED_SIZE"
      fixed_size_chunking_configuration {
        max_tokens         = 300
        overlap_percentage = 20
      }
    }
  }
}

# Generate config.js file for the static website
resource "local_file" "config_js" {
  filename = "${path.module}/../static-site/config.js"
  content  = <<-EOT
// Configuration file - Generated by Terraform
// DO NOT EDIT MANUALLY - This file is automatically generated
window.CONFIG = {
    // AWS Region
    region: '${var.aws_region}',
    
    // Cognito Configuration
    cognito: {
        userPoolId: '${aws_cognito_user_pool.main.id}',
        userPoolWebClientId: '${aws_cognito_user_pool_client.main.id}',
        identityPoolId: '${aws_cognito_identity_pool.main.id}',
        domain: '${var.cognito_domain_prefix}.auth.${var.aws_region}.amazoncognito.com'
    },
    
    // Bedrock Configuration
    bedrock: {
        knowledgeBaseId: '${aws_bedrock_knowledge_base.main.id}',
        modelId: 'us.anthropic.claude-sonnet-4-20250514-v1:0'
    },
    
    // MCP Server Configuration (optional)
    mcpServerUrl: '${var.mcp_server_url}'
};
EOT
}

# Upload static website files to S3
resource "aws_s3_object" "index_html" {
  bucket       = aws_s3_bucket.website.id
  key          = "index.html"
  source       = "${path.module}/../static-site/index.html"
  etag         = filemd5("${path.module}/../static-site/index.html")
  content_type = "text/html"
}

resource "aws_s3_object" "styles_css" {
  bucket       = aws_s3_bucket.website.id
  key          = "styles.css"
  source       = "${path.module}/../static-site/styles.css"
  etag         = filemd5("${path.module}/../static-site/styles.css")
  content_type = "text/css"
}

resource "aws_s3_object" "app_js" {
  bucket       = aws_s3_bucket.website.id
  key          = "app.js"
  source       = "${path.module}/../static-site/app.js"
  etag         = filemd5("${path.module}/../static-site/app.js")
  content_type = "application/javascript"
}

resource "aws_s3_object" "config_js" {
  bucket       = aws_s3_bucket.website.id
  key          = "config.js"
  content      = local_file.config_js.content
  etag         = md5(local_file.config_js.content)
  content_type = "application/javascript"
}
EOT
}
