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

    @staticmethod
    def _smart_contract(contract):
        """落單時強制用 SMART 路由，避免 Error 10311 direct routing"""
        from copy import copy
        c = copy(contract)
        c.exchange = "SMART"
        return c

    def place_buy_order(self, contract, quantity: int, limit_price: float):
        """下買單（限價）"""
        try:
            order = LimitOrder("BUY", quantity, limit_price)
            order.tif = "GTC"
            order.outsideRth = True
            trade = self.ib.placeOrder(self._smart_contract(contract), order)
            log.info(f"下買單: {quantity} @ ${limit_price:.2f} (GTC, outsideRth)")
            self.ib.sleep(2)
            if trade.orderStatus.status in ("Cancelled", "Inactive"):
                log.error(f"買單被拒絕/取消: {contract.symbol} (狀態: {trade.orderStatus.status})")
                return None
            return trade
        except Exception as e:
            log.error(f"下買單失敗: {e}")
            return None

    def get_position_shares(self, symbol: str) -> int:
        """查 IBKR 帳戶持有某股票嘅實際股數（唔包括 pending 單）"""
        try:
            positions = self.ib.positions()
            for p in positions:
                if p.contract.symbol == symbol and p.position > 0:
                    return int(p.position)
            return 0
        except Exception as e:
            log.error(f"查詢 {symbol} 持股數量失敗: {e}")
            return -1  # -1 = 查詢失敗

    def place_sell_order(self, contract, quantity: int, limit_price: float):
        """下賣單（限價）"""
        try:
            order = LimitOrder("SELL", quantity, limit_price)
            order.tif = "DAY"   # DAY：當日唔填就作廢，防止 GTC 積單 + 新賣單雙重成交做空
            order.outsideRth = False
            trade = self.ib.placeOrder(self._smart_contract(contract), order)
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
        """下賣單（市價）- 用於止蝕，只在盤中用"""
        try:
            order = MarketOrder("SELL", quantity)
            order.tif = "DAY"   # 市價單即成即走，唔需要 GTC 或 outsideRth
            trade = self.ib.placeOrder(self._smart_contract(contract), order)
            log.info(f"下市價賣單: {quantity}股 (DAY)")
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
            trade = self.ib.placeOrder(self._smart_contract(contract), order)
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

    def get_small_cap_position_count(self, min_price: float = 2.0, max_price: float = 20.0) -> int:
        """查詢帳戶內真實小市值持倉數量（過濾其他 bot 嘅大價股）"""
        try:
            positions = self.ib.positions()
            count = sum(
                1 for p in positions
                if p.position > 0 and min_price <= p.avgCost <= max_price
            )
            log.debug(f"帳戶真實小市值持倉: {count} 個")
            return count
        except Exception as e:
            log.error(f"查詢帳戶持倉失敗: {e}")
            return -1  # -1 = 查詢失敗

    def get_atr(self, contract, period: int = 14) -> float:
        """計算 ATR(14)，用日線 True Range"""
        try:
            bars = self.ib.reqHistoricalData(
                contract,
                endDateTime="",
                durationStr="20 D",
                barSizeSetting="1 day",
                whatToShow="TRADES",
                useRTH=True
            )
            bars = list(bars) if bars else []
            if len(bars) < period + 1:
                log.warning(f"ATR 數據不足: {len(bars)} 條 (需要 {period + 1})")
                return None

            true_ranges = []
            for i in range(1, len(bars)):
                high = bars[i].high
                low = bars[i].low
                prev_close = bars[i - 1].close
                tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
                true_ranges.append(tr)

            atr = sum(true_ranges[-period:]) / period
            return round(atr, 4)
        except Exception as e:
            log.error(f"計算 ATR 失敗: {e}")
            return None

    def get_prev_close(self, contract) -> float:
        """獲取前一日收盤價，用於計算開盤跳空 %"""
        try:
            bars = self.ib.reqHistoricalData(
                contract, endDateTime="", durationStr="3 D",
                barSizeSetting="1 day", whatToShow="TRADES", useRTH=True
            )
            bars = list(bars) if bars else []
            # bars[-1] 可能係今日（仍未收市），bars[-2] 係昨日收盤
            if len(bars) < 2:
                return None
            return round(bars[-2].close, 4)
        except Exception as e:
            log.error(f"獲取前收盤價失敗: {e}")
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
