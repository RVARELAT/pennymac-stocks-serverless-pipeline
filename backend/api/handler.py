"""
API Lambda for the PennyMac Stocks Serverless Pipeline.

This Lambda reads stock mover history from DynamoDB and returns it as JSON.

It will be connected to API Gateway later at:

GET /movers
"""

import json
import os
from decimal import Decimal

import boto3


TABLE_NAME = os.getenv("DYNAMODB_TABLE_NAME")


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

    DynamoDB item example:
    {
        "date": "2026-06-10",
        "ticker": "TSLA",
        "percent_change": Decimal("-2.54"),
        "close_price": Decimal("381.59")
    }

    API response item:
    {
        "date": "2026-06-10",
        "ticker": "TSLA",
        "percent_change": -2.54,
        "close_price": 381.59
    }
    """

    return {
        "date": item["date"],
        "ticker": item["ticker"],
        "percent_change": convert_decimal(item["percent_change"]),
        "close_price": convert_decimal(item["close_price"]),
    }


def get_last_7_movers():
    """
    Read mover records from DynamoDB.
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

    # Return only the last 7 records.
    return formatted_items[:7]


def lambda_handler(event, context):
    """
    AWS Lambda entry point for the API.

    API Gateway will call this function when someone visits GET /movers.
    """

    try:
        movers = get_last_7_movers()

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps(
                {
                    "count": len(movers),
                    "movers": movers,
                }
            ),
        }

    except Exception as error:
        print(f"Error retrieving movers: {error}")

        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps(
                {
                    "message": "Failed to retrieve stock movers.",
                }
            ),
        }