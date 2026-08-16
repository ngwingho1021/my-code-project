#!/usr/bin/env python3
"""
測試 IBKR 回測集成
驗證 IBKR 連接和歷史數據獲取功能
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.ibkr_client import IBKRClient
from config.settings import IB_HOST, IB_PORT, IB_CLIENT_ID


async def test_ibkr_connection():
    """測試 IBKR 連接"""
    print(f"\n{'='*80}")
    print("測試 1: IBKR 連接")
    print(f"{'='*80}")
    print(f"Host: {IB_HOST}")
    print(f"Port: {IB_PORT}")
    print(f"Client ID: {IB_CLIENT_ID}")
    print()

    try:
        client = IBKRClient()
        print("🔗 正在連接 IBKR...")
        client.connect()
        print("✅ IBKR 連接成功!")

        # 獲取管理帳戶
        print("\n📊 帳戶信息:")
        print(f"  連接狀態: {client.connected}")

        return client
    except Exception as e:
        print(f"❌ 連接失敗: {e}")
        print("\n💡 可能的原因:")
        print("  1. TWS/IB Gateway 未啟動")
        print("  2. API 未在 TWS 中啟用")
        print("  3. 端口設置不正確 (7497 for 紙交易, 7496 for 實盤)")
        print("  4. 防火牆阻止連接")
        return None


async def test_ibkr_historical_data(client: IBKRClient):
    """測試 IBKR 歷史數據獲取"""
    if not client:
        return

    print(f"\n{'='*80}")
    print("測試 2: IBKR 歷史數據獲取")
    print(f"{'='*80}\n")

    # 測試用的股票和日期範圍
    test_cases = [
        {
            "symbol": "SPY",
            "start_date": (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"),
            "end_date": datetime.now().strftime("%Y-%m-%d"),
            "timeframe": "1 Min",
            "description": "SPY - 過去30天 - 1分鐘K線"
        },
        {
            "symbol": "AAPL",
            "start_date": (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d"),
            "end_date": datetime.now().strftime("%Y-%m-%d"),
            "timeframe": "1 Min",
            "description": "AAPL - 過去5天 - 1分鐘K線"
        }
    ]

    for test_case in test_cases:
        print(f"測試: {test_case['description']}")
        print(f"  符號: {test_case['symbol']}")
        print(f"  日期: {test_case['start_date']} 至 {test_case['end_date']}")
        print(f"  周期: {test_case['timeframe']}")
        print()

        try:
            df = client.get_historical_bars(
                symbol=test_case['symbol'],
                start_date=test_case['start_date'],
                end_date=test_case['end_date'],
                timeframe=test_case['timeframe']
            )

            if df is not None and not df.empty:
                print(f"✅ 成功獲取 {len(df)} 根K線")
                print(f"   時間範圍: {df.index[0]} 至 {df.index[-1]}")
                print(f"   列: {list(df.columns)}")
                print(f"   樣本數據:\n{df.head(3)}\n")
            else:
                print("⚠️  無數據或數據為空\n")

        except Exception as e:
            print(f"❌ 錯誤: {e}\n")


async def test_ibkr_contract_qualification(client: IBKRClient):
    """測試合約確認"""
    if not client:
        return

    print(f"\n{'='*80}")
    print("測試 3: 合約確認")
    print(f"{'='*80}\n")

    symbols = ["AAPL", "TSLA", "MSFT"]

    for symbol in symbols:
        try:
            print(f"正在確認 {symbol}...", end=" ")
            contract = client.make_stock(symbol)
            qualified = client.qualify(contract)
            print(f"✅ 成功 (合約ID: {qualified.conId})")
        except Exception as e:
            print(f"❌ 失敗: {e}")


async def main():
    """主測試函數"""
    print(f"\n\n{'='*80}")
    print("IBKR 回測集成測試套件")
    print(f"{'='*80}\n")
    print("此測試驗證以下功能:")
    print("  1. IBKR 連接")
    print("  2. 歷史數據獲取")
    print("  3. 合約確認")
    print()

    # 測試1: 連接
    client = await test_ibkr_connection()

    if client:
        # 測試2: 歷史數據
        await test_ibkr_historical_data(client)

        # 測試3: 合約確認
        await test_ibkr_contract_qualification(client)

        # 斷開連接
        print(f"\n{'='*80}")
        print("清理資源")
        print(f"{'='*80}\n")
        try:
            client.disconnect()
            print("✅ 已斷開 IBKR 連接")
        except Exception as e:
            print(f"⚠️  斷開連接時出錯: {e}")

    print(f"\n{'='*80}")
    print("測試完成")
    print(f"{'='*80}\n")
    print("✨ 如果所有測試都通過，可以使用以下命令進行回測:")
    print()
    print("  python backtest_runner.py \\")
    print("    --symbol SPY \\")
    print("    --start 2024-01-01 \\")
    print("    --end 2024-06-30 \\")
    print("    --data-source ibkr")
    print()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⏹️  測試被用户中斷")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 致命錯誤: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
