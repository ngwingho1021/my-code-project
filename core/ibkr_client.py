"""
統一管理同 IBKR TWS / Gateway 嘅連線。
用 ib_async（原 ib_insync 嘅維護分支）。
"""
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
