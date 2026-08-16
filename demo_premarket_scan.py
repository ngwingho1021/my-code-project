#!/usr/bin/env python3
"""
演示: 盤前Gap-Up Momentum掃描

這個腳本展示了完整的工作流程：
1. 連接Alpaca獲取盤前數據
2. 掃描gap-up股票
3. 識別技術面（支撐位/阻力位）
4. 準備信號給IBKR下單

用途：
- 驗證Alpaca整合是否正常
- 展示系統如何工作
- 測試盤前掃描邏輯
"""

import asyncio
import logging
import sys
from pathlib import Path
from datetime import datetime
import json

sys.path.insert(0, str(Path(__file__).parent))

from core.alpaca_client import AlpacaClient
from core.data_fetcher import DataFetcher, GapAnalysis
from config.settings import TRADING_HOURS
import pytz

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class PremarketScanner:
    """盤前掃描系統"""

    def __init__(self):
        self.fetcher = None
        self.tz = pytz.timezone(TRADING_HOURS["timezone"])

        # 美股常見的盤前活躍股票
        self.watchlist = [
            "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA",
            "META", "NVDA", "AMD", "NFLX", "AVGO",
            "ADBE", "CRM", "INTC", "TXN", "ASML",
            "MU", "QCOM", "PYPL", "SQ", "SHOP",
        ]

    async def initialize(self):
        """初始化掃描器"""
        self.fetcher = DataFetcher()
        await self.fetcher.initialize()
        logger.info("✅ PremarketScanner 初始化完成")

    async def close(self):
        """關閉連接"""
        if self.fetcher:
            await self.fetcher.close()

    async def run_scan(self) -> list:
        """
        執行完整的盤前掃描

        Returns:
            符合條件的候選股票列表
        """
        logger.info("=" * 80)
        logger.info("🚀 盤前Gap-Up Momentum掃描開始")
        logger.info("=" * 80)

        # 檢查市場狀態
        market_status = await self.fetcher.check_market_hours()
        logger.info(f"📍 市場狀態: {market_status}")

        if market_status not in ["premarket", "market"]:
            logger.warning("⚠️ 當前不在盤前或交易時段")
            logger.info("   盤前時段: 4:00 AM - 9:30 AM EST")
            logger.info("   交易時段: 9:30 AM - 4:00 PM EST")

        # 掃描gap-up
        logger.info(f"\n📊 掃描 {len(self.watchlist)} 個符號...")
        gapups = await self.fetcher.scan_gapups(self.watchlist)

        if not gapups:
            logger.warning("⚠️ 未找到符合條件的gap-up股票")
            return []

        # 詳細分析每個候選
        logger.info("\n" + "=" * 80)
        logger.info("📈 候選股票分析 (按Gap%排序)")
        logger.info("=" * 80)

        candidates = []

        for i, gap in enumerate(gapups, 1):
            logger.info(f"\n[{i}] {gap.symbol}")
            logger.info(f"    Gap: {gap.gap_pct:+.2f}%")
            logger.info(f"    Price: ${gap.current_price:.2f}")
            logger.info(f"    Rel Volume: {gap.rel_volume:.2f}x")
            logger.info(f"    Today Volume: {gap.volume_today:,} shares")
            logger.info(f"    20D Avg Volume: {gap.avg_volume_20d:,.0f} shares")

            # 獲取技術面
            try:
                support, resistance = await self.fetcher.identify_support_resistance(gap.symbol)

                if support:
                    logger.info(f"    Support: {[f'${s:.2f}' for s in support]}")
                if resistance:
                    logger.info(f"    Resistance: {[f'${r:.2f}' for r in resistance]}")

                # 計算風險/收益比
                if support:
                    rr_ratio = (resistance[0] - gap.current_price) / (gap.current_price - support[0])
                    logger.info(f"    Risk/Reward: {rr_ratio:.2f}:1 (1:1 = 中性)")

            except Exception as e:
                logger.warning(f"    ⚠️ 技術面分析失敗: {e}")

            # 添加到候選列表
            candidates.append({
                "symbol": gap.symbol,
                "gap_pct": gap.gap_pct,
                "current_price": gap.current_price,
                "rel_volume": gap.rel_volume,
                "volume": gap.volume_today,
            })

        return candidates

    def generate_trading_signal(self, candidates: list) -> dict:
        """
        生成交易信號（給IBKR使用）

        Returns:
            交易信號字典
        """
        logger.info("\n" + "=" * 80)
        logger.info("⚡ 交易信號生成")
        logger.info("=" * 80)

        signals = {
            "timestamp": datetime.now(self.tz).isoformat(),
            "market_status": "premarket",
            "candidates": candidates,
            "total_opportunities": len(candidates),
        }

        if candidates:
            logger.info(f"✅ 發現 {len(candidates)} 個交易機會")
            logger.info("   待IBKR執行以下信號：")
            for candidate in candidates[:5]:
                logger.info(
                    f"   - {candidate['symbol']}: "
                    f"Gap {candidate['gap_pct']:+.2f}% | "
                    f"Vol {candidate['rel_volume']:.2f}x"
                )
        else:
            logger.warning("❌ 未發現符合條件的交易機會")

        return signals

    async def save_scan_result(self, signals: dict, filename: str = "premarket_scan_result.json"):
        """保存掃描結果"""
        try:
            with open(filename, 'w') as f:
                json.dump(signals, f, indent=2)
            logger.info(f"\n💾 掃描結果已保存: {filename}")
        except Exception as e:
            logger.error(f"❌ 保存結果失敗: {e}")


async def main():
    """主程序"""
    scanner = PremarketScanner()

    try:
        # 初始化
        await scanner.initialize()

        # 執行掃描
        candidates = await scanner.run_scan()

        # 生成信號
        signals = scanner.generate_trading_signal(candidates)

        # 保存結果
        await scanner.save_scan_result(signals)

        # 總結
        logger.info("\n" + "=" * 80)
        logger.info("📋 掃描總結")
        logger.info("=" * 80)
        logger.info(f"發現機會: {signals['total_opportunities']}")
        logger.info(f"時間: {signals['timestamp']}")

        if candidates:
            top = candidates[0]
            logger.info(f"\n🏆 Top機會: {top['symbol']}")
            logger.info(f"   Gap: {top['gap_pct']:+.2f}%")
            logger.info(f"   相對成交量: {top['rel_volume']:.2f}x")
            logger.info(f"   當前價格: ${top['current_price']:.2f}")

        logger.info("\n✅ 掃描完成！準備提交給交易執行系統...")
        logger.info("   下一步: 需要IBKR客戶端進行實際下單")

        return 0

    except Exception as e:
        logger.error(f"❌ 掃描失敗: {e}", exc_info=True)
        return 1

    finally:
        await scanner.close()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
