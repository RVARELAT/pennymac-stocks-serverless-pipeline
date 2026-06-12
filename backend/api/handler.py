"""
API Lambda for the PennyMac Stocks Serverless Pipeline.

This Lambda reads stock mover history from DynamoDB and returns it as JSON.

It is connected to API Gateway at:

GET /movers
GET /movers?limit=7
"""

import json
import os
from decimal import Decimal

import boto3


TABLE_NAME = os.getenv("DYNAMODB_TABLE_NAME")
DEFAULT_LIMIT = 7
MAX_LIMIT = 30


def convert_decimal(value):
    """
    DynamoDB stores numbers as Decimal in Python.

    JSON does not understand Decimal, so we convert:
    Decimal("-2.54") -> -2.54
    """

    if isinstance(value, Decimal):
        return float(value)

    return value


def format_item(item):
    """
    Convert one DynamoDB item into clean JSON-friendly data.
    """

    return {
        "date": item["date"],
        "ticker": item["ticker"],
        "percent_change": convert_decimal(item["percent_change"]),
        "close_price": convert_decimal(item["close_price"]),
    }


def get_limit_from_event(event):
    """
    Read the optional limit query parameter from the API request.

    Examples:
    /movers          -> 7 records by default
    /movers?limit=3  -> 3 records
    /movers?limit=10 -> 10 records

    To keep the API safe, the limit cannot be less than 1 or greater than 30.
    """

    query_params = event.get("queryStringParameters") or {}
    raw_limit = query_params.get("limit")

    if raw_limit is None:
        return DEFAULT_LIMIT

    try:
        limit = int(raw_limit)
    except ValueError:
        return DEFAULT_LIMIT

    if limit < 1:
        return DEFAULT_LIMIT

    if limit > MAX_LIMIT:
        return MAX_LIMIT

    return limit


def build_headers(limit):
    """
    Return standard and custom response headers.

    These headers make the API response more professional and easier to debug.
    """

    return {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
        "Cache-Control": "public, max-age=60",
        "X-Data-Source": "DynamoDB",
        "X-Record-Limit": str(limit),
    }


def get_movers(limit):
    """
    Read mover records from DynamoDB.

    For this small project, scan is okay because we only store one item per day.

    Later, for a larger production app, we would design the table for more efficient queries.
    """

    if not TABLE_NAME:
        raise RuntimeError("DYNAMODB_TABLE_NAME environment variable is missing.")

    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(TABLE_NAME)

    response = table.scan()
    items = response.get("Items", [])

    formatted_items = [format_item(item) for item in items]

    # Sort newest date first.
    formatted_items.sort(key=lambda item: item["date"], reverse=True)

    # Return only the requested number of records.
    return formatted_items[:limit]


def lambda_handler(event, context):
    """
    AWS Lambda entry point for the API.

    API Gateway calls this function when someone visits GET /movers.
    """

    try:
        limit = get_limit_from_event(event)
        movers = get_movers(limit)

        return {
            "statusCode": 200,
            "headers": build_headers(limit),
            "body": json.dumps(
                {
                    "count": len(movers),
                    "limit": limit,
                    "movers": movers,
                }
            ),
        }

    except Exception as error:
        print(f"Error retrieving movers: {error}")

        return {
            "statusCode": 500,
            "headers": build_headers(DEFAULT_LIMIT),
            "body": json.dumps(
                {
                    "message": "Failed to retrieve stock movers.",
                }
            ),
        }