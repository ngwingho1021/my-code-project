#!/usr/bin/env python3
"""
獨立版 Backtest 運行器 — 使用模擬數據，無需網絡連接

使用方法：
  python scripts/run_standalone_backtest.py
  python scripts/run_standalone_backtest.py --days 90 --risk-per-trade 150
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse
from backtest.standalone_backtester import StandaloneBacktester


def print_report(metrics, trades):
    """打印績效報告"""
    print('\n' + '=' * 70)
    print('【回測結果】')
    print('=' * 70)

    # 基本績效
    print('\n📊 基本績效:')
    print(f'  總交易筆數: {metrics["total_trades"]}')
    print(f'  盈利交易: {metrics["winning_trades"]}')
    print(f'  虧損交易: {metrics["losing_trades"]}')
    print(f'  勝率: {metrics["win_rate"]:.1f}%')

    print('\n💰 資金績效:')
    print(f'  初始資金: $10,000.00')
    print(f'  最終淨值: ${metrics["final_nav"]:.2f}')
    print(f'  總淨利: ${metrics["total_pnl"]:.2f}')
    print(f'  收益率: {metrics["total_pnl_pct"]:+.1f}%')

    print('\n📈 交易統計:')
    print(f'  平均盈利: ${metrics["avg_win"]:.2f}')
    print(f'  平均虧損: ${metrics["avg_loss"]:.2f}')
    print(f'  最大虧損: ${metrics["max_loss"]:.2f}')
    if metrics["profit_factor"] != float('inf'):
        print(f'  利潤因子: {metrics["profit_factor"]:.2f}')
    else:
        print(f'  利潤因子: ∞ (無虧損交易)')

    print('\n⚠️ 風控指標:')
    print(f'  最大回撤: {metrics["max_drawdown"]:.2f}%')
    print(f'  Sharpe 比率: {metrics["sharpe_ratio"]:.2f}')

    # 交易明細
    if trades:
        print('\n📋 交易明細 (所有交易):')
        for i, trade in enumerate(trades, 1):
            pnl = trade.pnl()
            pnl_pct = trade.pnl_pct()
            print(
                f'  {i:2}. {trade.symbol} @ {trade.entry_date} '
                f'entry=${trade.entry_price:.2f} exit=${trade.exit_price:.2f} '
                f'qty={trade.quantity} '
                f'${pnl:+7.2f} ({pnl_pct:+6.1f}%) '
                f'[{trade.exit_type}]'
            )

    print('\n' + '=' * 70)

    # 判斷
    print('\n📊 策略評估:')
    if metrics['win_rate'] > 55 and metrics['profit_factor'] > 2.0:
        print('  ✅ 很有潛力！建議進行下一階段測試')
    elif metrics['win_rate'] > 50 and metrics['profit_factor'] > 1.5:
        print('  🟡 還不錯，可嘗試調優參數')
    elif metrics['win_rate'] > 0 and metrics['total_pnl'] > 0:
        print('  🟡 有盈利但穩定性待改進')
    else:
        print('  ❌ 需要重新評估策略或參數')


def main():
    parser = argparse.ArgumentParser(
        description='獨立版 Backtest — 模擬數據，無需網絡'
    )
    parser.add_argument('--days', type=int, default=60,
                       help='模擬交易天數 (預設: 60)')
    parser.add_argument('--initial-cash', type=float, default=10000,
                       help='初始資金 USD (預設: 10000)')
    parser.add_argument('--risk-per-trade', type=float, default=100,
                       help='每筆交易風險 USD (預設: 100)')
    parser.add_argument('--gap-threshold', type=float, default=20.0,
                       help='Gap Up 門檻 % (預設: 20.0)')
    parser.add_argument('--float-max', type=float, default=30e6,
                       help='最大流通股 (預設: 30e6)')
    parser.add_argument('--rvol-min', type=float, default=5.0,
                       help='最小 RVol 倍數 (預設: 5.0)')

    args = parser.parse_args()

    print('\n╔════════════════════════════════════════════════════════════╗')
    print('║        🚀 獨立版 Backtest — Ross Cameron 策略             ║')
    print('║            (模擬數據，無需網絡連接)                        ║')
    print('╚════════════════════════════════════════════════════════════╝')

    print(f'\n⚙️ 回測配置:')
    print(f'  模擬天數: {args.days}')
    print(f'  初始資金: ${args.initial_cash:,.0f}')
    print(f'  風險/筆: ${args.risk_per_trade:.0f}')

    # 運行回測
    backtester = StandaloneBacktester(
        initial_cash=args.initial_cash,
        risk_per_trade=args.risk_per_trade,
        gap_threshold=args.gap_threshold,
        float_max=args.float_max,
        rvol_min=args.rvol_min,
    )

    metrics = backtester.run_simulation(num_days=args.days)

    # 打印報告
    print_report(metrics, backtester.trades)

    print('\n💡 提示:')
    print('  想調整參數？試試這些命令：')
    print('  • python scripts/run_standalone_backtest.py --gap-threshold 15')
    print('  • python scripts/run_standalone_backtest.py --risk-per-trade 150')
    print('  • python scripts/run_standalone_backtest.py --days 120')
    print('\n  想了解詳情？閱讀 backtest/README.md')


if __name__ == '__main__':
    main()
