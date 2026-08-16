#!/usr/bin/env python3
"""Test Alpaca bars API directly"""

import asyncio
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
import aiohttp

load_dotenv()

API_KEY = os.getenv("ALPACA_API_KEY")
SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")

async def test_bars():
    headers = {
        "APCA-API-KEY-ID": API_KEY,
    }

    url = "https://data.alpaca.markets/v1beta3/stocks/SPY/bars"

    # Try different date formats
    end = datetime.now()
    start = end - timedelta(days=5)

    params = {
        "timeframe": "1Min",
        "limit": 10,
        "start": start.isoformat(),
        "end": end.isoformat(),
    }

    print(f"Testing Alpaca bars API")
    print(f"URL: {url}")
    print(f"Params: {params}")
    print()

    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params, headers=headers) as resp:
            print(f"Status: {resp.status}")
            data = await resp.json()
            print(f"Response: {data}")

if __name__ == "__main__":
    asyncio.run(test_bars())
