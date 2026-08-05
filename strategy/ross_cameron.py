"""
Ross Cameron 風格動能策略核心邏輯：
  5 核心篩選（已喺 scanner 完成）+ 1分鐘圖 MACD/VWAP + 10秒圖同 Level2/Tape 輔助確認
  + micro pullback 進場 + 分批止盈 + topping tail / 動能衰減離場判斷
"""
import pandas as pd
from dataclasses import dataclass

from config.settings import STRATEGY
from core.indicators import (
    compute_vwap, compute_macd, macd_is_uptrend, price_above_vwap,
    detect_micro_pullback, detect_topping_tail, momentum_is_decaying,
)
from core.level2 import Level2Monitor
from utils.logger import get_logger

log = get_logger("strategy")


@dataclass
class EntrySignal:
    should_enter: bool
    reason: str
    entry_price: float | None = None
    stop_price: float | None = None
    reward_risk_ratio: float | None = None


@dataclass
class ExitSignal:
    should_exit: bool
    exit_type: str  # "stop" | "target1" | "target2" | "topping_tail" | "level2_weakness" | "none"
    reason: str = ""


class RossCameronStrategy:
    def __init__(self, symbol: str, level2: Level2Monitor, has_catalyst: bool):
        self.symbol = symbol
        self.level2 = level2
        self.has_catalyst = has_catalyst

    # ------------------------------------------------------------------
    def evaluate_entry(self, bars_1min: pd.DataFrame, bars_10s: pd.DataFrame) -> EntrySignal:
        if len(bars_1min) < STRATEGY.macd_slow + STRATEGY.macd_signal:
            return EntrySignal(False, "1分鐘K線資料唔夠計MACD")

        vwap = compute_vwap(bars_1min)
        macd_line, signal_line, hist = compute_macd(bars_1min["close"])

        if not macd_is_uptrend(macd_line, signal_line, hist):
            return EntrySignal(False, "MACD 未形成向上趨勢")

        if STRATEGY.require_price_above_vwap and not price_above_vwap(bars_1min, vwap):
            return EntrySignal(False, "股價未企穩喺 VWAP 之上")

        if not detect_micro_pullback(bars_1min):
            return EntrySignal(False, "未見健康嘅 micro pullback 形態")

        last_bar = bars_1min.iloc[-1]
        if detect_topping_tail(last_bar):
            return EntrySignal(False, "最新K線出現 topping tail，唔追高")

        # 用 10 秒圖確認短線動能未熄火
        if len(bars_10s) >= STRATEGY.momentum_decay_lookback + 1 and momentum_is_decaying(bars_10s):
            return EntrySignal(False, "10秒圖顯示短線動能衰減")

        # Level 2 / Tape 確認
        if not self.level2.confirms_entry_strength():
            return EntrySignal(False, "Level2/Tape 未確認買盤強度")

        entry_price = last_bar["close"]
        stop_price = self._compute_stop(bars_1min)
        risk = entry_price - stop_price
        if risk <= 0:
            return EntrySignal(False, "止蝕位計算異常（risk <= 0）")

        target_price = entry_price + risk * STRATEGY.target_reward_risk_ratio
        rr = (target_price - entry_price) / risk

        if rr < STRATEGY.min_reward_risk_ratio:
            return EntrySignal(False, f"盈虧比 {rr:.2f} 未達最低要求 {STRATEGY.min_reward_risk_ratio}")

        if not self.has_catalyst:
            log.info(f"{self.symbol} 冇偵測到明確新聞催化劑，仍然符合其餘技術條件，降低信心進場。")

        return EntrySignal(
            should_enter=True,
            reason="MACD向上 + VWAP之上 + micro pullback + Level2確認",
            entry_price=entry_price,
            stop_price=stop_price,
            reward_risk_ratio=rr,
        )

    def _compute_stop(self, bars_1min: pd.DataFrame) -> float:
        """止蝕位放喺 micro pullback 嘅低位之下一個 tick，唔係隨便用固定%。"""
        recent_low = bars_1min["low"].tail(STRATEGY.pullback_lookback_bars).min()
        return round(recent_low * 0.998, 2)

    # ------------------------------------------------------------------
    def evaluate_exit(self, bars_1min: pd.DataFrame, entry_price: float, stop_price: float,
                       remaining_pct: float, took_profit_1: bool, took_profit_2: bool) -> ExitSignal:
        if len(bars_1min) == 0:
            return ExitSignal(False, "none")

        last_bar = bars_1min.iloc[-1]
        current_price = last_bar["close"]
        risk = entry_price - stop_price
        if risk <= 0:
            risk = entry_price * 0.02

        r_multiple = (current_price - entry_price) / risk

        # 1) Topping tail + 動能衰減 => 優先考慮離場/唔再加倉
        if detect_topping_tail(last_bar) and momentum_is_decaying(bars_1min):
            return ExitSignal(True, "topping_tail", "出現 topping tail 同時動能衰減，落實止盈離場")

        # 2) Level2 / Tape 轉弱訊號
        if self.level2.should_exit_on_weakness():
            return ExitSignal(True, "level2_weakness", "Level2/Tape 顯示買盤流動性衰減同賣壓轉強")

        # 3) 分批止盈點
        if not took_profit_1 and r_multiple >= STRATEGY.profit_take_1_rr:
            return ExitSignal(True, "target1", f"到達第一止盈點 {STRATEGY.profit_take_1_rr}R")

        if took_profit_1 and not took_profit_2 and r_multiple >= STRATEGY.profit_take_2_rr:
            return ExitSignal(True, "target2", f"到達第二止盈點 {STRATEGY.profit_take_2_rr}R")

        return ExitSignal(False, "none")

    def compute_trailing_stop(self, bars_1min: pd.DataFrame, current_stop: float) -> float:
        """尾段用近期低位/VWAP 嚟 trail，只可以向上調，唔可以向下調。"""
        vwap = compute_vwap(bars_1min)
        recent_low = bars_1min["low"].tail(3).min()
        candidate = max(recent_low, vwap.iloc[-1]) * (1 - STRATEGY.trailing_stop_pct / 100)
        return max(current_stop, round(candidate, 2))
