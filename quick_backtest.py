"""
快速回测工具 - 完全独立版本
在 Windows CMD 中运行：python quick_backtest.py

无需任何外部依赖（pandas 和 numpy 除外）
"""

import pandas as pd
import numpy as np
import os
import json
from datetime import datetime


def run_mock_backtest(days=120, gap_threshold=2.0, risk_per_trade=100):
    """运行模拟回测"""
    print('\n【模拟数据回测】')
    print(f'  天数: {days}')
    print(f'  Gap 门槛: {gap_threshold}%')
    print(f'  风险: ${risk_per_trade}')

    # 生成模拟价格数据
    np.random.seed(42)
    dates = pd.bdate_range(periods=days)

    prices = [10.0]
    for _ in range(days):
        change = np.random.normal(0, 0.03)
        prices.append(prices[-1] * (1 + change))

    trades = []
    cash = 10000

    for i in range(1, len(prices)-1):
        prev_close = prices[i]
        today_open = prices[i+1] * (1 - gap_threshold/100) if np.random.random() < 0.15 else prices[i+1]
        today_high = today_open * 1.03
        today_low = today_open * 0.97
        today_close = prices[i+1]

        gap_pct = ((today_open - prev_close) / prev_close) * 100

        if gap_pct < gap_threshold:
            continue

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

        trades.append({
            'pnl': pnl,
            'type': exit_type,
            'entry': entry_price,
            'exit': exit_price
        })

    # 计算指标
    if not trades:
        return {
            'trades': 0,
            'win_rate': 0,
            'pnl': 0,
            'pnl_pct': 0,
            'profit_factor': 0,
            'final_nav': cash
        }

    wins = [t for t in trades if t['pnl'] > 0]
    losses = [t for t in trades if t['pnl'] < 0]
    total_pnl = sum(t['pnl'] for t in trades)

    profit_factor = sum(t['pnl'] for t in wins) / abs(sum(t['pnl'] for t in losses)) if losses else float('inf')

    return {
        'trades': len(trades),
        'win_rate': len(wins) / len(trades) * 100,
        'pnl': total_pnl,
        'pnl_pct': total_pnl / 10000 * 100,
        'profit_factor': profit_factor if profit_factor != float('inf') else 999,
        'final_nav': cash,
        'avg_win': sum(t['pnl'] for t in wins) / len(wins) if wins else 0,
        'avg_loss': sum(t['pnl'] for t in losses) / len(losses) if losses else 0,
    }


def run_csv_backtest(csv_file, gap_threshold=2.0, risk_per_trade=100):
    """运行 CSV 回测"""
    if not os.path.exists(csv_file):
        print(f'\n❌ 文件不存在: {csv_file}')
        return None

    print(f'\n【CSV 数据回测】')
    print(f'  文件: {csv_file}')
    print(f'  Gap 门槛: {gap_threshold}%')

    try:
        df = pd.read_csv(csv_file, index_col=0, parse_dates=True)
    except Exception as e:
        print(f'❌ 读取失败: {e}')
        return None

    if df.empty:
        print('❌ CSV 文件为空')
        return None

    print(f'  数据范围: {df.index[0].date()} ~ {df.index[-1].date()} ({len(df)} 行)')

    trades = []
    cash = 10000

    for i in range(1, len(df)):
        prev_close = df.iloc[i-1]['Close']
        today_open = df.iloc[i]['Open']
        today_high = df.iloc[i]['High']
        today_low = df.iloc[i]['Low']
        today_close = df.iloc[i]['Close']

        gap_pct = ((today_open - prev_close) / prev_close) * 100

        if gap_pct < gap_threshold:
            continue

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

        trades.append({
            'pnl': pnl,
            'type': exit_type,
            'entry': entry_price,
            'exit': exit_price
        })

    if not trades:
        print('❌ 无交易生成')
        return None

    wins = [t for t in trades if t['pnl'] > 0]
    losses = [t for t in trades if t['pnl'] < 0]
    total_pnl = sum(t['pnl'] for t in trades)

    profit_factor = sum(t['pnl'] for t in wins) / abs(sum(t['pnl'] for t in losses)) if losses else 999

    return {
        'trades': len(trades),
        'win_rate': len(wins) / len(trades) * 100,
        'pnl': total_pnl,
        'pnl_pct': total_pnl / 10000 * 100,
        'profit_factor': profit_factor,
        'final_nav': cash,
        'avg_win': sum(t['pnl'] for t in wins) / len(wins) if wins else 0,
        'avg_loss': sum(t['pnl'] for t in losses) / len(losses) if losses else 0,
    }


def print_results(mock_result, csv_result):
    """打印结果和对比"""
    print('\n' + '='*70)
    print('【回测结果对比】')
    print('='*70)

    print(f'\n交易笔数: {mock_result["trades"]:3d} (Mock) vs {csv_result["trades"]:3d} (CSV)')
    print(f'勝率:     {mock_result["win_rate"]:5.1f}% (Mock) vs {csv_result["win_rate"]:5.1f}% (CSV)')
    print(f'利潤因子: {mock_result["profit_factor"]:5.2f} (Mock) vs {csv_result["profit_factor"]:5.2f} (CSV)')
    print(f'淨利:     ${mock_result["pnl"]:7.2f} (Mock) vs ${csv_result["pnl"]:7.2f} (CSV)')
    print(f'回报率:   {mock_result["pnl_pct"]:5.2f}% (Mock) vs {csv_result["pnl_pct"]:5.2f}% (CSV)')

    print('\n' + '='*70)
    print('【评估】')
    print('='*70)

    if csv_result['win_rate'] > 40:
        print('✅ CSV 胜率 > 40% - 策略很有潜力！')
        print('   建议：进行纸上交易验证 → 小额实盘')
    elif csv_result['win_rate'] > 35:
        print('✅ CSV 胜率 35-40% - 策略有潜力')
        print('   建议：纸上交易验证')
    elif csv_result['win_rate'] > 25:
        print('🟡 CSV 胜率 25-35% - 需要改进')
        print('   建议：调整参数重新测试')
    else:
        print('❌ CSV 胜率 < 25% - 策略需要重设计')
        print('   建议：考虑架构改进')

    # 对比差异
    diff_wr = mock_result['win_rate'] - csv_result['win_rate']
    diff_pnl = mock_result['pnl'] - csv_result['pnl']

    print(f'\nMock vs CSV 差异:')
    print(f'  胜率差: {diff_wr:+.1f}% (Mock 更乐观)')
    print(f'  利润差: ${diff_pnl:+.2f} (Mock 更乐观)')
    print(f'\n→ Mock 数据比真实数据乐观 {"" if diff_wr > 0 else "保守"}')


def main():
    """主程序"""
    print('\n╔════════════════════════════════════════════════════════════╗')
    print('║        🎯 快速回测 - Mock vs 真实数据对比              ║')
    print('╚════════════════════════════════════════════════════════════╝')

    # 运行 Mock 回测
    print('\n⏳ 运行 Mock 回测...')
    mock_result = run_mock_backtest(days=120, gap_threshold=2.0, risk_per_trade=100)

    print(f'  交易: {mock_result["trades"]} | 胜率: {mock_result["win_rate"]:.1f}% | PnL: ${mock_result["pnl"]:.2f}')

    # 查找 CSV 文件
    csv_dir = 'backtest/csv_data'
    if not os.path.exists(csv_dir):
        print(f'\n❌ 未找到数据目录: {csv_dir}')
        print('请先运行数据下载命令')
        return

    csv_files = [f for f in os.listdir(csv_dir) if f.endswith('.csv')]
    if not csv_files:
        print(f'\n❌ 未找到 CSV 文件')
        return

    # 运行 CSV 回测（第一个文件）
    csv_file = os.path.join(csv_dir, csv_files[0])
    print(f'\n⏳ 运行 CSV 回测 ({csv_files[0]})...')
    csv_result = run_csv_backtest(csv_file, gap_threshold=2.0, risk_per_trade=100)

    if csv_result:
        print(f'  交易: {csv_result["trades"]} | 胜率: {csv_result["win_rate"]:.1f}% | PnL: ${csv_result["pnl"]:.2f}')

        # 打印对比结果
        print_results(mock_result, csv_result)

        # 如果有多个 CSV 文件，提示用户
        if len(csv_files) > 1:
            print(f'\n💡 可以测试其他股票: {", ".join([f[:-4] for f in csv_files[1:]])}')

    print('\n' + '='*70)
    print('完成！')
    print('='*70 + '\n')


if __name__ == '__main__':
    main()
