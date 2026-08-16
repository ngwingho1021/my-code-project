#!/usr/bin/env python3
"""
快速回测工具 - Windows 专用版本
直接运行：python backtest_real_data.py

用途：
1. 用 CSV 数据运行回测
2. 对比 Mock vs 真实数据
3. 帮助决策下一步
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import numpy as np
from datetime import datetime
from backtest.standalone_backtester import StandaloneBacktester
from backtest.csv_data_loader import CSVDataLoader
import json


def run_mock_backtest(days=120, gap_threshold=2.0, risk_per_trade=100):
    """运行 Mock 回测"""
    print('\n【Mock 数据回测】')
    print(f'  天数: {days}')
    print(f'  Gap 门槛: {gap_threshold}%')
    print(f'  风险: ${risk_per_trade}')
    print('\n开始模拟...\n')

    backtester = StandaloneBacktester(
        initial_cash=10000,
        risk_per_trade=risk_per_trade,
        gap_threshold=gap_threshold,
    )

    metrics = backtester.run_simulation(num_days=days)

    print('\n' + '='*70)
    print('【Mock 回测结果】')
    print('='*70)
    print(f'交易笔数: {metrics["total_trades"]}')
    print(f'勝率: {metrics["win_rate"]:.1f}%')
    print(f'利潤因子: {metrics["profit_factor"]:.2f}')
    print(f'淨利: ${metrics["total_pnl"]:+.2f}')
    print(f'回报率: {metrics["total_pnl_pct"]:+.2f}%')
    print('='*70)

    return metrics


def run_csv_backtest(csv_file, gap_threshold=2.0, risk_per_trade=100):
    """运行 CSV 数据回测"""
    print(f'\n【CSV 数据回测】')
    print(f'  文件: {csv_file}')
    print(f'  Gap 门槛: {gap_threshold}%')
    print(f'  风险: ${risk_per_trade}')

    csv_loader = CSVDataLoader()
    df = csv_loader.load_from_csv('USER_DATA', csv_file)

    if df.empty:
        print('❌ 无法加载 CSV 文件')
        return None

    print(f'\n数据范围: {df.index[0].date()} ~ {df.index[-1].date()}')
    print('开始回测...\n')

    # 简单回测逻辑
    trades = []
    cash = 10000
    initial_cash = 10000

    for i in range(1, len(df)):
        prev_close = df.iloc[i-1]['Close']
        today_open = df.iloc[i]['Open']
        today_high = df.iloc[i]['High']
        today_low = df.iloc[i]['Low']
        today_close = df.iloc[i]['Close']
        today_date = df.index[i].strftime('%Y-%m-%d')

        # 计算 gap
        gap_pct = ((today_open - prev_close) / prev_close) * 100

        if gap_pct < gap_threshold:
            continue

        # 进场
        entry_price = today_open
        stop_price = today_low - 0.05
        risk = entry_price - stop_price

        if risk <= 0:
            continue

        qty = int(risk_per_trade / risk)
        if qty <= 0:
            continue

        tp1 = entry_price + risk * 2.0
        tp2 = entry_price + risk * 3.0

        # 止盈逻辑
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
        cash += pnl

        status = '✅' if pnl > 0 else '❌'
        print(f'  {status} [{today_date}] ${entry_price:.2f}→${exit_price:.2f} ({exit_type}) | qty={qty} | PnL=${pnl:+.2f}')

        trades.append({
            'date': today_date,
            'entry': entry_price,
            'exit': exit_price,
            'pnl': pnl,
            'type': exit_type
        })

    # 计算指标
    if not trades:
        print('❌ 无交易生成')
        return None

    wins = [t for t in trades if t['pnl'] > 0]
    losses = [t for t in trades if t['pnl'] < 0]

    total_pnl = sum(t['pnl'] for t in trades)
    total_pnl_pct = (total_pnl / initial_cash) * 100

    print('\n' + '='*70)
    print('【CSV 回测结果】')
    print('='*70)
    print(f'交易笔数: {len(trades)}')
    print(f'勝率: {len(wins)/len(trades)*100:.1f}%')
    print(f'利潤因子: {sum(t["pnl"] for t in wins)/abs(sum(t["pnl"] for t in losses)):.2f}' if losses else '∞')
    print(f'淨利: ${total_pnl:+.2f}')
    print(f'回报率: {total_pnl_pct:+.2f}%')
    print('='*70)

    return {
        'trades': len(trades),
        'win_rate': len(wins)/len(trades)*100,
        'pnl': total_pnl,
        'pnl_pct': total_pnl_pct,
    }


def main():
    """主程序"""
    print('\n╔════════════════════════════════════════════════════════════╗')
    print('║           🔄 Mock vs CSV 真实数据对比回测             ║')
    print('╚════════════════════════════════════════════════════════════╝')

    # 参数
    days = 120
    gap = 2.0
    risk = 100

    # 运行 Mock 回测
    mock_result = run_mock_backtest(days=days, gap_threshold=gap, risk_per_trade=risk)

    # 检查 CSV 文件
    csv_files = []
    if os.path.exists('backtest/csv_data'):
        csv_files = [f for f in os.listdir('backtest/csv_data') if f.endswith('.csv')]

    if not csv_files:
        print('\n❌ 未找到 CSV 文件，请先运行：')
        print('python -c "import yfinance as yf; import os; os.makedirs(\'backtest\\\\csv_data\', exist_ok=True); [yf.download(s, start=\'2024-01-01\', end=\'2024-08-31\').to_csv(f\'backtest\\\\csv_data\\\\{s}.csv\') or print(f\'✅ {s}\') for s in [\'NVDA\',\'AMD\',\'TSLA\',\'PLTR\']]"')
        sys.exit(1)

    print(f'\n找到 {len(csv_files)} 个 CSV 文件')

    # 运行 CSV 回测（第一个文件）
    csv_file = f'backtest/csv_data/{csv_files[0]}'
    csv_result = run_csv_backtest(csv_file, gap_threshold=gap, risk_per_trade=risk)

    # 对比
    if csv_result:
        print('\n' + '='*70)
        print('【Mock vs CSV 对比】')
        print('='*70)
        print(f'勝率: {mock_result["win_rate"]:.1f}% (Mock) vs {csv_result["win_rate"]:.1f}% (CSV)')
        print(f'淨利: ${mock_result["total_pnl"]:+.2f} (Mock) vs ${csv_result["pnl"]:+.2f} (CSV)')
        print(f'回报: {mock_result["total_pnl_pct"]:+.2f}% (Mock) vs {csv_result["pnl_pct"]:+.2f}% (CSV)')
        print('='*70)

        # 建议
        print('\n💡 建议:')
        if csv_result['win_rate'] > 35:
            print('  ✅ CSV 胜率 > 35%，策略有潜力！')
            print('  下一步：进行纸上交易验证')
        elif csv_result['win_rate'] > 25:
            print('  🟡 CSV 胜率 25-35%，需要参数调整')
            print('  下一步：调整 gap/risk 参数重新测试')
        else:
            print('  ❌ CSV 胜率 < 25%，策略需要改进')
            print('  下一步：考虑架构改进或其他策略')

        # 试试其他股票
        if len(csv_files) > 1:
            print(f'\n📊 可以试试其他股票：{", ".join([f[:-4] for f in csv_files[1:]])}')
            print('运行类似命令测试其他股票...')

    print('\n' + '='*70)


if __name__ == '__main__':
    main()
