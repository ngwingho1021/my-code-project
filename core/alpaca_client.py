"""
Alpaca 數據層 - 免費盤前數據 + 實時行情
用於：
1. 盤前gap檢測（>= 5%）
2. 成交量爆量檢測
3. K線數據獲取（1min、5min、15min）
4. 實時價格推送（WebSocket）

與IBKR的關係：
- Alpaca處理數據和信號生成
- IBKR處理實際交易執行
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from dataclasses import dataclass
import json

import aiohttp
import pytz
from config.settings import ALPACA_API_KEY, ALPACA_SECRET_KEY, ALPACA_BASE_URL, TRADING_HOURS

logger = logging.getLogger(__name__)

# Alpaca API 端點
ALPACA_DATA_URL = "https://data.alpaca.markets"
ALPACA_WS_URL = "wss://data.alpaca.markets/v1beta3/crypto"  # Crypto WS（測試用）
# 股票實時數據需用 REST API

@dataclass
class BarData:
    """K線數據"""
    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int

@dataclass
class QuoteData:
    """報價數據"""
    symbol: str
    bid: float
    ask: float
    bid_size: int
    ask_size: int
    last_trade: float
    last_update: datetime


class AlpacaClient:
    """Alpaca API 客戶端 - 完全非同步"""

    def __init__(self):
        self.api_key = ALPACA_API_KEY
        self.secret_key = ALPACA_SECRET_KEY
        self.base_url = ALPACA_BASE_URL
        self.data_url = ALPACA_DATA_URL
        self.session: Optional[aiohttp.ClientSession] = None
        self.tz = pytz.timezone(TRADING_HOURS["timezone"])

        if not self.api_key or not self.secret_key:
            logger.warning("⚠️ Alpaca API密鑰未設定，請設定環境變數 ALPACA_API_KEY 和 ALPACA_SECRET_KEY")

    async def __aenter__(self):
        """非同步上下文管理"""
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """清理資源"""
        if self.session:
            await self.session.close()

    def _get_headers(self) -> Dict:
        """Alpaca API 標頭"""
        return {
            "APCA-API-KEY-ID": self.api_key,
            "APCA-API-SECRET-KEY": self.secret_key,
        }

    async def get_latest_bars(self, symbols: List[str]) -> Dict[str, BarData]:
        """
        獲取最新K線（1分鐘）

        Args:
            symbols: 股票代碼列表

        Returns:
            {symbol: BarData}
        """
        if not self.session:
            raise RuntimeError("Session not initialized. Use 'async with AlpacaClient() as client:'")

        # 用逗號分隔符號列表
        symbols_param = ",".join(symbols)
        url = f"{self.data_url}/v1beta3/stocks/bars"

        params = {
            "symbols": symbols_param,
            "timeframe": "1Min",
            "limit": 1,  # 只要最新的1根bar
            "sort": "desc",
        }

        try:
            async with self.session.get(
                url,
                params=params,
                headers=self._get_headers(),
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    result = {}

                    for symbol, bars in data.get("bars", {}).items():
                        if bars:
                            bar = bars[0]  # 最新的bar
                            result[symbol] = BarData(
                                symbol=symbol,
                                timestamp=datetime.fromisoformat(bar["t"].replace("Z", "+00:00")),
                                open=bar["o"],
                                high=bar["h"],
                                low=bar["l"],
                                close=bar["c"],
                                volume=bar["v"]
                            )
                    return result
                else:
                    logger.error(f"❌ Alpaca API error: {resp.status}")
                    return {}

        except asyncio.TimeoutError:
            logger.error("⏱️ Alpaca API 超時")
            return {}
        except Exception as e:
            logger.error(f"❌ 獲取K線失敗: {e}")
            return {}

    async def get_bars(
        self,
        symbol: str,
        timeframe: str = "1Min",
        limit: int = 100,
        start: Optional[str] = None,
        end: Optional[str] = None,
    ) -> List[BarData]:
        """
        獲取歷史K線

        Args:
            symbol: 股票代碼
            timeframe: 時間框架（1Min, 5Min, 15Min, 1Hour）
            limit: 返回根數（最大10000）
            start: 開始日期（ISO格式）
            end: 結束日期（ISO格式）

        Returns:
            BarData列表
        """
        if not self.session:
            raise RuntimeError("Session not initialized")

        url = f"{self.data_url}/v1beta3/stocks/{symbol}/bars"

        params = {
            "timeframe": timeframe,
            "limit": min(limit, 10000),
        }

        if start:
            params["start"] = start
        if end:
            params["end"] = end

        try:
            async with self.session.get(
                url,
                params=params,
                headers=self._get_headers(),
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    bars = data.get("bars", [])

                    return [
                        BarData(
                            symbol=symbol,
                            timestamp=datetime.fromisoformat(bar["t"].replace("Z", "+00:00")),
                            open=bar["o"],
                            high=bar["h"],
                            low=bar["l"],
                            close=bar["c"],
                            volume=bar["v"]
                        )
                        for bar in bars
                    ]
                else:
                    logger.error(f"❌ 獲取 {symbol} K線失敗: {resp.status}")
                    return []

        except Exception as e:
            logger.error(f"❌ {symbol} K線獲取錯誤: {e}")
            return []

    async def get_latest_quote(self, symbol: str) -> Optional[QuoteData]:
        """
        獲取最新報價

        Args:
            symbol: 股票代碼

        Returns:
            QuoteData 或 None
        """
        if not self.session:
            raise RuntimeError("Session not initialized")

        url = f"{self.data_url}/v1beta3/stocks/{symbol}/quotes/latest"

        try:
            async with self.session.get(
                url,
                headers=self._get_headers(),
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    quote = data.get("quote", {})

                    return QuoteData(
                        symbol=symbol,
                        bid=quote.get("bp", 0),
                        ask=quote.get("ap", 0),
                        bid_size=quote.get("bs", 0),
                        ask_size=quote.get("as", 0),
                        last_trade=quote.get("c", 0),
                        last_update=datetime.fromisoformat(quote.get("t", "").replace("Z", "+00:00"))
                    )
                else:
                    return None

        except Exception as e:
            logger.error(f"❌ 獲取 {symbol} 報價失敗: {e}")
            return None

    async def get_assets(self, status: str = "active") -> List[Dict]:
        """
        獲取股票列表（過濾條件）

        Args:
            status: 狀態（active, inactive）

        Returns:
            資產列表
        """
        if not self.session:
            raise RuntimeError("Session not initialized")

        url = f"{self.base_url}/v2/assets"

        params = {
            "status": status,
            "asset_class": "us_equity",
        }

        try:
            async with self.session.get(
                url,
                params=params,
                headers=self._get_headers(),
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
                else:
                    logger.error(f"❌ 獲取資產列表失敗: {resp.status}")
                    return []

        except Exception as e:
            logger.error(f"❌ 獲取資產列表錯誤: {e}")
            return []

    async def get_account(self) -> Optional[Dict]:
        """
        獲取賬戶信息

        Returns:
            賬戶數據或None
        """
        if not self.session:
            raise RuntimeError("Session not initialized")

        url = f"{self.base_url}/v2/account"

        try:
            async with self.session.get(
                url,
                headers=self._get_headers(),
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
                else:
                    return None

        except Exception as e:
            logger.error(f"❌ 獲取賬戶信息失敗: {e}")
            return None

    def is_premarket(self) -> bool:
        """判斷是否盤前時段（4:00 AM - 9:30 AM EST）"""
        now = datetime.now(self.tz)
        hour = now.hour
        minute = now.minute

        premarket_start = 4  # 4:00 AM
        market_open = 9      # 9:30 AM

        # 在4:00-9:30之間
        return (
            (hour > premarket_start) or
            (hour == market_open and minute < 30)
        ) and now.weekday() < 5  # 非週末

    def is_market_hours(self) -> bool:
        """判斷是否交易時段（9:30 AM - 4:00 PM EST）"""
        now = datetime.now(self.tz)
        hour = now.hour
        minute = now.minute

        # 在9:30-16:00之間
        return (
            (hour > 9 or (hour == 9 and minute >= 30)) and
            hour < 16
        ) and now.weekday() < 5

    def is_afterhours(self) -> bool:
        """判斷是否盤後時段（4:00 PM - 8:00 PM EST）"""
        now = datetime.now(self.tz)
        hour = now.hour

        return 16 <= hour < 20 and now.weekday() < 5


# 測試用的非同步入口
async def test_alpaca():
    """簡單測試Alpaca連接"""
    async with AlpacaClient() as client:
        logger.info("🔌 連接Alpaca API...")

        # 獲取賬戶信息
        account = await client.get_account()
        if account:
            logger.info(f"✅ 賬戶連接成功")
            logger.info(f"   現金: ${account.get('cash', 0):.2f}")
            logger.info(f"   淨值: ${account.get('portfolio_value', 0):.2f}")

        # 測試獲取K線
        symbols = ["AAPL", "TSLA", "SPY"]
        bars = await client.get_latest_bars(symbols)
        logger.info(f"✅ 獲取最新K線: {len(bars)} 個")
        for symbol, bar in list(bars.items())[:2]:
            logger.info(f"   {symbol}: ${bar.close:.2f} (vol: {bar.volume})")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(test_alpaca())
