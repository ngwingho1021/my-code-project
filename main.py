"""
主程式：連接 IBKR -> 掃描 -> 監控 -> 進場 -> 管理持倉 -> 離場。
用法（Paper Trading）:
    1. 開啟 TWS 或 IB Gateway，登入 Paper Trading 帳戶
    2. TWS: File -> Global Configuration -> API -> Settings，
       打勾 "Enable ActiveX and Socket Clients"，Socket port 設做 7497
    3. pip install -r requirements.txt
    4. python main.py
"""
import time
import pandas as pd

from config.settings import TRADING_HOURS, SCANNER
from core.ibkr_client import IBKRClient
from core.scanner import MomentumScanner
from core.news import NewsChecker
from core.level2 import Level2Monitor
from core.order_manager import OrderManager
from core.risk_manager import RiskManager
from strategy.ross_cameron import RossCameronStrategy
from utils.logger import get_logger

log = get_logger("main")

SCAN_INTERVAL_SEC = 60
MANAGE_INTERVAL_SEC = 5


def bars_to_df(bars) -> pd.DataFrame:
    if not bars:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
    return pd.DataFrame({
        "open": [b.open for b in bars],
        "high": [b.high for b in bars],
        "low": [b.low for b in bars],
        "close": [b.close for b in bars],
        "volume": [b.volume for b in bars],
    })


class TradingBot:
    def __init__(self):
        self.client = IBKRClient()
        self.ib = None
        self.risk = RiskManager()
        self.order_mgr: OrderManager | None = None
        self.watchlist: dict[str, dict] = {}  # symbol -> {contract, level2, strategy, has_catalyst}

    def start(self):
        self.ib = self.client.connect()
        self.order_mgr = OrderManager(self.ib)
        log.info("交易機械人啟動（Paper Trading）")
        log.info(self.risk.status_summary())

        try:
            self.run_loop()
        except KeyboardInterrupt:
            log.info("收到手動中止指令，準備安全結束...")
        finally:
            self.shutdown()

    def run_loop(self):
        last_scan = 0
        while True:
            now = time.time()
            if now - last_scan > SCAN_INTERVAL_SEC:
                self.scan_for_candidates()
                last_scan = now

            self.manage_open_positions()
            self.evaluate_entries()
            time.sleep(MANAGE_INTERVAL_SEC)

    # ------------------------------------------------------------------
    def scan_for_candidates(self):
        scanner = MomentumScanner(self.ib)
        symbols = scanner.scan_gap_up_candidates()
        results = scanner.enrich_and_filter(symbols)

        news_checker = NewsChecker(self.ib)
        for r in results:
            if r.symbol in self.watchlist:
                continue
            contract = self.client.make_stock(r.symbol)
            self.client.qualify(contract)

            catalyst_info = news_checker.get_catalyst(r.symbol, contract)
            if SCANNER.require_catalyst and not catalyst_info.has_catalyst:
                log.info(f"{r.symbol} 冇催化劑，跳過（require_catalyst=True）")
                continue

            level2 = Level2Monitor(r.symbol)
            self._subscribe_level2(contract, level2)

            self.watchlist[r.symbol] = {
                "contract": contract,
                "level2": level2,
                "strategy": RossCameronStrategy(r.symbol, level2, catalyst_info.has_catalyst),
            }
            log.info(f"加入監控名單: {r.symbol} gap={r.gap_pct:.1f}% relVol={r.rel_volume:.1f}x "
                     f"catalyst={catalyst_info.has_catalyst}")

    def _subscribe_level2(self, contract, level2: Level2Monitor):
        try:
            depth = self.ib.reqMktDepth(contract, numRows=10)

            def on_update(depth_ticker):
                bids = [(lvl.price, lvl.size) for lvl in depth_ticker.domBids]
                asks = [(lvl.price, lvl.size) for lvl in depth_ticker.domAsks]
                level2.on_depth_update(bids, asks)

            depth.updateEvent += on_update

            tick = self.ib.reqMktData(contract, "", False, False)

            def on_tick(t):
                if t.last and t.lastSize:
                    at_ask = t.last >= (t.ask or t.last)
                    level2.on_tape_print(t.last, t.lastSize, at_ask)

            tick.updateEvent += on_tick
        except Exception as e:
            log.warning(f"訂閱 Level2/Tape 失敗: {e}")

    # ------------------------------------------------------------------
    def evaluate_entries(self):
        for symbol, info in list(self.watchlist.items()):
            if symbol in self.order_mgr.positions:
                continue

            bars_1m = bars_to_df(self._get_recent_bars(info["contract"], "1 min", "2 D"))
            bars_10s = bars_to_df(self._get_recent_bars(info["contract"], "10 secs", "1800 S"))

            signal = info["strategy"].evaluate_entry(bars_1m, bars_10s)
            if not signal.should_enter:
                continue

            planned_risk = abs(signal.entry_price - signal.stop_price)
            shares = self.risk.position_size(signal.entry_price, signal.stop_price)
            if shares <= 0:
                log.info(f"{symbol} 計算出股數為 0，跳過")
                continue

            total_risk_dollars = planned_risk * shares
            ok, why = self.risk.can_open_new_trade(symbol, total_risk_dollars)
            if not ok:
                log.info(f"{symbol} 風控否決進場: {why}")
                continue

            self.order_mgr.enter_long(info["contract"], symbol, shares, signal.entry_price, signal.stop_price)
            self.risk.register_open(symbol, signal.entry_price, shares, signal.stop_price)

    def manage_open_positions(self):
        for symbol, pos in list(self.order_mgr.positions.items()):
            info = self.watchlist.get(symbol)
            if not info:
                continue

            self.order_mgr.monitor_and_manage_halts(symbol)
            if symbol in self.order_mgr.halted_symbols:
                continue  # 熔斷期間唔做任何策略判斷

            bars_1m = bars_to_df(self._get_recent_bars(info["contract"], "1 min", "2 D"))
            if len(bars_1m) == 0:
                continue

            exit_signal = info["strategy"].evaluate_exit(
                bars_1m, pos.entry_price, pos.trailing_stop_price or pos.initial_stop,
                pos.remaining_shares / pos.shares, pos.took_profit_1, pos.took_profit_2,
            )

            if not exit_signal.should_exit:
                new_trailing = info["strategy"].compute_trailing_stop(
                    bars_1m, pos.trailing_stop_price or pos.initial_stop
                )
                if new_trailing != (pos.trailing_stop_price or pos.initial_stop):
                    self.order_mgr.update_stop(symbol, new_trailing)
                continue

            last_price = bars_1m["close"].iloc[-1]

            if exit_signal.exit_type == "target1":
                self.order_mgr.take_partial_profit(symbol, STRATEGY_PROFIT_1_PCT(), last_price)
                self.risk.register_partial_close(symbol, int(pos.shares * STRATEGY_PROFIT_1_PCT()), last_price)
                pos.took_profit_1 = True
            elif exit_signal.exit_type == "target2":
                self.order_mgr.take_partial_profit(symbol, STRATEGY_PROFIT_2_PCT(), last_price)
                self.risk.register_partial_close(symbol, int(pos.shares * STRATEGY_PROFIT_2_PCT()), last_price)
                pos.took_profit_2 = True
            else:
                self.order_mgr.exit_all(symbol, exit_signal.reason)
                self.risk.register_full_close(symbol, last_price)

    def _get_recent_bars(self, contract, bar_size: str, duration: str):
        return self.ib.reqHistoricalData(
            contract, endDateTime="", durationStr=duration,
            barSizeSetting=bar_size, whatToShow="TRADES", useRTH=False, keepUpToDate=False,
        )

    def shutdown(self):
        self.client.disconnect()
        log.info("已安全結束。" + self.risk.status_summary())


def STRATEGY_PROFIT_1_PCT():
    from config.settings import STRATEGY
    return STRATEGY.profit_take_1_pct


def STRATEGY_PROFIT_2_PCT():
    from config.settings import STRATEGY
    return STRATEGY.profit_take_2_pct


if __name__ == "__main__":
    bot = TradingBot()
    bot.start()
