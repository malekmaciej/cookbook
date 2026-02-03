output "website_url" {
  description = "URL of the static website via CloudFront"
  value       = "https://${aws_cloudfront_distribution.website.domain_name}"
}

output "cloudfront_distribution_id" {
  description = "ID of the CloudFront distribution"
  value       = aws_cloudfront_distribution.website.id
}

output "website_s3_bucket" {
  description = "Name of the S3 bucket hosting the website"
  value       = aws_s3_bucket.website.id
}

output "recipes_s3_bucket" {
  description = "Name of the S3 bucket for recipe storage"
  value       = aws_s3_bucket.recipes.id
}

output "knowledge_base_id" {
  description = "ID of the Bedrock Knowledge Base"
  value       = aws_bedrock_knowledge_base.main.id
}

output "data_source_id" {
  description = "ID of the Bedrock Data Source"
  value       = aws_bedrock_data_source.main.data_source_id
}

output "cognito_user_pool_id" {
  description = "ID of the Cognito User Pool"
  value       = aws_cognito_user_pool.main.id
}

output "cognito_client_id" {
  description = "ID of the Cognito User Pool Client"
  value       = aws_cognito_user_pool_client.main.id
}

output "cognito_identity_pool_id" {
  description = "ID of the Cognito Identity Pool"
  value       = aws_cognito_identity_pool.main.id
}

output "cognito_domain" {
  description = "Cognito domain for authentication"
  value       = "${var.cognito_domain_prefix}.auth.${var.aws_region}.amazoncognito.com"
}

output "opensearch_collection_endpoint" {
  description = "Endpoint of the OpenSearch Serverless collection"
  value       = aws_opensearchserverless_collection.main.collection_endpoint
}
