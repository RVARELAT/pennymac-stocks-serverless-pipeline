variable "aws_region" {
  description = "AWS region where resources will be created"
  type        = string
  default     = "us-west-2"
}

variable "dynamodb_table_name" {
  description = "Name of the DynamoDB table for storing daily stock movers"
  type        = string
  default     = "pennymac-stock-movers"
}

variable "massive_api_key" {
  description = "API key for Massive stock data API"
  type        = string
  sensitive   = true
}