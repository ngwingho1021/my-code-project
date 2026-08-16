"""
統一數據獲取層 - Gap檢測、成交量分析、技術指標
與Alpaca無縫集成，提供掃描器所需的所有數據
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass

import pandas as pd
import numpy as np
from core.alpaca_client import AlpacaClient, BarData
from config.settings import SCANNER, TRADING_HOURS
import pytz

logger = logging.getLogger(__name__)

@dataclass
class GapAnalysis:
    """Gap分析結果"""
    symbol: str
    previous_close: float
    current_price: float
    gap_pct: float  # % (可正可負)
    is_gapup: bool  # >= 5%
    volume_today: int
    avg_volume_20d: float
    rel_volume: float  # 今日成交量 / 20日平均


class DataFetcher:
    """數據獲取和分析引擎"""

    def __init__(self):
        self.alpaca = None
        self.tz = pytz.timezone(TRADING_HOURS["timezone"])
        self._cache = {}  # K線數據緩存

    async def initialize(self):
        """初始化Alpaca客戶端"""
        self.alpaca = AlpacaClient()
        self.alpaca.session = __import__('aiohttp').ClientSession()
        logger.info("✅ DataFetcher 初始化完成")

    async def close(self):
        """關閉連接"""
        if self.alpaca and self.alpaca.session:
            await self.alpaca.session.close()

    async def check_market_hours(self) -> str:
        """
        檢查市場狀態

        Returns:
            "premarket" / "market" / "afterhours" / "closed"
        """
        now = datetime.now(self.tz)

        if now.weekday() >= 5:  # 週末
            return "closed"

        hour = now.hour
        minute = now.minute

        if hour < 4 or hour >= 20:
            return "closed"
        elif hour < 9 or (hour == 9 and minute < 30):
            return "premarket"
        elif hour < 16:
            return "market"
        else:
            return "afterhours"

    async def get_bars_dataframe(
        self,
        symbol: str,
        timeframe: str = "1Min",
        days_back: int = 5,
    ) -> Optional[pd.DataFrame]:
        """
        獲取K線數據並轉換為DataFrame

        Args:
            symbol: 股票代碼
            timeframe: 時間框架
            days_back: 往回幾天

        Returns:
            DataFrame 或 None
        """
        if not self.alpaca:
            logger.error("❌ Alpaca客戶端未初始化")
            return None

        # 計算日期範圍
        end = datetime.now(self.tz)
        start = end - timedelta(days=days_back)

        try:
            bars = await self.alpaca.get_bars(
                symbol,
                timeframe=timeframe,
                limit=10000,
                start=start.isoformat(),
                end=end.isoformat(),
            )

            if not bars:
                logger.warning(f"⚠️ {symbol} 無K線數據")
                return None

            df = pd.DataFrame({
                'timestamp': [bar.timestamp for bar in bars],
                'open': [bar.open for bar in bars],
                'high': [bar.high for bar in bars],
                'low': [bar.low for bar in bars],
                'close': [bar.close for bar in bars],
                'volume': [bar.volume for bar in bars],
            })

            df.set_index('timestamp', inplace=True)
            df = df.sort_index()

            return df

        except Exception as e:
            logger.error(f"❌ {symbol} 獲取數據失敗: {e}")
            return None

    async def calculate_gap(self, symbol: str) -> Optional[GapAnalysis]:
        """
        計算盤前gap

        Args:
            symbol: 股票代碼

        Returns:
            GapAnalysis 或 None
        """
        try:
            # 獲取今日數據（盤前1分鐘bar）
            bars_today = await self.alpaca.get_bars(
                symbol,
                timeframe="1Min",
                limit=10,
                start=datetime.now(self.tz).date().isoformat(),
            )

            if not bars_today:
                logger.warning(f"⚠️ {symbol} 今天無數據")
                return None

            today_bar = bars_today[0]
            current_price = today_bar.close
            volume_today = sum(bar.volume for bar in bars_today)

            # 獲取昨日收盤（前5天的數據）
            start = (datetime.now(self.tz) - timedelta(days=5)).date().isoformat()
            end = (datetime.now(self.tz) - timedelta(days=1)).date().isoformat()

            bars_prev = await self.alpaca.get_bars(
                symbol,
                timeframe="1Day",
                limit=5,
                start=start,
                end=end,
            )

            if not bars_prev:
                logger.warning(f"⚠️ {symbol} 無前期數據")
                return None

            prev_bar = bars_prev[-1]  # 最後一個bar（最近的）
            previous_close = prev_bar.close

            # 計算gap和相對成交量
            gap_pct = ((current_price - previous_close) / previous_close) * 100

            # 計算20日平均成交量
            bars_20d = await self.alpaca.get_bars(
                symbol,
                timeframe="1Day",
                limit=20,
            )

            avg_volume_20d = np.mean([bar.volume for bar in bars_20d]) if bars_20d else volume_today
            rel_volume = volume_today / avg_volume_20d if avg_volume_20d > 0 else 1.0

            is_gapup = gap_pct >= SCANNER.gap_up_pct_min

            return GapAnalysis(
                symbol=symbol,
                previous_close=previous_close,
                current_price=current_price,
                gap_pct=gap_pct,
                is_gapup=is_gapup,
                volume_today=volume_today,
                avg_volume_20d=avg_volume_20d,
                rel_volume=rel_volume,
            )

        except Exception as e:
            logger.error(f"❌ {symbol} gap計算失敗: {e}")
            return None

    async def scan_gapups(self, symbols: List[str]) -> List[GapAnalysis]:
        """
        掃描gap-up股票

        Args:
            symbols: 股票代碼列表

        Returns:
            GapAnalysis列表（已按gap%排序）
        """
        logger.info(f"🔍 掃描 {len(symbols)} 個符號...")

        results = []
        tasks = [self.calculate_gap(symbol) for symbol in symbols]

        # 並行計算gap
        gap_analyses = await asyncio.gather(*tasks, return_exceptions=True)

        for analysis in gap_analyses:
            if isinstance(analysis, GapAnalysis):
                # 過濾條件
                if (
                    analysis.is_gapup and
                    analysis.rel_volume >= SCANNER.rel_volume_min and
                    analysis.current_price >= SCANNER.price_min and
                    analysis.current_price <= SCANNER.price_max
                ):
                    results.append(analysis)
                    logger.info(
                        f"✅ {analysis.symbol}: gap {analysis.gap_pct:+.2f}% "
                        f"| rel_vol {analysis.rel_volume:.2f}x "
                        f"| ${analysis.current_price:.2f}"
                    )

        # 按gap%降序排序
        results.sort(key=lambda x: x.gap_pct, reverse=True)

        logger.info(f"📊 找到 {len(results)} 個gap-up機會")
        return results

    async def get_intraday_volume_profile(
        self,
        symbol: str,
        lookback_days: int = 5,
    ) -> Dict[float, int]:
        """
        獲取價格成交量分佈（用於支撐位/阻力位分析）

        Args:
            symbol: 股票代碼
            lookback_days: 往回幾天

        Returns:
            {price_level: volume_count}
        """
        df = await self.get_bars_dataframe(symbol, timeframe="1Min", days_back=lookback_days)

        if df is None or df.empty:
            return {}

        # 按價格分bucket統計成交量
        df['price_bucket'] = (df['close'] * 4).round() / 4  # 四分之一美元精度
        volume_profile = df.groupby('price_bucket')['volume'].sum().to_dict()

        return volume_profile

    async def identify_support_resistance(
        self,
        symbol: str,
        lookback_days: int = 5,
    ) -> Tuple[List[float], List[float]]:
        """
        識別支撐位和阻力位

        Args:
            symbol: 股票代碼
            lookback_days: 往回幾天

        Returns:
            (支撐位列表, 阻力位列表)
        """
        df = await self.get_bars_dataframe(symbol, timeframe="1Min", days_back=lookback_days)

        if df is None or df.empty:
            return [], []

        # 簡單實現：找局部低點（支撐）和高點（阻力）
        close_prices = df['close'].values

        support = []
        resistance = []

        # 尋找局部極值
        for i in range(10, len(close_prices) - 10):
            window = close_prices[i-10:i+10]

            # 局部低點 = 支撐
            if close_prices[i] == window.min():
                support.append(float(close_prices[i]))

            # 局部高點 = 阻力
            if close_prices[i] == window.max():
                resistance.append(float(close_prices[i]))

        # 去重並排序
        support = sorted(list(set(support)), reverse=True)[:3]  # 取前3個
        resistance = sorted(list(set(resistance)))[:3]

        return support, resistance


# 使用示例
async def example_usage():
    """測試數據獲取"""
    fetcher = DataFetcher()
    await fetcher.initialize()

    try:
        # 檢查市場狀態
        market_status = await fetcher.check_market_hours()
        logger.info(f"📍 市場狀態: {market_status}")

        # 掃描gap-up
        test_symbols = ["AAPL", "TSLA", "AMD", "NVDA", "NFLX"]
        gapups = await fetcher.scan_gapups(test_symbols)

        for gap in gapups[:3]:
            logger.info(f"\n{gap.symbol}:")
            logger.info(f"  Gap: {gap.gap_pct:+.2f}%")
            logger.info(f"  Rel Vol: {gap.rel_volume:.2f}x")

            # 獲取支撐位/阻力位
            support, resistance = await fetcher.identify_support_resistance(gap.symbol)
            logger.info(f"  Support: {[f'${s:.2f}' for s in support]}")
            logger.info(f"  Resistance: {[f'${r:.2f}' for r in resistance]}")

    finally:
        await fetcher.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(example_usage())
