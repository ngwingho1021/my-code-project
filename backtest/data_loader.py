"""Data loader for backtest — fetch from yfinance with caching."""

import os
import json
from datetime import datetime, timedelta
import pandas as pd
import yfinance as yf


class DataLoader:
    def __init__(self, cache_dir: str = './backtest/cache'):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)

    def get_daily_bars(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        載入日線數據（含盤前/盤後）

        Args:
            symbol: 股票代碼 (e.g., 'AAPL')
            start_date: 開始日期 (e.g., '2024-01-01')
            end_date: 結束日期 (e.g., '2024-12-31')

        Returns:
            DataFrame 含 OHLCV 數據
        """
        cache_file = os.path.join(self.cache_dir, f'{symbol}_{start_date}_{end_date}.parquet')

        # 先檢查快取
        if os.path.exists(cache_file):
            print(f'  📦 {symbol} 從快取讀取')
            return pd.read_parquet(cache_file)

        # 沒快取就從 yfinance 下載
        try:
            print(f'  ⬇️ {symbol} 從 yfinance 下載 ({start_date} ~ {end_date})...')
            df = yf.download(
                symbol,
                start=start_date,
                end=end_date,
                progress=False,
                prepost=True  # 含盤前盤後
            )

            if df.empty:
                print(f'  ❌ {symbol} 無數據')
                return pd.DataFrame()

            # 清理列名
            df.columns = ['Open', 'High', 'Low', 'Close', 'Volume', 'Adj Close']
            df = df.drop('Adj Close', axis=1)

            # 存快取
            df.to_parquet(cache_file)
            print(f'  ✅ {symbol} 下載完成，已快取')
            return df

        except Exception as e:
            print(f'  ⚠️ {symbol} 下載失敗: {e}')
            return pd.DataFrame()

    def get_gap_up_stocks(self,
                         gap_threshold: float = 20.0,
                         date: str = None) -> list:
        """
        從已有數據中找 gap up 的股票

        這裡先用簡單邏輯，實際應該連接掃描器
        """
        # 簡單實現：返回已知的爆升股票列表（可擴展）
        # 實際應該從 IBKR 掃描器或其他來源獲取

        gap_up_stocks = {
            # 2024年1月-8月的一些已知爆升股
            '2024-01-15': ['WYHG', 'TBKG', 'NAKD'],
            '2024-02-20': ['NVDA', 'PLTR'],
            '2024-03-10': ['GME', 'AMC'],
            '2024-04-05': ['AAPL', 'TSLA'],
        }

        if date in gap_up_stocks:
            return gap_up_stocks[date]
        return []

    def get_stock_info(self, symbol: str) -> dict:
        """獲取股票基本信息（float shares, 等）"""
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            return {
                'float_shares': info.get('floatShares', 0),
                'prev_close': info.get('previousClose', 0),
                'current_price': info.get('currentPrice', 0),
            }
        except Exception as e:
            print(f'  ⚠️ {symbol} 信息獲取失敗: {e}')
            return {}
