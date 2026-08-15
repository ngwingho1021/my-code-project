#!/usr/bin/env python3
"""
簡單 Backtest 運行器 — POC 版本

使用方法：
  python scripts/run_backtest_simple.py --start 2024-01-01 --end 2024-08-15
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse
import pandas as pd
import json
from datetime import datetime, timedelta
from backtest.data_loader import DataLoader
from backtest.simple_backtester import SimpleBacktester


def parse_args():
    parser = argparse.ArgumentParser(description='Ross Cameron 策略 Backtest')
    parser.add_argument('--start', type=str, default='2024-01-01',
                       help='開始日期 (YYYY-MM-DD)')
    parser.add_argument('--end', type=str, default='2024-08-15',
                       help='結束日期 (YYYY-MM-DD)')
    parser.add_argument('--initial-cash', type=float, default=10000,
                       help='初始資金 (USD)')
    parser.add_argument('--risk-per-trade', type=float, default=100,
                       help='每筆交易風險 (USD)')
    parser.add_argument('--gap-threshold', type=float, default=20.0,
                       help='Gap Up 門檻 (%)')
    parser.add_argument('--float-max', type=float, default=30e6,
                       help='最大流通股 (shares)')
    parser.add_argument('--rvol-min', type=float, default=5.0,
                       help='最小相對成交量 (x)')
    return parser.parse_args()


def get_trading_dates(start_str: str, end_str: str) -> list:
    """
    生成交易日期列表（排除週末）
    """
    start = pd.to_datetime(start_str)
    end = pd.to_datetime(end_str)

    # 簡單邏輯：生成所有工作日（排除週末）
    # 注：實際交易日還應排除節假日，但這裡簡化處理
    dates = pd.bdate_range(start=start, end=end)
    return [d.strftime('%Y-%m-%d') for d in dates]


def generate_mock_candidates(data_loader: DataLoader,
                             all_dates: list,
                             gap_threshold: float = 20.0) -> dict:
    """
    簡單版本：根據歷史數據生成候選股票
    （實際應連接 IBKR 掃描器）

    這裡用簡化邏輯：隨機選一些股票進行回測
    """
    # 測試用的股票列表（美股爆升股示例）
    # 注：這些股票在實盤應從 IBKR 掃描器獲取
    test_symbols = ['AAPL', 'TSLA', 'NVDA', 'AMD', 'MSFT', 'GOOGL']

    symbols_by_date = {}

    for i, date_str in enumerate(all_dates):
        date = pd.to_datetime(date_str)

        # 簡化邏輯：每隔3個工作日選1-2隻股票
        if i % 3 == 0:
            # 輪流選股票
            idx = (i // 3) % len(test_symbols)
            symbols_by_date[date_str] = [test_symbols[idx]]
            if idx + 1 < len(test_symbols):
                symbols_by_date[date_str].append(test_symbols[idx + 1])

    return symbols_by_date


def print_report(metrics: dict, trades: list):
    """打印績效報告"""
    print('\n' + '=' * 60)
    print('【回測結果】')
    print('=' * 60)

    # 基本績效
    print('\n📊 基本績效:')
    print(f'  總交易筆數: {metrics["total_trades"]}')
    print(f'  盈利交易: {metrics["winning_trades"]}')
    print(f'  虧損交易: {metrics["losing_trades"]}')
    print(f'  勝率: {metrics["win_rate"]:.1f}%')

    print('\n💰 資金績效:')
    print(f'  總淨利: ${metrics["total_pnl"]:.2f}')
    print(f'  收益率: {metrics["total_pnl_pct"]:+.1f}%')
    print(f'  最終淨值: ${metrics["final_nav"]:.2f}')

    print('\n📈 交易統計:')
    print(f'  平均盈利: ${metrics["avg_win"]:.2f}')
    print(f'  平均虧損: ${metrics["avg_loss"]:.2f}')
    print(f'  最大虧損: ${metrics["max_loss"]:.2f}')
    print(f'  利潤因子: {metrics["profit_factor"]:.2f}')

    print('\n⚠️ 風控指標:')
    print(f'  最大回撤: {metrics["max_drawdown"]:.2f}%')
    print(f'  Sharpe 比率: {metrics["sharpe_ratio"]:.2f}')

    if trades:
        print('\n📋 交易明細 (前10筆):')
        for i, trade in enumerate(trades[:10], 1):
            pnl = trade.pnl()
            pnl_pct = trade.pnl_pct()
            print(
                f'  {i:2}. {trade.symbol} '
                f'entry=${trade.entry_price:.2f} exit=${trade.exit_price:.2f} '
                f'qty={trade.quantity} '
                f'${pnl:+7.2f} ({pnl_pct:+6.1f}%) '
                f'[{trade.exit_type}]'
            )

    print('\n' + '=' * 60)


def main():
    args = parse_args()

    print('\n【簡單 Backtest POC】')
    print(f'  期間: {args.start} ~ {args.end}')
    print(f'  初始資金: ${args.initial_cash:,.0f}')
    print(f'  風險/筆: ${args.risk_per_trade:.0f}')

    # 初始化
    data_loader = DataLoader()

    # 生成交易日期
    print('\n⏳ 生成交易日期...')
    all_dates = get_trading_dates(args.start, args.end)
    print(f'  共 {len(all_dates)} 個交易日')

    # 生成候選股票
    print('📊 生成候選股票...')
    symbols_by_date = generate_mock_candidates(
        data_loader, all_dates,
        gap_threshold=args.gap_threshold
    )
    print(f'  共 {len(symbols_by_date)} 個交易日有候選股')

    # 運行 Backtest
    print('\n🚀 運行回測...')
    backtester = SimpleBacktester(
        initial_cash=args.initial_cash,
        risk_per_trade=args.risk_per_trade,
        gap_threshold=args.gap_threshold,
        float_max=args.float_max,
        rvol_min=args.rvol_min,
    )

    metrics = backtester.run(symbols_by_date, data_loader, all_dates)

    # 打印報告
    print_report(metrics, backtester.trades)

    # 保存結果
    result_file = 'backtest_results.json'
    with open(result_file, 'w') as f:
        # 轉換為可 JSON 序列化的格式
        metrics_serializable = {
            k: (float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else v)
            for k, v in metrics.items()
        }
        json.dump(metrics_serializable, f, indent=2)
    print(f'\n✅ 結果已保存到 {result_file}')


if __name__ == '__main__':
    main()
