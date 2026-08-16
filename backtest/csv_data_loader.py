"""CSV 數據導入器 - 支持用戶上傳本地數據進行回測"""

import os
import pandas as pd
from datetime import datetime


class CSVDataLoader:
    """從 CSV 文件加載歷史數據"""

    def __init__(self, csv_dir: str = './backtest/csv_data'):
        self.csv_dir = csv_dir
        os.makedirs(csv_dir, exist_ok=True)

    def load_from_csv(self, symbol: str, csv_path: str) -> pd.DataFrame:
        """
        從 CSV 文件加載數據

        CSV 格式要求：
        Date,Open,High,Low,Close,Volume
        2024-06-01,100.0,102.5,99.5,101.0,1000000
        ...

        Args:
            symbol: 股票代碼（用於快取）
            csv_path: CSV 文件路徑

        Returns:
            OHLCV DataFrame
        """
        if not os.path.exists(csv_path):
            print(f'  ❌ {symbol} CSV 文件不存在: {csv_path}')
            return pd.DataFrame()

        try:
            print(f'  📂 {symbol} 從 CSV 加載: {csv_path}')
            df = pd.read_csv(csv_path)

            # 標準化列名
            df.columns = [col.strip() for col in df.columns]
            required_cols = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']

            # 檢查必要列
            if not all(col in df.columns for col in required_cols):
                print(f'  ❌ CSV 缺少必要列。需要: {required_cols}')
                print(f'     實際列: {list(df.columns)}')
                return pd.DataFrame()

            # 設置日期為索引
            df['Date'] = pd.to_datetime(df['Date'])
            df.set_index('Date', inplace=True)

            # 選擇 OHLCV 列
            df = df[required_cols[1:]]

            print(f'  ✅ 成功加載 {len(df)} 條數據 ({df.index[0].date()} ~ {df.index[-1].date()})')
            return df

        except Exception as e:
            print(f'  ❌ {symbol} CSV 加載失敗: {e}')
            return pd.DataFrame()

    def list_available_files(self) -> list:
        """列出 csv_data 目錄中的所有文件"""
        if not os.path.exists(self.csv_dir):
            return []

        files = []
        for f in os.listdir(self.csv_dir):
            if f.endswith('.csv'):
                files.append(os.path.join(self.csv_dir, f))
        return sorted(files)

    def create_sample_csv(self):
        """創建示例 CSV 文件"""
        sample_data = {
            'Date': [
                '2024-06-01', '2024-06-02', '2024-06-03',
                '2024-06-04', '2024-06-05', '2024-06-06'
            ],
            'Open': [100.0, 102.0, 98.5, 105.0, 107.0, 106.0],
            'High': [102.5, 104.0, 102.0, 107.0, 109.5, 108.0],
            'Low': [99.5, 101.0, 97.0, 103.0, 105.5, 104.0],
            'Close': [101.0, 103.0, 100.0, 106.0, 108.0, 107.0],
            'Volume': [1000000, 1200000, 900000, 1500000, 1300000, 1100000]
        }

        df = pd.DataFrame(sample_data)
        sample_file = os.path.join(self.csv_dir, 'SAMPLE.csv')
        df.to_csv(sample_file, index=False)
        print(f'✅ 示例 CSV 已建立: {sample_file}')
        print('   可以此作為模板添加真實數據')
        return sample_file
