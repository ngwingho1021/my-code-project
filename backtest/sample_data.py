"""生成示例K線數據用於回測（繞過API限制）"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def generate_sample_bars(symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
    """
    生成模擬K線數據用於演示回測

    Args:
        symbol: 股票代碼
        start_date: 開始日期 (YYYY-MM-DD)
        end_date: 結束日期 (YYYY-MM-DD)

    Returns:
        DataFrame with OHLCV data
    """

    start = datetime.fromisoformat(start_date)
    end = datetime.fromisoformat(end_date)

    # 生成交易時間序列（排除週末）
    dates = []
    current = start
    while current <= end:
        if current.weekday() < 5:  # 週一至週五
            dates.append(current)
        current += timedelta(minutes=1)

    n = len(dates)

    # 生成模擬價格數據（基於SPY 2024年3月的價格）
    base_price = 410.0

    # 生成日內趨勢
    trend = np.cumsum(np.random.randn(n) * 0.05)
    close_prices = base_price + trend

    # 生成OHLC
    opens = close_prices + np.random.randn(n) * 0.1
    highs = np.maximum(opens, close_prices) + np.abs(np.random.randn(n) * 0.2)
    lows = np.minimum(opens, close_prices) - np.abs(np.random.randn(n) * 0.2)

    # 生成成交量（帶爆量）
    base_volume = 100000
    volumes = base_volume + np.random.randint(0, 50000, n)

    # 隨機加入爆量（模擬gap-up）
    gap_indices = np.random.choice(n, size=max(1, n // 1000), replace=False)
    for idx in gap_indices:
        volumes[idx] = base_volume * np.random.uniform(1.5, 3.0)

    df = pd.DataFrame({
        'o': opens,
        'h': highs,
        'l': lows,
        'c': close_prices,
        'v': volumes,
    }, index=dates)

    df.index.name = 'timestamp'
    return df
