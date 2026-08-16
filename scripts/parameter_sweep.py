#!/usr/bin/env python3
"""
參數掃描工具 - 幫助找到最優參數組合
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backtest.standalone_backtester import StandaloneBacktester
import json
from datetime import datetime

def run_parameter_sweep():
    """運行參數掃描"""

    # 測試參數範圍
    gap_thresholds = [2, 3, 5, 8, 10, 15, 20]
    risk_per_trades = [25, 50, 75, 100, 150]
    num_days = 120

    results = []

    print('\n【開始參數掃描】')
    print(f'總共將執行 {len(gap_thresholds) * len(risk_per_trades)} 次回測...\n')

    for gap_threshold in gap_thresholds:
        for risk_per_trade in risk_per_trades:
            backtester = StandaloneBacktester(
                initial_cash=10000,
                risk_per_trade=risk_per_trade,
                gap_threshold=gap_threshold,
                max_daily_trades=12
            )

            metrics = backtester.run_simulation(num_days=num_days)

            # 計算綜合評分 (勝率 + 利潤因子 - 最大回撤)
            score = (
                metrics['win_rate'] * 2 +  # 勝率權重高
                metrics['profit_factor'] * 10 -  # 利潤因子最重要
                metrics['max_drawdown']  # 回撤越小越好
            )

            result = {
                'gap_threshold': gap_threshold,
                'risk_per_trade': risk_per_trade,
                'win_rate': metrics['win_rate'],
                'profit_factor': metrics['profit_factor'],
                'max_drawdown': metrics['max_drawdown'],
                'total_pnl': metrics['total_pnl'],
                'total_trades': metrics['total_trades'],
                'score': score
            }
            results.append(result)

            status = '✅' if metrics['total_pnl'] > 0 else '❌'
            print(
                f'{status} gap={gap_threshold:2}% risk=${risk_per_trade:3.0f} | '
                f'trades={metrics["total_trades"]:2} | '
                f'WR={metrics["win_rate"]:5.1f}% | '
                f'PF={metrics["profit_factor"]:5.2f} | '
                f'PnL=${metrics["total_pnl"]:+7.2f} | '
                f'Score={score:7.1f}'
            )

    # 排序結果
    results_sorted = sorted(results, key=lambda x: x['score'], reverse=True)

    print('\n' + '='*80)
    print('【TOP 10 最佳參數組合】')
    print('='*80)
    for i, result in enumerate(results_sorted[:10], 1):
        print(
            f'{i:2}. gap={result["gap_threshold"]:2}% risk=${result["risk_per_trade"]:3.0f} | '
            f'WR={result["win_rate"]:5.1f}% | '
            f'PF={result["profit_factor"]:5.2f} | '
            f'Drawdown={result["max_drawdown"]:5.2f}% | '
            f'PnL=${result["total_pnl"]:+7.2f} | '
            f'Trades={result["total_trades"]:2}'
        )

    # 保存詳細結果
    output_file = 'parameter_sweep_results.json'
    with open(output_file, 'w') as f:
        json.dump(results_sorted, f, indent=2)
    print(f'\n✅ 詳細結果已保存到 {output_file}')

    # 最差參數組合
    print('\n' + '='*80)
    print('【最差參數組合 TOP 5】')
    print('='*80)
    for i, result in enumerate(results_sorted[-5:], 1):
        print(
            f'{i}. gap={result["gap_threshold"]:2}% risk=${result["risk_per_trade"]:3.0f} | '
            f'WR={result["win_rate"]:5.1f}% | Score={result["score"]:7.1f}'
        )

if __name__ == '__main__':
    run_parameter_sweep()
