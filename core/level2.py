"""
整合 Level 2 (market depth) 同 Time & Sales，判斷買賣盤流動性係咪衰減，
用嚟輔助進場/離場決定（唔係取代 K 線，係加多一層確認）。

需要 IBKR 帳戶有 Level 2 / 深度數據權限 (US Equity - NYSE/ARCA/BATS L2 或 NASDAQ TotalView)。
"""
from collections import deque
from dataclasses import dataclass, field
from time import time

from config.settings import LEVEL2
from utils.logger import get_logger

log = get_logger("level2")


@dataclass
class BookSnapshot:
    bid_levels: list  # [(price, size), ...] 由最優到最差
    ask_levels: list
    timestamp: float = field(default_factory=time)

    @property
    def total_bid_size(self) -> int:
        return sum(size for _, size in self.bid_levels)

    @property
    def total_ask_size(self) -> int:
        return sum(size for _, size in self.ask_levels)

    @property
    def imbalance(self) -> float:
        """> 0 代表買盤壓過賣盤（睇好），< 0 代表賣壓大。範圍 -1 ~ 1。"""
        total = self.total_bid_size + self.total_ask_size
        if total == 0:
            return 0.0
        return (self.total_bid_size - self.total_ask_size) / total


@dataclass
class TapePrint:
    price: float
    size: int
    timestamp: float = field(default_factory=time)
    at_ask: bool = False   # True = 主動買盤 (aggressor buy)，False = 主動沽盤


class Level2Monitor:
    """
    每隻股一個 instance，持續累積 depth snapshot 同 tape prints，
    對外提供「流動性衰減」「買賣盤失衡」「主動買賣速度」等訊號。
    """

    def __init__(self, symbol: str):
        self.symbol = symbol
        self.snapshots: deque[BookSnapshot] = deque(maxlen=200)
        self.tape: deque[TapePrint] = deque(maxlen=500)
        self._peak_bid_size = 0

    def on_depth_update(self, bid_levels, ask_levels):
        snap = BookSnapshot(bid_levels=bid_levels, ask_levels=ask_levels)
        self.snapshots.append(snap)
        self._peak_bid_size = max(self._peak_bid_size, snap.total_bid_size)

    def on_tape_print(self, price: float, size: int, at_ask: bool):
        self.tape.append(TapePrint(price=price, size=size, at_ask=at_ask))

    # ------------------------------------------------------------------
    # 訊號
    # ------------------------------------------------------------------
    def bid_liquidity_decaying(self) -> bool:
        """買盤總量由高峰跌落到某個比例之下 = 支持力量正在消失，追貨/持倉要小心。"""
        if not self.snapshots or self._peak_bid_size == 0:
            return False
        current = self.snapshots[-1].total_bid_size
        ratio = current / self._peak_bid_size
        decaying = ratio < LEVEL2.liquidity_decay_ratio
        if decaying:
            log.info(f"{self.symbol} 買盤流動性衰減: 現在 {current} / 高峰 {self._peak_bid_size} = {ratio:.2f}")
        return decaying

    def ask_side_thinning_fast(self) -> bool:
        """賣盤（ask）頭幾檔嘅貨迅速被食走 = 買方主動性強，可能係好進場時機。"""
        if len(self.snapshots) < 2:
            return False
        prev = self.snapshots[-2]
        cur = self.snapshots[-1]
        n = LEVEL2.ask_pull_alert_levels
        prev_top = sum(size for _, size in prev.ask_levels[:n])
        cur_top = sum(size for _, size in cur.ask_levels[:n])
        if prev_top == 0:
            return False
        return (prev_top - cur_top) / prev_top > 0.5

    def order_book_imbalance(self) -> float:
        if not self.snapshots:
            return 0.0
        return self.snapshots[-1].imbalance

    def tape_buy_sell_ratio(self) -> float:
        """最近 tape_speed_window_sec 秒入面，主動買 vs 主動沽嘅成交量比例。"""
        now = time()
        window = [t for t in self.tape if now - t.timestamp <= LEVEL2.tape_speed_window_sec]
        if not window:
            return 1.0
        buy_vol = sum(t.size for t in window if t.at_ask)
        sell_vol = sum(t.size for t in window if not t.at_ask)
        if sell_vol == 0:
            return float("inf") if buy_vol > 0 else 1.0
        return buy_vol / sell_vol

    def tape_speed(self) -> int:
        """最近時間窗入面嘅成交筆數，用嚟感受盤口熱度/降溫。"""
        now = time()
        return sum(1 for t in self.tape if now - t.timestamp <= LEVEL2.tape_speed_window_sec)

    def should_exit_on_weakness(self) -> bool:
        """
        綜合訊號：買盤衰減 + 賣壓轉強 (imbalance < 0) + tape 轉為沽盤主導，
        三個訊號同時出現先建議離場，避免單一訊號誤判。
        """
        decaying = self.bid_liquidity_decaying()
        imbalance_negative = self.order_book_imbalance() < -0.15
        tape_selling = self.tape_buy_sell_ratio() < 0.7
        signals = sum([decaying, imbalance_negative, tape_selling])
        if signals >= 2:
            log.warning(
                f"{self.symbol} Level2/Tape 轉弱訊號 ({signals}/3): "
                f"decaying={decaying}, imbalance={self.order_book_imbalance():.2f}, "
                f"buy/sell={self.tape_buy_sell_ratio():.2f}"
            )
            return True
        return False

    def confirms_entry_strength(self) -> bool:
        """進場前確認：買盤有支撐、ask 被食走快、tape 買盤主導。"""
        imbalance_positive = self.order_book_imbalance() > 0.1
        ask_thinning = self.ask_side_thinning_fast()
        tape_buying = self.tape_buy_sell_ratio() > 1.3
        signals = sum([imbalance_positive, ask_thinning, tape_buying])
        return signals >= 2
