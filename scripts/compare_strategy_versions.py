#!/usr/bin/env python3
"""
策略版本對比 — 評估改進效果

對比 4 個版本：
- baseline: 僅看 gap up
- v1: gap + 成交量
- v2: gap + 成交量 + 價格
- v3: 完整篩選（包含 ATR 動態止盈）
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse
from backtest.improved_backtester import ImprovedBacktester
import json


def parse_args():
    parser = argparse.ArgumentParser(description='策略版本對比')
    parser.add_argument('--days', type=int, default=120,
                       help='模擬天數')
    parser.add_argument('--initial-cash', type=float, default=10000,
                       help='初始資金')
    parser.add_argument('--risk-per-trade', type=float, default=100,
                       help='每筆交易風險')
    parser.add_argument('--gap', type=float, default=2.0,
                       help='Gap 門檻 (%)')
    return parser.parse_args()


def print_comparison(results):
    """打印對比報告"""
    print('\n' + '='*80)
    print('【策略版本對比報告】')
    print('='*80)

    # 表頭
    print('\n| 版本 | 交易數 | 勝率 | 平均贏 | 平均虧 | 利潤因子 | PnL | 回撤 | Sharpe |')
    print('|------|--------|--------|--------|--------|---------|------|--------|--------|')

    best_version = None
    best_pnl = -float('inf')

    for version, result in results.items():
        m = result['metrics']
        win_rate = m['win_rate']
        avg_win = m['avg_win']
        avg_loss = m['avg_loss']
        pf = m['profit_factor']
        pnl = m['total_pnl']
        dd = m['max_drawdown']
        sharpe = m['sharpe_ratio']

        print(
            f'| {version:8} | {m["total_trades"]:4} | {win_rate:5.1f}% | '
            f'${avg_win:6.2f} | ${avg_loss:6.2f} | {pf:7.2f} | '
            f'${pnl:+6.2f} | {dd:6.2f}% | {sharpe:6.2f} |'
        )

        if pnl > best_pnl:
            best_pnl = pnl
            best_version = version

    print('|------|--------|--------|--------|--------|---------|------|--------|--------|')

    # 詳細分析
    print('\n📊 詳細分析:')
    print(f'\n最佳版本: {best_version.upper()}')
    best_result = results[best_version]
    print(f'  交易筆數: {best_result["metrics"]["total_trades"]}')
    print(f'  勝率: {best_result["metrics"]["win_rate"]:.1f}%')
    print(f'  利潤因子: {best_result["metrics"]["profit_factor"]:.2f}')
    print(f'  淨利: ${best_result["metrics"]["total_pnl"]:+.2f} ({best_result["metrics"]["total_pnl_pct"]:+.2f}%)')
    print(f'  最大回撤: {best_result["metrics"]["max_drawdown"]:.2f}%')

    # 版本對比分析
    print('\n🔍 版本對比分析:')
    print(f'\nV1 vs Baseline:')
    baseline = results['baseline']['metrics']
    v1 = results['v1']['metrics']
    print(f'  交易變化: {v1["total_trades"]} vs {baseline["total_trades"]} '
          f'({v1["total_trades"] - baseline["total_trades"]:+d})')
    print(f'  勝率變化: {v1["win_rate"]:.1f}% vs {baseline["win_rate"]:.1f}%')
    print(f'  PnL 變化: ${v1["total_pnl"]:+.2f} vs ${baseline["total_pnl"]:+.2f}')

    print(f'\nV2 vs V1:')
    v2 = results['v2']['metrics']
    print(f'  交易變化: {v2["total_trades"]} vs {v1["total_trades"]} '
          f'({v2["total_trades"] - v1["total_trades"]:+d})')
    print(f'  勝率變化: {v2["win_rate"]:.1f}% vs {v1["win_rate"]:.1f}%')
    print(f'  PnL 變化: ${v2["total_pnl"]:+.2f} vs ${v1["total_pnl"]:+.2f}')

    print(f'\nV3 vs V2 (動態止盈):')
    v3 = results['v3']['metrics']
    print(f'  交易變化: {v3["total_trades"]} vs {v2["total_trades"]} '
          f'({v3["total_trades"] - v2["total_trades"]:+d})')
    print(f'  勝率變化: {v3["win_rate"]:.1f}% vs {v2["win_rate"]:.1f}%')
    print(f'  PnL 變化: ${v3["total_pnl"]:+.2f} vs ${v2["total_pnl"]:+.2f}')

    # 建議
    print('\n💡 建議:')
    if v1['total_trades'] < baseline['total_trades']:
        print('  ✅ V1 透過成交量篩選減少交易 (品質優先於數量)')
    if v2['win_rate'] > v1['win_rate']:
        print('  ✅ V2 透過價格確認改進勝率')
    if v3['profit_factor'] > v2['profit_factor']:
        print('  ✅ V3 透過動態止盈改進利潤因子')

    if best_result['metrics']['total_pnl'] > 0:
        print('  ✅ 策略改進有效！')
    else:
        print('  ⚠️  策略仍需優化，建議：')
        print('      • 進一步提高進場標準')
        print('      • 調整止盈/止蝕比例')
        print('      • 測試更多股票或時間段')

    print('\n' + '='*80)


def main():
    args = parse_args()

    print('\n╔════════════════════════════════════════════════════════════╗')
    print('║         🔄 策略版本對比 — Ross Cameron 策略             ║')
    print('║         評估改進：進場條件、止盈、風險管理             ║')
    print('╚════════════════════════════════════════════════════════════╝')

    print(f'\n⚙️ 配置:')
    print(f'  模擬天數: {args.days}')
    print(f'  初始資金: ${args.initial_cash:,.0f}')
    print(f'  風險/筆: ${args.risk_per_trade:.0f}')
    print(f'  Gap 門檻: {args.gap}%')

    # 運行 4 個版本
    versions = ['baseline', 'v1', 'v2', 'v3']
    results = {}

    for version in versions:
        print(f'\n🚀 運行 {version.upper()}...')
        backtester = ImprovedBacktester(
            initial_cash=args.initial_cash,
            risk_per_trade=args.risk_per_trade,
            gap_threshold=args.gap,
            strategy_version=version
        )

        metrics = backtester.run_simulation(num_days=args.days)
        results[version] = {
            'metrics': metrics,
            'trades': backtester.trades
        }

    # 打印對比
    print_comparison(results)

    # 保存詳細結果
    output_file = 'strategy_comparison_results.json'
    serializable_results = {}

    for version, data in results.items():
        serializable_results[version] = {
            'metrics': {
                k: (float(v) if isinstance(v, (int, float)) else v)
                for k, v in data['metrics'].items()
            },
            'trades': [
                {
                    'symbol': t.symbol,
                    'entry_date': t.entry_date,
                    'entry_price': float(t.entry_price),
                    'quantity': int(t.quantity),
                    'pnl': float(t.pnl()),
                    'pnl_pct': float(t.pnl_pct()),
                    'exit_type': t.exit_type
                }
                for t in data['trades']
            ]
        }

    with open(output_file, 'w') as f:
        json.dump(serializable_results, f, indent=2)
    print(f'\n✅ 詳細結果已保存到 {output_file}')


if __name__ == '__main__':
    main()
