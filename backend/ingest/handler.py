"""
Ingestion Lambda for the PennyMac Stocks Serverless Pipeline

This Lambda will eventually be triggered by Amazon EventBridge once per day.

What it does:
1. Reads the Massive API key from an environment variable.
2. Calls Massive's Previous Day Bar endpoint for each stock in the watchlist.
3. Calculates percent change from open price to close price.
4. Finds the stock with the biggest move up or down.
5. Returns the top mover.
"""

import json
import os
import time
from datetime import datetime, timezone

import requests


API_KEY = os.getenv("MASSIVE_API_KEY")

WATCHLIST = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA"]


def convert_timestamp_to_date(timestamp_ms):
    """
    Convert Massive's Unix millisecond timestamp into a readable date.

    Example:
    1605042000000 -> 2020-11-10
    """

    timestamp_seconds = timestamp_ms / 1000
    date = datetime.fromtimestamp(timestamp_seconds, timezone.utc)
    return date.strftime("%Y-%m-%d")


def calculate_percent_change(open_price, close_price):
    """
    Calculate percent change from open to close.

    Formula:
    ((Close - Open) / Open) * 100
    """

    return ((close_price - open_price) / open_price) * 100


def fetch_previous_day_data(ticker):
    """
    Fetch previous trading day OHLC data for one ticker from Massive.

    Endpoint:
    /v2/aggs/ticker/{stocksTicker}/prev
    
    Why use this endpoint?
    Because it gives us the previous completed trading day.

    That is safer than using today's data because the market might still be open.
    """

    url = f"https://api.massive.com/v2/aggs/ticker/{ticker}/prev"

    params = {
        "adjusted": "true",
        "apiKey": API_KEY,
    }

    max_retries = 3

    for attempt in range(max_retries):
        response = requests.get(url, params=params, timeout=10)

        if response.status_code == 429:
            wait_time = 3 * (attempt + 1)
            print(f"Rate limited for {ticker}. Waiting {wait_time} seconds...")
            time.sleep(wait_time)
            continue

        if response.status_code >= 400:
            raise RuntimeError(
                f"Massive API request failed for {ticker}. "
                f"Status code: {response.status_code}"
            )

        break
    else:
        raise RuntimeError(
            f"Rate limit continued after {max_retries} attempts for {ticker}"
        )

    data = response.json()

    if data.get("status") != "OK":
        raise ValueError(f"Massive returned status {data.get('status')} for {ticker}")

    if data.get("resultsCount", 0) == 0:
        raise ValueError(f"No results returned for {ticker}")

    results = data.get("results", [])

    if not results:
        raise ValueError(f"Missing results array for {ticker}")

    result = results[0]

    open_price = result["o"]
    close_price = result["c"]
    timestamp_ms = result["t"]
    ticker_symbol = result.get("T", data.get("ticker", ticker))

    market_date = convert_timestamp_to_date(timestamp_ms)

    return {
        "date": market_date,
        "ticker": ticker_symbol,
        "open_price": open_price,
        "close_price": close_price,
    }


def find_top_mover():
    """
    Check every stock in the watchlist and return the biggest mover.
    
    Biggest mover means largest absolute percent change.

    Example:
    AAPL = +2%
    TSLA = -5%
    NVDA = +3%

    TSLA wins because abs(-5) = 5, which is the biggest move.
    """

    movers = []

    for ticker in WATCHLIST:
        try:
            stock_data = fetch_previous_day_data(ticker)

            percent_change = calculate_percent_change(
                stock_data["open_price"],
                stock_data["close_price"],
            )

            mover = {
                "date": stock_data["date"],
                "ticker": stock_data["ticker"],
                "percent_change": round(percent_change, 2),
                "close_price": stock_data["close_price"],
            }

            movers.append(mover)

            print(
                f"{mover['date']} | "
                f"{mover['ticker']}: "
                f"{mover['percent_change']}% | "
                f"close=${mover['close_price']}"
            )
            # Slow down between API calls to reduce free-tier rate limit issues.
            time.sleep(12)

        except Exception as error:
            print(f"Error fetching {ticker}: {error}")

    if not movers:
        raise RuntimeError("No stock data could be fetched.")

    top_mover = max(movers, key=lambda stock: abs(stock["percent_change"]))

    return top_mover


def lambda_handler(event, context):
    """
    AWS Lambda entry point.

    AWS Lambda looks for this function when it runs the file.

    event = data AWS passes into the Lambda
    context = information about the Lambda runtime
    """

    if not API_KEY:
        raise RuntimeError("MASSIVE_API_KEY environment variable is missing.")

    top_mover = find_top_mover()

    return {
        "statusCode": 200,
        "body": json.dumps(
            {
                "message": "Top mover calculated successfully.",
                "top_mover": top_mover,
            }
        ),
    }