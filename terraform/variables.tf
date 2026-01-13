variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name (e.g., dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
  default     = "cookbook-chatbot"
}

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "List of availability zones"
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b"]
}

variable "container_image" {
  description = "Docker image for the Chainlit application"
  type        = string
  default     = "cookbook-chatbot:latest"
}

variable "container_cpu" {
  description = "CPU units for the container (1024 = 1 vCPU)"
  type        = number
  default     = 1024
}

variable "container_memory" {
  description = "Memory for the container in MB"
  type        = number
  default     = 2048
}

variable "desired_count" {
  description = "Desired number of ECS tasks"
  type        = number
  default     = 2
}

variable "bedrock_model_id" {
  description = "Bedrock model ID to use"
  type        = string
  default     = "anthropic.claude-3-sonnet-20240229-v1:0"
}

variable "knowledge_base_name" {
  description = "Name for the Bedrock Knowledge Base"
  type        = string
  default     = "cooking-recipes-kb"
}

variable "cognito_domain_prefix" {
  description = "Prefix for Cognito domain"
  type        = string
}

variable "domain_name" {
  description = "Domain name for the application (e.g., cookbook.maciejmalek.com)"
  type        = string
  default     = ""
}

variable "route53_zone_id" {
  description = "Route53 hosted zone ID for the domain"
  type        = string
  default     = ""
}

variable "allowed_email_domains" {
  description = "List of allowed email domains for Cognito signup"
  type        = list(string)
  default     = []
}
