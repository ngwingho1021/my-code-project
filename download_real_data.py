"""
Windows 用户专用：下载真实股票数据脚本

在 Windows CMD 中直接运行：
  python download_real_data.py
"""

import yfinance as yf
import os
import sys

def download_stock_data():
    """下载多只股票的历史数据"""

    # 创建输出目录
    os.makedirs('backtest/csv_data', exist_ok=True)

    # 股票列表（gap-up 策略常见）
    symbols = ['NVDA', 'AMD', 'TSLA', 'PLTR', 'AAPL', 'MSFT', 'GOOGL', 'META']

    print('=' * 60)
    print('【下载真实股票数据】')
    print('=' * 60)
    print(f'\n股票代码: {", ".join(symbols)}')
    print('时间范围: 2024-01-01 ~ 2024-08-31')
    print('输出目录: backtest/csv_data/')
    print('\n开始下载...\n')

    success_count = 0

    for symbol in symbols:
        try:
            print(f'⬇️  {symbol:6} ', end='', flush=True)

            # 下载数据
            df = yf.download(
                symbol,
                start='2024-01-01',
                end='2024-08-31',
                progress=False
            )

            if df.empty:
                print('❌ 无数据')
                continue

            # 保存为 CSV
            filepath = f'backtest/csv_data/{symbol}.csv'
            df.to_csv(filepath)

            print(f'✅ 完成 ({len(df)} 行)')
            success_count += 1

        except Exception as e:
            print(f'❌ 错误: {str(e)[:40]}')

    print('\n' + '=' * 60)
    print(f'下载完成: {success_count}/{len(symbols)} 成功')
    print(f'保存位置: {os.path.abspath("backtest/csv_data")}')
    print('=' * 60)

    if success_count > 0:
        print('\n✅ 数据已准备好，可以运行回测：')
        print('python scripts/run_backtest_with_real_or_mock.py --mode csv --csv backtest/csv_data/NVDA.csv')
    else:
        print('\n❌ 无法下载数据，检查网络连接')
        sys.exit(1)

if __name__ == '__main__':
    download_stock_data()
