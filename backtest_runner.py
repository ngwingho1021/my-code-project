#!/usr/bin/env python3
"""
回測運行器 - 從命令行執行回測

Usage:
    python backtest_runner.py --symbol AAPL --start 2024-01-01 --end 2024-12-31
    python backtest_runner.py --symbol SPY --start 2024-06-01 --end 2024-06-30 --timeframe 5Min
"""

import asyncio
import argparse
from datetime import datetime
from pathlib import Path
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backtest.backtester import Backtester
from backtest.analyzer import BacktestAnalyzer
from strategy.gap_momentum_strategy import GapMomentumStrategy, create_backtest_signal_function


async def main():
    parser = argparse.ArgumentParser(
        description="盤前Gap動量交易系統 - 回測工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
範例:
  # 回測單個股票
  python backtest_runner.py --symbol AAPL --start 2024-01-01 --end 2024-12-31

  # 使用自定義時間框架
  python backtest_runner.py --symbol TSLA --start 2024-06-01 --end 2024-06-30 --timeframe 5Min

  # 使用自定義初始資本
  python backtest_runner.py --symbol SPY --start 2024-01-01 --end 2024-03-31 --capital 50000
        """
    )

    parser.add_argument('--symbol', type=str, required=True, help='股票代碼 (e.g., AAPL, SPY)')
    parser.add_argument('--start', type=str, required=True, help='開始日期 (YYYY-MM-DD)')
    parser.add_argument('--end', type=str, required=True, help='結束日期 (YYYY-MM-DD)')
    parser.add_argument('--timeframe', type=str, default='1Min', help='時間框架 (預設: 1Min)')
    parser.add_argument('--capital', type=float, default=25000.0, help='初始資本 (預設: 25000)')
    parser.add_argument('--slippage', type=float, default=0.5, help='滑點百分比 (預設: 0.5 百分點)')
    parser.add_argument('--output', type=str, default='backtest_reports', help='報告輸出目錄')

    args = parser.parse_args()

    # 驗證日期格式
    try:
        start_date = datetime.strptime(args.start, '%Y-%m-%d')
        end_date = datetime.strptime(args.end, '%Y-%m-%d')
        if start_date >= end_date:
            print("❌ 錯誤: 開始日期必須早於結束日期")
            sys.exit(1)
    except ValueError as e:
        print(f"❌ 日期格式錯誤: {e}")
        sys.exit(1)

    print(f"\n{'='*80}")
    print(f"🚀 盤前Gap動量交易系統 - 回測模式")
    print(f"{'='*80}")
    print(f"股票代碼: {args.symbol}")
    print(f"回測期間: {args.start} 至 {args.end}")
    print(f"時間框架: {args.timeframe}")
    print(f"初始資本: ${args.capital:,.2f}")
    print(f"滑點設定: {args.slippage}%")
    print(f"{'='*80}\n")

    # 創建回測器
    backtester = Backtester(initial_capital=args.capital, slippage_pct=args.slippage)

    # 創建策略
    strategy = GapMomentumStrategy()
    signal_func = create_backtest_signal_function(strategy)

    # 運行回測
    try:
        result = backtester.run(
            symbol=args.symbol,
            start_date=args.start,
            end_date=args.end,
            signal_func=signal_func
        )

        if 'error' in result:
            print(f"\n❌ 回測失敗: {result['error']}")
            sys.exit(1)

        # 生成報告
        print(f"\n{'='*80}")
        print("📊 生成報告...")
        print(f"{'='*80}\n")

        analyzer = BacktestAnalyzer(report_dir=args.output)

        # HTML報告
        html_path = analyzer.generate_html_report(
            result,
            args.symbol,
            args.start,
            args.end
        )

        # JSON報告
        json_path = analyzer.generate_json_report(result, args.symbol)

        # 打印摘要
        print_summary(result)

        print(f"\n{'='*80}")
        print("✅ 回測完成!")
        print(f"{'='*80}")
        print(f"📄 HTML報告: {html_path}")
        print(f"📄 JSON數據: {json_path}")
        print()

    except Exception as e:
        print(f"\n❌ 回測出錯: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def print_summary(result: dict):
    """打印回測摘要"""
    summary = result.get('summary', {})
    stats = result.get('trading_stats', {})

    print(f"\n📈 總體績效")
    print(f"  初始資本:     ${summary.get('initial_capital', 0):>12,.2f}")
    print(f"  最終淨值:     ${summary.get('final_equity', 0):>12,.2f}")
    print(f"  淨收益:       ${summary.get('total_return', 0):>12,.2f}")
    print(f"  回報率:       {summary.get('total_return_pct', 0):>12.2f}%")
    print(f"  最大回撤:     {summary.get('max_drawdown_pct', 0):>12.2f}%")

    print(f"\n📊 交易統計")
    print(f"  總交易數:     {stats.get('total_trades', 0):>12}")
    print(f"  勝利交易:     {stats.get('winning_trades', 0):>12}")
    print(f"  失敗交易:     {stats.get('losing_trades', 0):>12}")
    print(f"  勝率:         {stats.get('win_rate', 0):>12.1f}%")
    print(f"  平均盈利:     ${stats.get('total_profit', 0):>12,.2f}")
    print(f"  平均虧損:     ${stats.get('total_loss', 0):>12,.2f}")
    print(f"  單筆平均損益: ${stats.get('avg_trade_pnl', 0):>12,.2f}")
    print(f"  最大單筆盈利: ${stats.get('largest_win', 0):>12,.2f}")
    print(f"  最大單筆虧損: ${stats.get('largest_loss', 0):>12,.2f}")
    print(f"  平均持倉時間: {stats.get('avg_holding_time_minutes', 0):>12} 分鐘")


if __name__ == '__main__':
    asyncio.run(main())
