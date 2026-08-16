#!/usr/bin/env python3
"""
真實數據回測 — 用 yfinance 歷史數據驗證策略

使用方法：
  python scripts/run_real_data_backtest.py --start 2024-06-01 --end 2024-08-31
  python scripts/run_real_data_backtest.py --start 2024-01-01 --end 2024-12-31 --symbols "NVDA,AMD,TSLA"
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse
import pandas as pd
from datetime import datetime, timedelta
from backtest.data_loader import DataLoader
from backtest.simple_backtester import SimpleBacktester
import json


def parse_args():
    parser = argparse.ArgumentParser(description='用真實數據回測 Ross Cameron 策略')
    parser.add_argument('--start', type=str, default='2024-06-01',
                       help='開始日期 (YYYY-MM-DD)')
    parser.add_argument('--end', type=str, default='2024-08-31',
                       help='結束日期 (YYYY-MM-DD)')
    parser.add_argument('--symbols', type=str, default='NVDA,AMD,TSLA,PLTR,AAPL,MSFT',
                       help='股票代碼 (逗號分隔)')
    parser.add_argument('--initial-cash', type=float, default=10000,
                       help='初始資金 (USD)')
    parser.add_argument('--risk-per-trade', type=float, default=100,
                       help='每筆交易風險 (USD)')
    parser.add_argument('--gap-threshold', type=float, default=2.0,
                       help='Gap Up 門檻 (%)')
    parser.add_argument('--float-max', type=float, default=30e6,
                       help='最大流通股 (shares)')
    parser.add_argument('--rvol-min', type=float, default=5.0,
                       help='最小相對成交量 (x)')
    return parser.parse_args()


def get_trading_dates(start_str: str, end_str: str) -> list:
    """生成交易日期列表（排除週末）"""
    start = pd.to_datetime(start_str)
    end = pd.to_datetime(end_str)
    dates = pd.bdate_range(start=start, end=end)
    return [d.strftime('%Y-%m-%d') for d in dates]


def find_gap_up_stocks(symbol: str,
                       data_loader: DataLoader,
                       all_dates: list,
                       gap_threshold: float = 2.0) -> dict:
    """
    找出每天的 Gap Up 股票

    Returns:
        {日期: [股票列表]}
    """
    print(f'\n📊 分析 {symbol}...')

    # 下載該股票的完整數據
    start_date = all_dates[0] if all_dates else '2024-01-01'
    end_date = all_dates[-1] if all_dates else '2024-12-31'

    df = data_loader.get_daily_bars(symbol, start_date, end_date)
    if df.empty:
        print(f'  ⚠️ {symbol} 無數據')
        return {}

    results = {}

    for i in range(1, len(df)):
        current_date = df.index[i].strftime('%Y-%m-%d')

        # 檢查是否在交易日期列表中
        if current_date not in all_dates:
            continue

        prev_close = df.iloc[i-1]['Close']
        curr_open = df.iloc[i]['Open']

        # 計算 gap 百分比
        gap_pct = ((curr_open - prev_close) / prev_close) * 100

        if gap_pct >= gap_threshold:
            if current_date not in results:
                results[current_date] = []
            results[current_date].append(symbol)
            print(f'  ✅ [{current_date}] {symbol}: Gap +{gap_pct:.1f}%')

    return results


def merge_gap_results(all_gap_results: list) -> dict:
    """合併多個股票的 gap 結果"""
    merged = {}
    for results in all_gap_results:
        for date, symbols in results.items():
            if date not in merged:
                merged[date] = []
            merged[date].extend(symbols)
    return merged


def print_report(metrics: dict, trades: list):
    """打印績效報告"""
    print('\n' + '=' * 70)
    print('【真實數據回測結果】')
    print('=' * 70)

    # 基本績效
    print('\n📊 基本績效:')
    print(f'  總交易筆數: {metrics["total_trades"]}')
    print(f'  盈利交易: {metrics["winning_trades"]}')
    print(f'  虧損交易: {metrics["losing_trades"]}')
    print(f'  勝率: {metrics["win_rate"]:.1f}%')

    print('\n💰 資金績效:')
    print(f'  初始資金: ${metrics["initial_cash"]:,.2f}')
    print(f'  最終淨值: ${metrics["final_nav"]:.2f}')
    print(f'  總淨利: ${metrics["total_pnl"]:+.2f}')
    print(f'  收益率: {metrics["total_pnl_pct"]:+.2f}%')

    print('\n📈 交易統計:')
    print(f'  平均盈利: ${metrics["avg_win"]:.2f}')
    print(f'  平均虧損: ${metrics["avg_loss"]:.2f}')
    print(f'  最大虧損: ${metrics["max_loss"]:.2f}')
    if metrics["profit_factor"] != float('inf') and metrics["profit_factor"] != 0:
        print(f'  利潤因子: {metrics["profit_factor"]:.2f}')
    else:
        print(f'  利潤因子: {"∞ (無虧損)" if metrics["losing_trades"] == 0 else "N/A"}')

    print('\n⚠️ 風控指標:')
    print(f'  最大回撤: {metrics["max_drawdown"]:.2f}%')
    print(f'  Sharpe 比率: {metrics["sharpe_ratio"]:.2f}')

    # 交易明細
    if trades:
        print('\n📋 交易明細 (所有交易):')
        for i, trade in enumerate(trades, 1):
            pnl = trade.pnl()
            pnl_pct = trade.pnl_pct()
            status = '✅' if pnl > 0 else '❌'
            print(
                f'  {status} {i:2}. {trade.symbol} @ {trade.entry_date.strftime("%Y-%m-%d")} '
                f'entry=${trade.entry_price:.2f} exit=${trade.exit_price:.2f} '
                f'qty={trade.quantity} '
                f'${pnl:+7.2f} ({pnl_pct:+6.1f}%) '
                f'[{trade.exit_type}]'
            )

    print('\n' + '=' * 70)

    # 評估
    print('\n📊 策略評估:')
    if metrics['total_trades'] == 0:
        print('  ⚠️ 無交易生成（可能 gap 條件太嚴格或數據不足）')
    elif metrics['win_rate'] > 55 and metrics['profit_factor'] > 2.0:
        print('  ✅ 表現很好！')
    elif metrics['win_rate'] > 50 and metrics['profit_factor'] > 1.5:
        print('  🟡 表現還可以')
    elif metrics['win_rate'] > 0 and metrics['total_pnl'] > 0:
        print('  🟡 有盈利但穩定性需改進')
    else:
        print('  ❌ 表現不理想，需要調整')


def main():
    args = parse_args()

    print('\n╔════════════════════════════════════════════════════════════╗')
    print('║           🚀 真實數據回測 — Ross Cameron 策略             ║')
    print('║            (使用 yfinance 歷史數據)                        ║')
    print('╚════════════════════════════════════════════════════════════╝')

    print(f'\n⚙️ 回測配置:')
    print(f'  期間: {args.start} ~ {args.end}')
    print(f'  股票: {args.symbols}')
    print(f'  初始資金: ${args.initial_cash:,.0f}')
    print(f'  風險/筆: ${args.risk_per_trade:.0f}')
    print(f'  Gap 門檻: {args.gap_threshold}%')

    # 初始化
    data_loader = DataLoader()
    symbols = [s.strip().upper() for s in args.symbols.split(',')]

    # 生成交易日期
    print('\n⏳ 生成交易日期...')
    all_dates = get_trading_dates(args.start, args.end)
    print(f'  共 {len(all_dates)} 個交易日')

    # 找出每日的 Gap Up 股票
    print('\n🔍 掃描 Gap Up 股票...')
    all_gap_results = []
    for symbol in symbols:
        results = find_gap_up_stocks(symbol, data_loader, all_dates, args.gap_threshold)
        all_gap_results.append(results)

    symbols_by_date = merge_gap_results(all_gap_results)
    print(f'\n✅ 找到 {len(symbols_by_date)} 個交易日有候選股')

    if not symbols_by_date:
        print('⚠️ 無法找到符合條件的股票，可能需要調整參數')
        return

    # 運行回測
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
    result_file = 'backtest_results_real_data.json'
    with open(result_file, 'w') as f:
        metrics_serializable = {
            k: (float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else v)
            for k, v in metrics.items()
        }
        json.dump(metrics_serializable, f, indent=2)
    print(f'\n✅ 結果已保存到 {result_file}')

    # 對比分析建議
    print('\n💡 對比分析:')
    print('  真實數據 vs Mock 數據:')
    print('  1. 比較勝率、利潤因子、最大回撤')
    print('  2. 分析差異原因（滑價、流動性、極端波動）')
    print('  3. 評估是否需要調整進場/止盈邏輯')


if __name__ == '__main__':
    main()
