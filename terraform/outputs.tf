output "dynamodb_table_name" {
  description = "Name of the DynamoDB table"
  value       = aws_dynamodb_table.stock_movers.name
}

output "dynamodb_table_arn" {
  description = "ARN of the DynamoDB table"
  value       = aws_dynamodb_table.stock_movers.arn
}

output "ingest_lambda_name" {
  description = "Name of the ingestion Lambda function"
  value       = aws_lambda_function.ingest_lambda.function_name
}

