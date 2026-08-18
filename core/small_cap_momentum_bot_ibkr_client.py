"""
統一管理同 IBKR TWS / Gateway 嘅連線。
用 ib_async（原 ib_insync 嘅維護分支）。
"""
from ib_async import IB, Stock, LimitOrder, StopLimitOrder, ScannerSubscription

from config.settings import IB_HOST, IB_PORT, IB_CLIENT_ID, PAPER_TRADING
from utils.logger import get_logger

log = get_logger("ibkr_client")


class IBKRClient:
    def __init__(self):
        self.ib = IB()
        self.connected = False
        self.account = None

    def connect(self) -> IB:
        """連接到 IBKR"""
        if not PAPER_TRADING:
            raise RuntimeError(
                "PAPER_TRADING = False，但呢個系統未經過人手覆核唔應該接真實盤。"
                "如要轉真實盤，請喺 config/settings.py 手動確認先。"
            )
        log.info(f"連接 IBKR {IB_HOST}:{IB_PORT} clientId={IB_CLIENT_ID} ...")
        try:
            self.ib.connect(IB_HOST, IB_PORT, clientId=IB_CLIENT_ID, timeout=15)
            self.connected = self.ib.isConnected()
            if self.connected:
                log.info("✅ IBKR 連線成功")
                accounts = self.ib.managedAccounts()
                self.account = accounts[0] if accounts else None
                log.info(f"帳戶: {self.account}")
            else:
                raise ConnectionError("連接失敗")
        except Exception as e:
            log.error(f"❌ 連接 IBKR 失敗: {e}")
            raise

        return self.ib

    def disconnect(self):
        """斷開連線"""
        if self.ib.isConnected():
            self.ib.disconnect()
            self.connected = False
            log.info("已斷開 IBKR 連線")

    def is_connected(self) -> bool:
        """檢查連線狀態"""
        return self.ib.isConnected()

    @staticmethod
    def make_stock(symbol: str, exchange: str = "SMART", currency: str = "USD") -> Stock:
        """創建股票合約"""
        return Stock(symbol, exchange, currency)

    def qualify_contract(self, contract) -> Stock:
        """確認合約詳情"""
        try:
            result = self.ib.qualifyContracts(contract)
            if not result:
                raise ValueError(f"無法確認合約: {contract}")
            return result[0]
        except Exception as e:
            log.error(f"合約確認失敗: {e}")
            raise

    def place_buy_order(self, contract, quantity: int, limit_price: float):
        """下買單（限價）"""
        try:
            order = LimitOrder("BUY", quantity, limit_price)
            trade = self.ib.placeOrder(contract, order)
            log.info(f"下買單: {quantity} @ ${limit_price:.2f}")
            return trade
        except Exception as e:
            log.error(f"下買單失敗: {e}")
            return None

    def place_stop_limit_order(self, contract, quantity: int, stop_price: float, limit_price: float):
        """下止蝕單（Stop-Limit）"""
        try:
            order = StopLimitOrder("SELL", quantity, stop_price, limit_price)
            order.tif = "GTC"  # Good Till Cancelled
            trade = self.ib.placeOrder(contract, order)
            log.info(f"下止蝕單: {quantity} @ 止蝕 ${stop_price:.2f} 限價 ${limit_price:.2f}")
            return trade
        except Exception as e:
            log.error(f"下止蝕單失敗: {e}")
            return None

    def cancel_order(self, trade):
        """取消訂單"""
        try:
            if trade and trade.order:
                self.ib.cancelOrder(trade.order)
                log.info(f"訂單已取消")
                return True
        except Exception as e:
            log.error(f"取消訂單失敗: {e}")
        return False

    def get_market_data(self, contract, timeout: int = 2):
        """獲取市場數據"""
        try:
            ticker = self.ib.reqMktData(contract, "", False, False)
            self.ib.sleep(timeout)
            self.ib.cancelMktData(contract)
            return ticker
        except Exception as e:
            log.error(f"獲取市場數據失敗: {e}")
            return None

    def get_historical_data(self, contract, duration: str = "20 D", bar_size: str = "1 day"):
        """獲取歷史數據"""
        try:
            bars = self.ib.reqHistoricalData(
                contract,
                endDateTime="",
                durationStr=duration,
                barSizeSetting=bar_size,
                whatToShow="TRADES",
                useRTH=True
            )
            return list(bars) if bars else []
        except Exception as e:
            log.error(f"獲取歷史數據失敗: {e}")
            return []

    def scan_for_gap_up_stocks(self, min_gap_pct: float = 5.0, min_price: float = 2.0, max_price: float = 20.0):
        """IBKR 掃描器 - 尋找開盤跳空股票"""
        try:
            # 建立掃描器訂閱
            sub = ScannerSubscription(
                instrument="STK",
                locationCode="STK.US.MAJOR",
                scanCode="TOP_PERC_GAIN"  # 最大漲幅
            )

            # 設定掃描參數
            sub.abovePrice = min_price
            sub.belowPrice = max_price

            # 發送掃描請求
            results = self.ib.reqScannerData(sub)
            log.info(f"掃描結果: {len(results) if results else 0} 隻股票")

            # 提取股票代碼
            symbols = []
            if results:
                for result in results[:20]:  # 限制前 20 個結果
                    contract = result.contractDetails.contract
                    if contract and contract.symbol:
                        symbols.append(contract.symbol)

            return symbols

        except Exception as e:
            log.error(f"掃描器失敗: {e}")
            return []
