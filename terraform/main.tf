terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }

    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.7"
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

data "archive_file" "ingest_lambda_zip" {
  type        = "zip"
  source_file = "${path.module}/../backend/ingest/handler.py"
  output_path = "${path.module}/ingest_lambda.zip"
}

resource "aws_iam_role" "ingest_lambda_role" {
  name = "pennymac-ingest-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Project     = "pennymac-stocks-serverless-pipeline"
    Environment = "dev"
    ManagedBy   = "terraform"
  }
}

resource "aws_iam_role_policy" "ingest_lambda_policy" {
  name = "pennymac-ingest-lambda-policy"
  role = aws_iam_role.ingest_lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:PutItem"
        ]
        Resource = aws_dynamodb_table.stock_movers.arn
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "*"
      }
    ]
  })
}

resource "aws_lambda_function" "ingest_lambda" {
  function_name = "pennymac-stock-mover-ingest"
  role          = aws_iam_role.ingest_lambda_role.arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.12"
  timeout       = 120

  filename         = data.archive_file.ingest_lambda_zip.output_path
  source_code_hash = data.archive_file.ingest_lambda_zip.output_base64sha256

  environment {
    variables = {
      MASSIVE_API_KEY     = var.massive_api_key
      DYNAMODB_TABLE_NAME = aws_dynamodb_table.stock_movers.name
    }
  }

  tags = {
    Project     = "pennymac-stocks-serverless-pipeline"
    Environment = "dev"
    ManagedBy   = "terraform"
  }
}


data "archive_file" "api_lambda_zip" {
  type        = "zip"
  source_file = "${path.module}/../backend/api/handler.py"
  output_path = "${path.module}/api_lambda.zip"
}

resource "aws_iam_role" "api_lambda_role" {
  name = "pennymac-api-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Project     = "pennymac-stocks-serverless-pipeline"
    Environment = "dev"
    ManagedBy   = "terraform"
  }
}

resource "aws_iam_role_policy" "api_lambda_policy" {
  name = "pennymac-api-lambda-policy"
  role = aws_iam_role.api_lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:Scan"
        ]
        Resource = aws_dynamodb_table.stock_movers.arn
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "*"
      }
    ]
  })
}

resource "aws_lambda_function" "api_lambda" {
  function_name = "pennymac-stock-mover-api"
  role          = aws_iam_role.api_lambda_role.arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.12"
  timeout       = 30

  filename         = data.archive_file.api_lambda_zip.output_path
  source_code_hash = data.archive_file.api_lambda_zip.output_base64sha256

  environment {
    variables = {
      DYNAMODB_TABLE_NAME = aws_dynamodb_table.stock_movers.name
    }
  }

  tags = {
    Project     = "pennymac-stocks-serverless-pipeline"
    Environment = "dev"
    ManagedBy   = "terraform"
  }
}

resource "aws_apigatewayv2_api" "stocks_api" {
  name          = "pennymac-stock-movers-api"
  protocol_type = "HTTP"

  cors_configuration {
    allow_origins = ["*"]
    allow_methods = ["GET", "OPTIONS"]
    allow_headers = ["Content-Type"]
  }

  tags = {
    Project     = "pennymac-stocks-serverless-pipeline"
    Environment = "dev"
    ManagedBy   = "terraform"
  }
}

resource "aws_apigatewayv2_integration" "api_lambda_integration" {
  api_id                 = aws_apigatewayv2_api.stocks_api.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.api_lambda.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "get_movers" {
  api_id    = aws_apigatewayv2_api.stocks_api.id
  route_key = "GET /movers"
  target    = "integrations/${aws_apigatewayv2_integration.api_lambda_integration.id}"
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.stocks_api.id
  name        = "$default"
  auto_deploy = true

  tags = {
    Project     = "pennymac-stocks-serverless-pipeline"
    Environment = "dev"
    ManagedBy   = "terraform"
  }
}

resource "aws_lambda_permission" "allow_api_gateway_to_call_api_lambda" {
  statement_id  = "AllowAPIGatewayInvokeApiLambda"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.api_lambda.function_name
  principal     = "apigateway.amazonaws.com"

  source_arn = "${aws_apigatewayv2_api.stocks_api.execution_arn}/*/*"
}



resource "aws_cloudwatch_event_rule" "daily_stock_ingestion" {
  name                = "pennymac-daily-stock-ingestion"
  description         = "Runs the stock mover ingestion Lambda once per day"
  schedule_expression = "cron(0 14 ? * MON-FRI *)"

  tags = {
    Project     = "pennymac-stocks-serverless-pipeline"
    Environment = "dev"
    ManagedBy   = "terraform"
  }
}

resource "aws_cloudwatch_event_target" "daily_stock_ingestion_target" {
  rule      = aws_cloudwatch_event_rule.daily_stock_ingestion.name
  target_id = "pennymac-stock-mover-ingest"
  arn       = aws_lambda_function.ingest_lambda.arn
}

resource "aws_lambda_permission" "allow_eventbridge_to_call_ingest_lambda" {
  statement_id  = "AllowEventBridgeInvokeIngestLambda"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.ingest_lambda.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.daily_stock_ingestion.arn
}