output "alb_dns_name" {
  description = "DNS name of the Application Load Balancer"
  value       = aws_lb.main.dns_name
}

output "project_name" {
  description = "Project name used for resource naming"
  value       = var.project_name
}

output "knowledge_base_id" {
  description = "ID of the Bedrock Knowledge Base"
  value       = aws_bedrockagent_knowledge_base.main.id
}

output "s3_bucket_name" {
  description = "Name of the S3 bucket for recipe storage"
  value       = aws_s3_bucket.recipes.id
}

output "s3_vectors_bucket_name" {
  description = "Name of the S3 Vectors bucket for embedding storage"
  value       = aws_s3vectors_vector_bucket.vectors.vector_bucket_name
}

output "s3_vectors_index_arn" {
  description = "ARN of the S3 Vectors index"
  value       = aws_s3vectors_index.main.arn
}

output "cognito_user_pool_id" {
  description = "ID of the Cognito User Pool"
  value       = aws_cognito_user_pool.main.id
}

output "cognito_user_pool_client_id" {
  description = "ID of the Cognito User Pool Client"
  value       = aws_cognito_user_pool_client.main.id
}

output "cognito_domain" {
  description = "Cognito domain for authentication"
  value       = aws_cognito_user_pool_domain.main.domain
}

output "ecs_cluster_name" {
  description = "Name of the ECS cluster"
  value       = aws_ecs_cluster.main.name
}

output "ecs_service_name" {
  description = "Name of the ECS service"
  value       = aws_ecs_service.main.name
}

output "mcp_server_service_name" {
  description = "Name of the MCP server ECS service"
  value       = var.github_token != "" ? aws_ecs_service.mcp_server[0].name : null
}

output "mcp_server_task_name" {
  description = "Task family name for the MCP server"
  value       = var.github_token != "" ? aws_ecs_task_definition.mcp_server[0].family : null
}

output "service_discovery_namespace" {
  description = "AWS Cloud Map namespace for service discovery"
  value       = var.github_token != "" ? aws_service_discovery_private_dns_namespace.main[0].name : null
}

output "mcp_server_dns" {
  description = "DNS name for the MCP server via service discovery"
  value       = var.github_token != "" && length(aws_service_discovery_private_dns_namespace.main) > 0 ? "mcp-server.${aws_service_discovery_private_dns_namespace.main[0].name}" : null
}
