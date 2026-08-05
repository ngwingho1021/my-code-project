"""
落單同離場執行層，重點處理：
  - 防滑價：止蝕用 STP LMT（stop-limit）而唔係純 STP（stop-market），
    避免急跌時以極差價位成交。
  - 熔斷 (LULD halt) 偵測同復牌 (resume) 後嘅安全處理。
  - 分批止盈。
"""
import time as time_mod
from dataclasses import dataclass

from ib_async import LimitOrder, StopLimitOrder, MarketOrder, Order

from config.settings import EXEC_SAFETY, STRATEGY
from utils.logger import get_logger

log = get_logger("order_manager")
trade_log = get_logger("trade")


@dataclass
class Position:
    symbol: str
    contract: object
    entry_price: float
    initial_stop: float
    shares: int
    remaining_shares: int
    took_profit_1: bool = False
    took_profit_2: bool = False
    trailing_stop_price: float | None = None


class OrderManager:
    def __init__(self, ib):
        self.ib = ib
        self.positions: dict[str, Position] = {}
        self.halted_symbols: set[str] = set()

    # ------------------------------------------------------------------
    # 進場
    # ------------------------------------------------------------------
    def enter_long(self, contract, symbol: str, shares: int, limit_price: float, stop_price: float):
        entry_order = LimitOrder("BUY", shares, round(limit_price, 2))
        trade = self.ib.placeOrder(contract, entry_order)
        self.ib.sleep(1)

        pos = Position(
            symbol=symbol, contract=contract, entry_price=limit_price,
            initial_stop=stop_price, shares=shares, remaining_shares=shares,
        )
        self.positions[symbol] = pos
        self._place_protective_stop(pos, stop_price)
        trade_log.info(f"ENTER {symbol} shares={shares} limit={limit_price:.4f} stop={stop_price:.4f}")
        return trade

    def _place_protective_stop(self, pos: Position, stop_price: float):
        """用 STP LMT 落止蝕，limit 價比 stop 價再低一個 offset，防止市價單喺急跌時以爛價成交。
        代價係喺極端流動性蒸發情況下有可能唔成交 —— 呢個由 monitor_and_manage_halts 處理。"""
        if EXEC_SAFETY.use_stop_limit_not_stop_market:
            limit_offset = stop_price * (EXEC_SAFETY.stop_limit_offset_pct / 100)
            stop_limit_price = round(stop_price - limit_offset, 2)
            order = StopLimitOrder("SELL", pos.remaining_shares, round(stop_price, 2), stop_limit_price)
        else:
            order = Order(action="SELL", orderType="STP", totalQuantity=pos.remaining_shares,
                           auxPrice=round(stop_price, 2))
        order.tif = "GTC"
        trade = self.ib.placeOrder(pos.contract, order)
        pos.stop_trade = trade
        return trade

    def update_stop(self, symbol: str, new_stop_price: float):
        pos = self.positions.get(symbol)
        if not pos:
            return
        existing = getattr(pos, "stop_trade", None)
        if existing and existing.orderStatus.status not in ("Filled", "Cancelled"):
            self.ib.cancelOrder(existing.order)
            self.ib.sleep(0.5)
        pos.trailing_stop_price = new_stop_price
        self._place_protective_stop(pos, new_stop_price)
        trade_log.info(f"{symbol} 更新止蝕價 -> {new_stop_price:.4f}")

    # ------------------------------------------------------------------
    # 分批止盈
    # ------------------------------------------------------------------
    def take_partial_profit(self, symbol: str, pct_of_original: float, limit_price: float):
        pos = self.positions.get(symbol)
        if not pos:
            return
        shares_to_sell = int(pos.shares * pct_of_original)
        shares_to_sell = min(shares_to_sell, pos.remaining_shares)
        if shares_to_sell <= 0:
            return
        order = LimitOrder("SELL", shares_to_sell, round(limit_price, 2))
        trade = self.ib.placeOrder(pos.contract, order)
        pos.remaining_shares -= shares_to_sell
        trade_log.info(f"{symbol} 分批止盈 shares={shares_to_sell} @ {limit_price:.4f} 剩低={pos.remaining_shares}")

        # 剩返嘅倉位要重新落一張細數量嘅保護性止蝕單
        if pos.remaining_shares > 0:
            existing = getattr(pos, "stop_trade", None)
            if existing and existing.orderStatus.status not in ("Filled", "Cancelled"):
                self.ib.cancelOrder(existing.order)
                self.ib.sleep(0.5)
            self._place_protective_stop(pos, pos.trailing_stop_price or pos.initial_stop)
        return trade

    def exit_all(self, symbol: str, reason: str, use_market: bool = False):
        pos = self.positions.get(symbol)
        if not pos or pos.remaining_shares <= 0:
            return None

        existing = getattr(pos, "stop_trade", None)
        if existing and existing.orderStatus.status not in ("Filled", "Cancelled"):
            self.ib.cancelOrder(existing.order)
            self.ib.sleep(0.5)

        if use_market:
            order = MarketOrder("SELL", pos.remaining_shares)
        else:
            ticker = self.ib.reqMktData(pos.contract, "", False, False)
            self.ib.sleep(1)
            bid = ticker.bid if ticker.bid and ticker.bid > 0 else pos.entry_price
            safe_limit = round(bid * (1 - EXEC_SAFETY.max_slippage_pct / 100), 2)
            order = LimitOrder("SELL", pos.remaining_shares, safe_limit)
            self.ib.cancelMktData(pos.contract)

        trade = self.ib.placeOrder(pos.contract, order)
        trade_log.info(f"EXIT ALL {symbol} reason='{reason}' shares={pos.remaining_shares} market={use_market}")
        del self.positions[symbol]
        return trade

    # ------------------------------------------------------------------
    # 熔斷 (Halt) 偵測同復牌處理
    # ------------------------------------------------------------------
    def is_halted(self, contract) -> bool:
        """
        用 reqMktData 嘅 halted 欄位偵測 (tickType 49 - Halted)。
        0 = 冇熔斷, 1 = 一般熔斷, 2 = LULD Volatility Pause。
        """
        ticker = self.ib.reqMktData(contract, "49", False, False)
        self.ib.sleep(1)
        halted = getattr(ticker, "halted", 0)
        self.ib.cancelMktData(contract)
        return bool(halted and halted > 0)

    def monitor_and_manage_halts(self, symbol: str):
        """
        喺持倉監控 loop 入面定期call：
          1) 若偵測到熔斷 -> 取消現有市場止蝕/限價單（避免復牌一開圖即以爛價觸發滑價成交），
             記錄呢隻股票為 halted，暫停對佢落任何新單。
          2) 復牌後唔即刻落單，先觀察連續幾個 tick 確認報價穩定，
             同埋首幾秒波幅唔可以超過 post_halt_volatility_guard_pct，
             先重新掛返保護性止蝕單（或者按當時情況決定係咪直接離場）。
        """
        pos = self.positions.get(symbol)
        if not pos:
            return

        if self.is_halted(pos.contract):
            if symbol not in self.halted_symbols:
                log.warning(f"{symbol} 偵測到熔斷/波動性暫停，取消現有掛單，進入等待復牌模式。")
                self.halted_symbols.add(symbol)
                existing = getattr(pos, "stop_trade", None)
                if existing and existing.orderStatus.status not in ("Filled", "Cancelled"):
                    self.ib.cancelOrder(existing.order)
            return

        if symbol in self.halted_symbols:
            log.info(f"{symbol} 似乎已復牌，開始確認報價穩定性...")
            resumed_safely = self._confirm_resume(pos)
            self.halted_symbols.discard(symbol)
            if resumed_safely:
                # 復牌價可能大幅偏離原本嘅 stop，用新市價重新計一個合理止蝕
                ticker = self.ib.reqMktData(pos.contract, "", False, False)
                self.ib.sleep(1)
                last = ticker.last or pos.entry_price
                self.ib.cancelMktData(pos.contract)
                new_stop = min(pos.initial_stop, last * (1 - EXEC_SAFETY.max_slippage_pct / 100))
                self._place_protective_stop(pos, new_stop)
                trade_log.info(f"{symbol} 復牌後重新掛止蝕 @ {new_stop:.4f}")
            else:
                log.warning(f"{symbol} 復牌後波動過大或未能確認穩定，直接市價離場止蝕。")
                self.exit_all(symbol, reason="resume_volatility_guard", use_market=True)

    def _confirm_resume(self, pos: Position) -> bool:
        """復牌後連續攞幾個 tick，確認波幅喺安全範圍內先當復牌成功。"""
        prices = []
        deadline = time_mod.time() + EXEC_SAFETY.resume_max_wait_sec
        while len(prices) < EXEC_SAFETY.resume_confirmation_ticks:
            if time_mod.time() > deadline:
                return False
            ticker = self.ib.reqMktData(pos.contract, "", False, False)
            self.ib.sleep(EXEC_SAFETY.halt_poll_interval_sec)
            if ticker.last and ticker.last > 0:
                prices.append(ticker.last)
            self.ib.cancelMktData(pos.contract)

        price_range_pct = (max(prices) - min(prices)) / min(prices) * 100
        if price_range_pct > EXEC_SAFETY.post_halt_volatility_guard_pct:
            log.warning(f"{pos.symbol} 復牌後波幅 {price_range_pct:.1f}% 超過安全上限，唔即刻重新掛止蝕")
            return False
        return True
