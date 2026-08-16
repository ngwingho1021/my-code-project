#!/usr/bin/env python3
"""Test Alpaca bars API directly"""

import asyncio
import os
import base64
from datetime import datetime, timedelta
from dotenv import load_dotenv
import aiohttp

load_dotenv()

API_KEY = os.getenv("ALPACA_API_KEY")
SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")

async def test_bars():
    # Try Basic Auth first
    credentials = f"{API_KEY}:{SECRET_KEY}"
    encoded = base64.b64encode(credentials.encode()).decode()

    headers = {
        "Authorization": f"Basic {encoded}",
    }

    url = "https://paper-api.alpaca.markets/v1beta3/stocks/SPY/bars"

    # Use recent dates (not future dates)
    end = datetime(2024, 3, 31)
    start = datetime(2024, 3, 1)

    params = {
        "timeframe": "1Min",
        "limit": 10,
        "start": start.isoformat(),
        "end": end.isoformat(),
    }

    print(f"Testing Alpaca bars API with Basic Auth")
    print(f"URL: {url}")
    print(f"Params: {params}")
    print()

    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params, headers=headers) as resp:
            print(f"Status: {resp.status}")
            text = await resp.text()
            print(f"Response: {text}")

if __name__ == "__main__":
    asyncio.run(test_bars())
