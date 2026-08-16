"""
統一管理同 IBKR TWS / Gateway 嘅連線。
用 ib_async（原 ib_insync 嘅維護分支）。
"""

# Python 3.14 相容性修復：設定預設事件循環
import asyncio
import sys
if sys.version_info >= (3, 10):
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())

import pandas as pd
from datetime import datetime
from ib_async import IB, Stock, MarketOrder, StopOrder, StopLimitOrder, LimitOrder

from config.settings import IB_HOST, IB_PORT, IB_CLIENT_ID, PAPER_TRADING
from utils.logger import get_logger

log = get_logger("ibkr_client")


class IBKRClient:
    def __init__(self):
        self.ib = IB()
        self.connected = False

    def connect(self):
        if not PAPER_TRADING:
            raise RuntimeError(
                "PAPER_TRADING = False，但呢個系統未經過人手覆核唔應該接真實盤。"
                "如要轉真實盤，請喺 config/settings.py 手動確認先。"
            )
        log.info(f"連接 IBKR {IB_HOST}:{IB_PORT} clientId={IB_CLIENT_ID} ...")
        self.ib.connect(IB_HOST, IB_PORT, clientId=IB_CLIENT_ID, timeout=15)
        self.connected = self.ib.isConnected()
        if self.connected:
            log.info("IBKR 連線成功。")
            # 確認真係連咗 paper account
            accounts = self.ib.managedAccounts()
            log.info(f"管理帳戶: {accounts}")
        else:
            raise ConnectionError("連接 IBKR 失敗，請確認 TWS/Gateway 已開啟並啟用 API。")
        return self.ib

    def disconnect(self):
        if self.ib.isConnected():
            self.ib.disconnect()
            log.info("已同 IBKR 斷開連線。")

    @staticmethod
    def make_stock(symbol: str, exchange: str = "SMART", currency: str = "USD") -> Stock:
        return Stock(symbol, exchange, currency)

    def qualify(self, contract):
        result = self.ib.qualifyContracts(contract)
        if not result:
            raise ValueError(f"無法確認合約: {contract}")
        return result[0]

    def get_historical_bars(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        timeframe: str = "1 Min",
        exchange: str = "SMART",
        currency: str = "USD"
    ) -> pd.DataFrame:
        """
        從IBKR獲取歷史K線數據

        Args:
            symbol: 股票代碼 (例: "SPY")
            start_date: 開始日期 (YYYY-MM-DD)
            end_date: 結束日期 (YYYY-MM-DD)
            timeframe: 時間框架 ("1 Min", "5 Mins", "1 hour", "1 day" 等)
            exchange: 交易所 (預設: "SMART")
            currency: 貨幣 (預設: "USD")

        Returns:
            DataFrame with columns ['o', 'h', 'l', 'c', 'v'] indexed by timestamp
        """
        if not self.connected:
            raise ConnectionError("IBKR未連接，請先調用 connect()")

        # 創建股票合約
        contract = self.make_stock(symbol, exchange, currency)
        contract = self.qualify(contract)

        # 計算持續時間字符串
        start_dt = datetime.fromisoformat(start_date)
        end_dt = datetime.fromisoformat(end_date)
        days_diff = (end_dt - start_dt).days

        if days_diff <= 0:
            raise ValueError(f"結束日期必須晚於開始日期: {start_date} to {end_date}")

        # 根據日期範圍構造持續時間字符串
        if days_diff <= 1:
            duration_str = "1 D"
        elif days_diff <= 30:
            duration_str = f"{days_diff + 1} D"
        elif days_diff <= 365:
            weeks = (days_diff + 1) // 7
            duration_str = f"{weeks} W"
        else:
            years = (days_diff + 1) // 365
            duration_str = f"{years} Y"

        log.info(
            f"從IBKR獲取 {symbol} K線: "
            f"開始={start_date}, 結束={end_date}, 周期={timeframe}, 持續={duration_str}"
        )

        try:
            # 從IBKR請求歷史數據
            bars = self.ib.reqHistoricalData(
                contract,
                endDateTime=end_dt.strftime("%Y%m%d %H:%M:%S"),
                durationStr=duration_str,
                barSizeSetting=timeframe,
                whatToShow="TRADES",
                useRTH=True,  # 交易時段數據 (排除盤前/盤後)
                formatDate=1,  # 返回datetime對象
            )

            if not bars:
                log.warning(f"⚠️  {symbol} 無K線數據 ({start_date} to {end_date})")
                return pd.DataFrame()

            # 轉換為DataFrame
            df = pd.DataFrame({
                'o': [bar.open for bar in bars],
                'h': [bar.high for bar in bars],
                'l': [bar.low for bar in bars],
                'c': [bar.close for bar in bars],
                'v': [int(bar.volume) for bar in bars],
            }, index=[bar.date for bar in bars])

            df.index.name = 'timestamp'
            df = df.sort_index()

            log.info(f"✅ {symbol}: 獲取 {len(df)} 根K線 ({df.index[0]} to {df.index[-1]})")
            return df

        except Exception as e:
            log.error(f"❌ 從IBKR獲取 {symbol} 數據失敗: {e}")
            raise
