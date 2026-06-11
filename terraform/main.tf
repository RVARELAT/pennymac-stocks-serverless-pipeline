terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

resource "aws_dynamodb_table" "stock_movers" {
  name         = var.dynamodb_table_name
  billing_mode = "PAY_PER_REQUEST"

  hash_key = "date"

  attribute {
    name = "date"
    type = "S"
  }

  tags = {
    Project     = "pennymac-stocks-serverless-pipeline"
    Environment = "dev"
    ManagedBy   = "terraform"
  }
}