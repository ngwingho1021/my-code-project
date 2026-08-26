"""
統一管理同 IBKR TWS / Gateway 嘅連線。
用 ib_async（原 ib_insync 嘅維護分支）。
"""
from ib_async import IB, Stock, LimitOrder, MarketOrder, StopLimitOrder, ScannerSubscription

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
                self.ib.reqMarketDataType(1)
                log.info("已設置即時市場數據 (type 1 - Live)")
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
            order.tif = "GTC"
            order.outsideRth = True
            trade = self.ib.placeOrder(contract, order)
            log.info(f"下買單: {quantity} @ ${limit_price:.2f} (GTC, outsideRth)")
            self.ib.sleep(2)
            if trade.orderStatus.status == "Cancelled":
                log.error(f"買單被取消: {contract.symbol}")
                return None
            return trade
        except Exception as e:
            log.error(f"下買單失敗: {e}")
            return None

    def place_sell_order(self, contract, quantity: int, limit_price: float):
        """下賣單（限價）"""
        try:
            order = LimitOrder("SELL", quantity, limit_price)
            order.tif = "GTC"
            order.outsideRth = True
            trade = self.ib.placeOrder(contract, order)
            log.info(f"下賣單: {quantity} @ ${limit_price:.2f} (GTC, outsideRth)")
            self.ib.sleep(2)
            if trade.orderStatus.status == "Cancelled":
                log.error(f"賣單被取消: {contract.symbol}")
                return None
            return trade
        except Exception as e:
            log.error(f"下賣單失敗: {e}")
            return None

    def place_market_sell_order(self, contract, quantity: int):
        """下賣單（市價）- 用於止蝕"""
        try:
            order = MarketOrder("SELL", quantity)
            order.tif = "GTC"
            order.outsideRth = True
            trade = self.ib.placeOrder(contract, order)
            log.info(f"下市價賣單: {quantity}股 (GTC, outsideRth)")
            self.ib.sleep(2)
            if trade.orderStatus.status == "Cancelled":
                log.error(f"市價賣單被取消: {contract.symbol}")
                return None
            return trade
        except Exception as e:
            log.error(f"下市價賣單失敗: {e}")
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
        """獲取市場數據（snapshot，用於一次性查價）"""
        try:
            ticker = self.ib.reqMktData(contract, "", False, False)
            self.ib.sleep(timeout)
            self.ib.cancelMktData(contract)
            return ticker
        except Exception as e:
            log.error(f"獲取市場數據失敗: {e}")
            return None

    def subscribe_market_data(self, contract):
        """訂閱持續串流數據 - 返回 ticker，後台自動更新"""
        try:
            ticker = self.ib.reqMktData(contract, "", False, False)
            self.ib.sleep(0.5)  # 等首個 tick
            log.info(f"已訂閱串流數據: {contract.symbol}")
            return ticker
        except Exception as e:
            log.error(f"訂閱串流數據失敗: {e}")
            return None

    def unsubscribe_market_data(self, contract):
        """退訂串流數據"""
        try:
            self.ib.cancelMktData(contract)
            log.info(f"已退訂串流數據: {contract.symbol}")
        except Exception as e:
            log.error(f"退訂串流數據失敗: {e}")

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
        """IBKR 掃描器 - 尋找開盤跳空股票，返回合約列表"""
        try:
            sub = ScannerSubscription(
                instrument="STK",
                locationCode="STK.US.MAJOR",
                scanCode="TOP_PERC_GAIN"
            )

            sub.abovePrice = min_price
            sub.belowPrice = max_price

            results = self.ib.reqScannerData(sub)
            log.info(f"掃描結果: {len(results) if results else 0} 隻股票")

            scan_results = []
            if results:
                for result in results[:20]:
                    try:
                        cd = result.contractDetails
                        contract = cd.contract
                        if contract and contract.symbol:
                            scan_results.append({
                                "symbol": contract.symbol,
                                "contract": contract
                            })
                    except Exception as e:
                        continue

            if scan_results:
                log.info(f"✅ 找到: {[r['symbol'] for r in scan_results[:10]]}")

            return scan_results

        except Exception as e:
            log.error(f"掃描器失敗: {e}")
            return []
