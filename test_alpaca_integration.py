#!/usr/bin/env python3
"""
測試Alpaca API集成
- 驗證API連接
- 測試數據獲取
- 測試gap檢測
"""

import asyncio
import logging
import sys
from pathlib import Path

# 添加項目根路徑
sys.path.insert(0, str(Path(__file__).parent))

from core.alpaca_client import AlpacaClient
from core.data_fetcher import DataFetcher
from config.settings import ALPACA_API_KEY, ALPACA_SECRET_KEY

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def test_alpaca_connection():
    """測試1: Alpaca API連接"""
    logger.info("=" * 60)
    logger.info("測試1: Alpaca API連接")
    logger.info("=" * 60)

    if not ALPACA_API_KEY or not ALPACA_SECRET_KEY:
        logger.error("❌ 未設定Alpaca API密鑰")
        logger.error("   請設定環境變數:")
        logger.error("   - ALPACA_API_KEY")
        logger.error("   - ALPACA_SECRET_KEY")
        logger.error("   或複製 .env.example 為 .env 並填入密鑰")
        return False

    try:
        async with AlpacaClient() as client:
            account = await client.get_account()

            if account:
                logger.info("✅ Alpaca連接成功!")
                logger.info(f"   賬戶ID: {account.get('id')}")
                logger.info(f"   現金: ${account.get('cash', 0):.2f}")
                logger.info(f"   淨值: ${account.get('portfolio_value', 0):.2f}")
                logger.info(f"   購買力: ${account.get('buying_power', 0):.2f}")
                logger.info(f"   槓桿: {account.get('multiplier')}x")
                return True
            else:
                logger.error("❌ 無法獲取賬戶信息")
                return False

    except Exception as e:
        logger.error(f"❌ 連接失敗: {e}")
        return False


async def test_data_fetching():
    """測試2: 數據獲取"""
    logger.info("\n" + "=" * 60)
    logger.info("測試2: 數據獲取")
    logger.info("=" * 60)

    try:
        async with AlpacaClient() as client:
            # 測試獲取多個符號的最新K線
            symbols = ["AAPL", "TSLA", "MSFT", "NVDA", "GOOGL"]
            logger.info(f"獲取 {symbols} 的最新K線...")

            bars = await client.get_latest_bars(symbols)

            if bars:
                logger.info(f"✅ 成功獲取 {len(bars)} 個K線")
                for symbol, bar in list(bars.items())[:3]:
                    logger.info(
                        f"   {symbol}: O={bar.open:.2f} H={bar.high:.2f} "
                        f"L={bar.low:.2f} C={bar.close:.2f} V={bar.volume:,}"
                    )
                return True
            else:
                logger.error("❌ 無法獲取K線數據")
                return False

    except Exception as e:
        logger.error(f"❌ 數據獲取失敗: {e}")
        return False


async def test_gap_detection():
    """測試3: Gap檢測"""
    logger.info("\n" + "=" * 60)
    logger.info("測試3: Gap檢測")
    logger.info("=" * 60)

    try:
        fetcher = DataFetcher()
        await fetcher.initialize()

        # 檢查市場狀態
        market_status = await fetcher.check_market_hours()
        logger.info(f"市場狀態: {market_status}")

        # 測試掃描
        test_symbols = ["AAPL", "TSLA", "MSFT", "NVDA", "GOOGL", "META", "AMZN", "AMD"]
        logger.info(f"掃描 {len(test_symbols)} 個符號尋找gap-up...")

        gapups = await fetcher.scan_gapups(test_symbols)

        if gapups:
            logger.info(f"✅ 找到 {len(gapups)} 個gap-up機會:")
            for gap in gapups[:5]:
                logger.info(
                    f"   {gap.symbol}: gap={gap.gap_pct:+.2f}% "
                    f"rel_vol={gap.rel_volume:.2f}x price=${gap.current_price:.2f}"
                )
            return True
        else:
            logger.info("ℹ️ 目前沒有找到符合條件的gap-up")
            return True

    except Exception as e:
        logger.error(f"❌ Gap檢測失敗: {e}")
        return False
    finally:
        await fetcher.close()


async def test_support_resistance():
    """測試4: 支撐位/阻力位識別"""
    logger.info("\n" + "=" * 60)
    logger.info("測試4: 支撐位/阻力位識別")
    logger.info("=" * 60)

    try:
        fetcher = DataFetcher()
        await fetcher.initialize()

        symbol = "AAPL"
        logger.info(f"分析 {symbol} 的支撐位和阻力位...")

        support, resistance = await fetcher.identify_support_resistance(symbol)

        if support or resistance:
            logger.info(f"✅ 識別完成:")
            if support:
                logger.info(f"   支撐位: {[f'${s:.2f}' for s in support]}")
            if resistance:
                logger.info(f"   阻力位: {[f'${r:.2f}' for r in resistance]}")
            return True
        else:
            logger.warning(f"⚠️ 無法識別支撐位/阻力位")
            return True

    except Exception as e:
        logger.error(f"❌ 支撐位/阻力位識別失敗: {e}")
        return False
    finally:
        await fetcher.close()


async def main():
    """運行所有測試"""
    logger.info("🚀 開始Alpaca整合測試")
    logger.info("=" * 60)

    results = []

    # 測試1: 連接
    results.append(("連接測試", await test_alpaca_connection()))

    # 測試2: 數據獲取
    results.append(("數據獲取", await test_data_fetching()))

    # 測試3: Gap檢測
    results.append(("Gap檢測", await test_gap_detection()))

    # 測試4: 支撐位/阻力位
    results.append(("支撐位/阻力位", await test_support_resistance()))

    # 總結
    logger.info("\n" + "=" * 60)
    logger.info("測試結果摘要")
    logger.info("=" * 60)

    for test_name, passed in results:
        status = "✅ 通過" if passed else "❌ 失敗"
        logger.info(f"{status} - {test_name}")

    all_passed = all(result[1] for result in results)

    if all_passed:
        logger.info("\n🎉 所有測試通過! Alpaca整合就緒")
        return 0
    else:
        logger.error("\n⚠️ 有些測試失敗，請檢查配置")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
