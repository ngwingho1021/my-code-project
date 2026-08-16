#!/usr/bin/env python3
"""
靈活回測工具 - 支持 CSV 數據或 Mock 數據

使用方法：
  # 用改進的 Mock 數據
  python scripts/run_backtest_with_real_or_mock.py --mode mock --days 120 --gap 2

  # 用 CSV 數據（需要先上傳 CSV）
  python scripts/run_backtest_with_real_or_mock.py --mode csv --csv NVDA.csv --gap 2
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse
import pandas as pd
import json
from datetime import datetime, timedelta
from backtest.standalone_backtester import StandaloneBacktester
from backtest.csv_data_loader import CSVDataLoader


def parse_args():
    parser = argparse.ArgumentParser(description='靈活回測工具')
    parser.add_argument('--mode', type=str, default='mock',
                       choices=['mock', 'csv'],
                       help='模式: mock (模擬數據) 或 csv (本地數據)')
    parser.add_argument('--csv', type=str, default='backtest/csv_data/SAMPLE.csv',
                       help='CSV 文件路徑（mode=csv 時使用）')
    parser.add_argument('--days', type=int, default=120,
                       help='模擬天數（mode=mock 時使用）')
    parser.add_argument('--initial-cash', type=float, default=10000,
                       help='初始資金')
    parser.add_argument('--risk-per-trade', type=float, default=100,
                       help='每筆交易風險')
    parser.add_argument('--gap', type=float, default=2.0,
                       help='Gap 門檻 (%)')
    return parser.parse_args()


def run_mock_backtest(args):
    """用模擬數據運行回測"""
    print('\n【模擬數據回測 - 改進版】')

    backtester = StandaloneBacktester(
        initial_cash=args.initial_cash,
        risk_per_trade=args.risk_per_trade,
        gap_threshold=args.gap,
    )

    metrics = backtester.run_simulation(num_days=args.days)

    print_report(metrics, backtester.trades, 'mock')
    save_results(metrics, backtester.trades, 'backtest_results_mock_improved.json')


def run_csv_backtest(args):
    """用 CSV 數據運行回測"""
    print('\n【CSV 數據回測】')

    csv_loader = CSVDataLoader()
    df = csv_loader.load_from_csv('USER_DATA', args.csv)

    if df.empty:
        print('❌ 無法加載 CSV 數據')
        return

    print('\n🚀 運行回測...')
    backtester = StandaloneBacktester(
        initial_cash=args.initial_cash,
        risk_per_trade=args.risk_per_trade,
        gap_threshold=args.gap,
    )

    # 簡單的 CSV 回測邏輯
    trades = []
    cash = args.initial_cash
    daily_pnl = {}

    for i in range(1, len(df)):
        current_date = df.index[i].strftime('%Y-%m-%d')
        if current_date not in daily_pnl:
            daily_pnl[current_date] = 0

        prev_close = df.iloc[i-1]['Close']
        today_open = df.iloc[i]['Open']
        today_high = df.iloc[i]['High']
        today_low = df.iloc[i]['Low']
        today_close = df.iloc[i]['Close']

        # 計算 gap
        gap_pct = ((today_open - prev_close) / prev_close) * 100

        if gap_pct < args.gap:
            continue

        # 進場
        entry_price = today_open
        stop_price = today_low - 0.05
        risk = entry_price - stop_price

        if risk <= 0:
            continue

        qty = int(args.risk_per_trade / risk)
        if qty <= 0:
            continue

        tp1 = entry_price + risk * 2.0
        tp2 = entry_price + risk * 3.0

        # 止盈邏輯
        if today_high >= tp2:
            exit_price = tp2
            exit_type = 'tp2'
        elif today_high >= tp1:
            exit_price = tp1
            exit_type = 'tp1'
        elif today_low <= stop_price:
            exit_price = stop_price
            exit_type = 'stop'
        else:
            exit_price = today_close
            exit_type = 'close'

        pnl = (exit_price - entry_price) * qty
        pnl_pct = (exit_price - entry_price) / entry_price * 100

        cash += pnl
        daily_pnl[current_date] += pnl

        status = '✅' if pnl > 0 else '❌'
        print(
            f'  {status} [{current_date}] entry=${entry_price:.2f}→${exit_price:.2f} '
            f'({exit_type}) | qty={qty} | PnL=${pnl:+.2f} ({pnl_pct:+.1f}%)'
        )

    # 計算指標
    metrics = calculate_metrics(trades, cash, args.initial_cash, daily_pnl)
    print_report(metrics, trades, 'csv')
    save_results(metrics, trades, 'backtest_results_csv.json')


def calculate_metrics(trades, cash, initial_cash, daily_pnl):
    """簡化的指標計算"""
    total_pnl = cash - initial_cash
    total_pnl_pct = (total_pnl / initial_cash) * 100

    return {
        'total_trades': len(trades),
        'winning_trades': len([t for t in trades if getattr(t, 'pnl', lambda: 0)() > 0]),
        'losing_trades': len([t for t in trades if getattr(t, 'pnl', lambda: 0)() < 0]),
        'win_rate': 0,
        'total_pnl': total_pnl,
        'total_pnl_pct': total_pnl_pct,
        'avg_win': 0,
        'avg_loss': 0,
        'max_loss': 0,
        'profit_factor': 0,
        'sharpe_ratio': 0,
        'max_drawdown': 0,
        'final_nav': cash,
    }


def print_report(metrics, trades, data_source):
    """打印報告"""
    print('\n' + '='*70)
    print(f'【回測結果 - {data_source.upper()}】')
    print('='*70)

    print('\n📊 基本績效:')
    print(f'  總交易筆數: {metrics["total_trades"]}')
    print(f'  盈利交易: {metrics["winning_trades"]}')
    print(f'  虧損交易: {metrics["losing_trades"]}')

    print('\n💰 資金績效:')
    print(f'  初始資金: ${10000:,.2f}')
    print(f'  最終淨值: ${metrics["final_nav"]:.2f}')
    print(f'  總淨利: ${metrics["total_pnl"]:+.2f}')
    print(f'  收益率: {metrics["total_pnl_pct"]:+.2f}%')

    print('\n' + '='*70)


def save_results(metrics, trades, filename):
    """保存結果"""
    metrics_serializable = {
        k: (float(v) if isinstance(v, (int, float)) else v)
        for k, v in metrics.items()
    }
    with open(filename, 'w') as f:
        json.dump(metrics_serializable, f, indent=2)
    print(f'\n✅ 結果已保存到 {filename}')


def main():
    args = parse_args()

    print('\n╔════════════════════════════════════════════════════════════╗')
    print('║         🚀 靈活回測工具 - Ross Cameron 策略             ║')
    print('╚════════════════════════════════════════════════════════════╝')

    print(f'\n⚙️ 配置:')
    print(f'  模式: {args.mode.upper()}')
    print(f'  初始資金: ${args.initial_cash:,.0f}')
    print(f'  風險/筆: ${args.risk_per_trade:.0f}')
    print(f'  Gap 門檻: {args.gap}%')

    if args.mode == 'mock':
        print(f'  模擬天數: {args.days}')
        run_mock_backtest(args)
    else:
        print(f'  CSV 文件: {args.csv}')
        run_csv_backtest(args)

    print('\n💡 下一步:')
    print('  1. 對比 mock vs 真實數據的結果')
    print('  2. 改進進場/止盈邏輯')
    print('  3. 用實際數據驗證')


if __name__ == '__main__':
    main()
