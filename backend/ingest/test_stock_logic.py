"""
Local test script

This script tests the main stock mover logic before we put it into AWS.

What it does:
1. Reads our Massive API key from a local .env file.
2. Calls Massive's Previous Day Bar endpoint for each stock.
3. Gets the open price and close price.
4. Calculates percent change.
5. Finds the stock with the biggest move up or down.

This is NOT the final Lambda yet.
This is just a local test version so we can make sure the logic works first.
"""
# Python built-in tools
import os
import time
from datetime import datetime, timezone
# Installed packages
import requests
from dotenv import load_dotenv

# This loads values from the .env file.
# Example .env:
# MASSIVE_API_KEY=your_api_key_here
load_dotenv()

# This gets API key from the .env file.
API_KEY = os.getenv("MASSIVE_API_KEY")

# Watchlist from the project instructions.
WATCHLIST = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA"]


def convert_timestamp_to_date(timestamp_ms):
    """
    Massive gives us the date as a Unix timestamp in milliseconds.

    Example:
    1605042000000

    We convert that into a readable date like:

    2020-11-10
    """

    timestamp_seconds = timestamp_ms / 1000
    date = datetime.fromtimestamp(timestamp_seconds, timezone.utc)
    return date.strftime("%Y-%m-%d")


def calculate_percent_change(open_price, close_price):
    """
    Calculate percent change using the formula from the project prompt.

    Formula:
    ((Close - Open) / Open) * 100

    Example:
    Open = 100
    Close = 110

    ((110 - 100) / 100) * 100 = 10%
    """

    return ((close_price - open_price) / open_price) * 100


def fetch_previous_day_data(ticker):
    """
    Fetch previous trading day stock data for one ticker.

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
        # If Massive says we are making too many requests, wait and try again.
        if response.status_code == 429:
            wait_time = 3 * (attempt + 1)
            print(f"Rate limited for {ticker}. Waiting {wait_time} seconds...")
            time.sleep(wait_time)
            continue
        # For any other error, do not continue. Stop and tell us something went wrong.”
        # Example: bad API key, rate limit, server error.
        response.raise_for_status()
        if response.status_code >= 400:
            raise RuntimeError(
                f"Massive API request failed for {ticker}. "
                f"Status code: {response.status_code}"
            )
            
        break

    else:
        raise RuntimeError(f"Rate limit continued after {max_retries} attempts for {ticker}")


    data = response.json()

    # Check that Massive says the request was successful.
    if data.get("status") != "OK":
        raise ValueError(
            f"Massive returned status {data.get('status')} for {ticker}"
        )

    # Check that Massive returned at least one result.
    if data.get("resultsCount", 0) == 0:
        raise ValueError(f"No results returned for {ticker}")

    results = data.get("results", [])

    if not results:
        raise ValueError(f"Missing results array for {ticker}")

    # The previous day endpoint should return one result.
    result = results[0]

    # These are the fields from Massive:
    # o = open price
    # c = close price
    # t = timestamp in milliseconds
    open_price = result["o"]
    close_price = result["c"]
    timestamp_ms = result["t"]

    # The sample response has results[0].T,
    # but the MASSIVE docs also show a top-level ticker field.
    # This makes our code safe either way.
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
    Loop through every stock and find the biggest mover.

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
            # If one stock fails, we print the error and keep going.
            # This is better than crashing the whole script immediately.
            print(f"Error fetching {ticker}: {error}")

    if not movers:
        raise RuntimeError("No stock data could be fetched.")

    top_mover = max(movers, key=lambda stock: abs(stock["percent_change"]))

    return top_mover


if __name__ == "__main__":
    # Make sure the API key exists before calling Massive.
    if not API_KEY:
        raise RuntimeError("MASSIVE_API_KEY is missing. Check your .env file.")

    winner = find_top_mover()

    print("\nTop mover:")
    print(winner)