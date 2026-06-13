# PennyMac Stocks Serverless Pipeline

A serverless stock mover dashboard that tracks a small stock watchlist, calculates the largest daily percentage mover, stores the result in DynamoDB, and displays recent mover history through a React frontend.

## Live Demo

Frontend Website:
http://pennymac-stock-mover-dashboard-bf558fd6.s3-website-us-west-2.amazonaws.com

API Endpoint:
https://7c199o6ef5.execute-api.us-west-2.amazonaws.com/movers

Example API request:

```bash
curl https://7c199o6ef5.execute-api.us-west-2.amazonaws.com/movers
```

Example with a custom limit:

```bash
curl "https://7c199o6ef5.execute-api.us-west-2.amazonaws.com/movers?limit=3"
```

## Project Overview

This project builds a serverless stock data pipeline using AWS. The pipeline runs on a schedule, checks a watchlist of major stocks, calculates which stock had the largest daily percentage movement, stores the result, and exposes the data through an API and frontend dashboard.

The stock watchlist includes:

```text
AAPL, MSFT, GOOGL, AMZN, TSLA, NVDA
```

The frontend displays:

* The latest top mover
* A daily market insight summary
* The most recent mover records
* Gain/loss color coding
* Data retrieved from the deployed API Gateway endpoint

## Architecture

```text
EventBridge Schedule
        ↓
Ingestion Lambda
        ↓
Massive Stock API
        ↓
DynamoDB
        ↓
API Lambda
        ↓
API Gateway GET /movers
        ↓
React Frontend
        ↓
S3 Static Website Hosting
```

## AWS Services Used

* **AWS Lambda**: Runs backend logic for stock ingestion and API retrieval
* **Amazon DynamoDB**: Stores daily top mover records
* **Amazon API Gateway**: Exposes the `/movers` REST endpoint
* **Amazon EventBridge**: Runs the ingestion Lambda on a weekday schedule
* **Amazon S3**: Hosts the React frontend as a static website
* **AWS IAM**: Provides least-privilege permissions for Lambda functions
* **CloudWatch Logs**: Captures Lambda logs for debugging and operational visibility
* **Terraform**: Manages AWS infrastructure as code

## How the Pipeline Works

1. EventBridge triggers the ingestion Lambda on a weekday schedule.
2. The ingestion Lambda calls the Massive previous-day stock endpoint for each ticker in the watchlist.
3. For each stock, the Lambda reads the opening price, closing price, ticker symbol, and market timestamp.
4. The Lambda calculates daily percentage change:

```text
((close_price - open_price) / open_price) * 100
```

5. The stock with the largest absolute percentage movement is selected as the daily top mover.
6. The top mover is saved to DynamoDB.
7. The API Lambda reads recent mover records from DynamoDB.
8. API Gateway exposes the data through `GET /movers`.
9. The React frontend calls the API and displays the results.

## API Design

### `GET /movers`

Returns recent stock mover records.

Example response:

```json
{
  "count": 7,
  "limit": 7,
  "movers": [
    {
      "date": "2026-06-10",
      "ticker": "TSLA",
      "percent_change": -2.54,
      "close_price": 381.59
    }
  ]
}
```

### `GET /movers?limit=3`

Returns a custom number of recent records.

The API supports a `limit` query parameter with a default of 7 and a maximum of 30.

### Custom Response Headers

The API includes custom response headers to make the response easier to debug and more production-like:

```text
Cache-Control: public, max-age=60
X-Data-Source: DynamoDB
X-Record-Limit: 7
```

## Error Handling and Robustness

The ingestion logic includes several safeguards:

* Checks that the Massive API response status is valid before using the data
* Checks that stock results exist before reading open and close prices
* Handles `429 Too Many Requests` responses with retry logic
* Slows down requests between tickers to reduce free-tier rate limit issues
* Uses safe custom error messages instead of exposing request URLs that could contain API keys
* Continues processing other tickers if one ticker fails
* Raises an error if no valid stock data can be retrieved

The Massive API free tier can rate limit requests quickly, so the ingestion Lambda waits between ticker requests. This makes the Lambda slower, but more reliable. Since the job only runs once per day, reliability is more important than speed.

## Security Considerations

* API keys are not committed to GitHub
* `.env` files are ignored through `.gitignore`
* Terraform uses a sensitive variable for the Massive API key
* Lambda receives secrets through environment variables
* The ingestion Lambda has permission to write to DynamoDB
* The API Lambda has permission to read from DynamoDB
* IAM permissions are separated by function responsibility
* CloudWatch logging is enabled for debugging and visibility

## Key Trade-offs

### Previous Day Stock Data

This project uses Massive’s previous-day stock endpoint instead of same-day intraday data.

This avoids incomplete data because the scheduled Lambda could run before the market closes. By using the previous completed trading day, the pipeline works with complete open and close prices.

### Market Date vs. Runtime Date

The pipeline stores the market date from the stock API timestamp instead of simply using the date when the Lambda runs.

This matters because if the Lambda runs on a Monday morning, the previous completed trading day may be Friday. Using the market timestamp makes the stored date more accurate.

### DynamoDB Scan

The API Lambda uses `scan()` to read recent mover records from DynamoDB.

For this project, that is acceptable because the table stores only one record per trading day. For a larger production system, I would use a DynamoDB query pattern or secondary index optimized for retrieving records by date.

### Sample Data

Some older records were manually added for frontend testing so the dashboard could demonstrate recent history and the API record limit behavior. In normal usage, the EventBridge schedule adds one top mover record per trading day.

## Local Development

### Backend

The backend is written in Python and deployed as AWS Lambda functions.

Main files:

```text
backend/ingest/handler.py
backend/api/handler.py
```

The ingestion Lambda calculates and stores the daily top mover.

The API Lambda returns recent mover history from DynamoDB.

### Frontend

The frontend is a React app created with Vite.

To run locally:

```bash
cd frontend
npm install
npm run dev
```

Local frontend URL:

```text
http://localhost:5173/
```

To build for production:

```bash
npm run build
```

The production build is created in:

```text
frontend/dist
```

## Deployment

### Terraform Infrastructure

Terraform manages the AWS infrastructure.

```bash
cd terraform
terraform init
terraform fmt
terraform plan
terraform apply
```

### Frontend Deployment

After building the React frontend:

```bash
cd frontend
npm run build
```

Upload the build files to S3:

```bash
aws s3 sync dist s3://pennymac-stock-mover-dashboard-bf558fd6 --delete
```

## Repository Structure

```text
backend/
  ingest/
    handler.py
    test_stock_logic.py
  api/
    handler.py

frontend/
  src/
    App.jsx
    App.css
    index.css
  package.json

terraform/
  main.tf
  variables.tf
  outputs.tf

docs/
  architecture.md

README.md
```

## Future Improvements

Given more time, I would improve the project by:

* Moving the stock API key from Lambda environment variables to AWS Secrets Manager
* Adding CloudWatch alarms for Lambda failures
* Adding CI/CD with GitHub Actions
* Adding a more advanced DynamoDB query pattern for larger datasets
* Adding frontend filtering and sorting
* Adding authenticated admin-only endpoints
* Adding unit tests for the API Lambda and ingestion Lambda
