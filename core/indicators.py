"""技術指標：VWAP、MACD、拉回(pullback)同 topping tail 偵測。"""
import numpy as np
import pandas as pd

from config.settings import STRATEGY


def compute_vwap(df: pd.DataFrame) -> pd.Series:
    """df 要有 high, low, close, volume 欄，按當日 session 由頭計起（df 已經係當日資料）。"""
    typical_price = (df["high"] + df["low"] + df["close"]) / 3
    cum_vol = df["volume"].cumsum()
    cum_vol_price = (typical_price * df["volume"]).cumsum()
    return cum_vol_price / cum_vol.replace(0, np.nan)


def compute_macd(close: pd.Series):
    ema_fast = close.ewm(span=STRATEGY.macd_fast, adjust=False).mean()
    ema_slow = close.ewm(span=STRATEGY.macd_slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=STRATEGY.macd_signal, adjust=False).mean()
    hist = macd_line - signal_line
    return macd_line, signal_line, hist


def macd_is_uptrend(macd_line: pd.Series, signal_line: pd.Series, hist: pd.Series) -> bool:
    """MACD 喺 0 軸之上或者剛穿越，而且 histogram 遞增（動能向上）。"""
    if len(macd_line) < 3:
        return False
    macd_rising = macd_line.iloc[-1] > macd_line.iloc[-2] > macd_line.iloc[-3]
    above_signal = macd_line.iloc[-1] > signal_line.iloc[-1]
    hist_rising = hist.iloc[-1] > hist.iloc[-2]
    return macd_rising and above_signal and hist_rising


def price_above_vwap(df: pd.DataFrame, vwap: pd.Series) -> bool:
    if len(df) == 0 or vwap.isna().all():
        return False
    last_price = df["close"].iloc[-1]
    last_vwap = vwap.iloc[-1]
    buffer = last_vwap * (STRATEGY.vwap_buffer_pct / 100)
    return last_price >= last_vwap + buffer


def detect_micro_pullback(df: pd.DataFrame) -> bool:
    """
    Micro pullback：喺升浪入面出現 2-4 支縮量細陰燭 / 窄幅整理，
    但冇跌穿前一段升浪嘅 50%，隨後有轉強跡象（呢個 function 只判斷「是否處於健康拉回」）。
    """
    n = STRATEGY.pullback_lookback_bars
    if len(df) < n + 2:
        return False

    recent = df.tail(n + 2).reset_index(drop=True)
    swing_low = recent["low"].iloc[0]
    swing_high = recent["high"].iloc[:3].max()
    if swing_high <= swing_low:
        return False

    move_range = swing_high - swing_low
    last_low = recent["low"].iloc[-1]
    retrace = (swing_high - last_low) / move_range

    volume_declining = recent["volume"].iloc[-3:].is_monotonic_decreasing
    within_retrace_limit = retrace <= STRATEGY.pullback_max_retrace_pct

    return within_retrace_limit and volume_declining


def detect_topping_tail(bar: pd.Series) -> bool:
    """單支 K 線上影線佔比過大 = 有人喺高位大手沽壓，動能可能已經衰減。"""
    full_range = bar["high"] - bar["low"]
    if full_range <= 0:
        return False
    body_top = max(bar["open"], bar["close"])
    upper_wick = bar["high"] - body_top
    wick_ratio = upper_wick / full_range
    return wick_ratio >= STRATEGY.topping_tail_wick_ratio


def momentum_is_decaying(df: pd.DataFrame) -> bool:
    """量能同波幅同時萎縮 = 動能衰減，配合 topping tail 使用嚟決定去或留。"""
    n = STRATEGY.momentum_decay_lookback
    if len(df) < n + 1:
        return False
    recent = df.tail(n)
    volume_decaying = recent["volume"].is_monotonic_decreasing
    ranges = (recent["high"] - recent["low"])
    range_decaying = ranges.is_monotonic_decreasing
    closes_stalling = recent["close"].diff().abs().mean() < df["close"].diff().abs().mean()
    return volume_decaying and (range_decaying or closes_stalling)
