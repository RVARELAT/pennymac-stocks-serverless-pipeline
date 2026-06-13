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

output "api_lambda_name" {
  description = "Name of the API Lambda function"
  value       = aws_lambda_function.api_lambda.function_name
}

output "api_gateway_url" {
  description = "Base URL for the API Gateway HTTP API"
  value       = aws_apigatewayv2_api.stocks_api.api_endpoint
}

output "eventbridge_rule_name" {
  description = "Name of the EventBridge rule that schedules daily ingestion"
  value       = aws_cloudwatch_event_rule.daily_stock_ingestion.name
}

output "frontend_bucket_name" {
  description = "Name of the S3 bucket hosting the frontend"
  value       = aws_s3_bucket.frontend_bucket.bucket
}

output "frontend_website_url" {
  description = "S3 static website URL for the frontend"
  value       = aws_s3_bucket_website_configuration.frontend_website.website_endpoint
}