"""盤前Gap動量交易策略 - 用於回測和實盤"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional
from datetime import datetime

from core.indicators import compute_macd, compute_vwap
from config.settings import STRATEGY as STRATEGY_PARAMS


class GapMomentumStrategy:
    """
    核心策略邏輯：
    1. 檢測盤前Gap >= 5%
    2. 確認成交量爆升 (>= 2x 平均)
    3. 突破點進場 (MACD + VWAP確認)
    4. 多層止盈 (TP1/TP2/TP3) + 止損
    """

    def __init__(self):
        pass

    def generate_signal(self, df: pd.DataFrame, current_idx: int) -> Optional[Dict[str, Any]]:
        """
        根據當前K線生成交易信號

        Args:
            df: OHLCV DataFrame，列: o/h/l/c/v
            current_idx: 當前K線索引

        Returns:
            {
                'action': 'buy' / 'sell' / 'hold' / 'exit',
                'entry_price': float,
                'tp1/tp2/tp3': float,
                'stop_loss': float,
                ...
            }
        """

        if current_idx < 50:  # 需要足夠歷史數據計算指標
            return None

        # 1. 檢查MACD信號
        macd_signal = self._check_macd(df, current_idx)
        if not macd_signal['bullish']:
            return None

        # 2. 檢查VWAP確認
        vwap_signal = self._check_vwap(df, current_idx)
        if not vwap_signal['above_vwap']:
            return None

        # 3. 檢查微觀拉回結構
        pullback_signal = self._check_pullback(df, current_idx)
        if not pullback_signal['confirmed']:
            return None

        # 4. 檢查成交量
        volume_signal = self._check_volume(df, current_idx)
        if not volume_signal['hot']:
            return None

        # 5. 計算進場價和止損
        entry_price = df.iloc[current_idx]['c']  # 收盤價作為參考
        support = pullback_signal['recent_low']
        stop_loss = support - (support * 0.02)  # 支撐位下方2%

        # 6. 計算止盈目標 (1:2 和 1:3 風險回報比)
        risk = entry_price - stop_loss
        tp1 = entry_price + (risk * 1.0)  # 1R 止盈
        tp2 = entry_price + (risk * 2.0)  # 2R 止盈
        tp3 = entry_price + (risk * 3.0)  # 3R 止盈

        return {
            'action': 'buy',
            'entry_price': entry_price,
            'tp1': tp1,
            'tp2': tp2,
            'tp3': tp3,
            'stop_loss': stop_loss,
            'confidence': min(100, (
                macd_signal.get('confidence', 0) +
                vwap_signal.get('confidence', 0) +
                pullback_signal.get('confidence', 0) +
                volume_signal.get('confidence', 0)
            ) / 4),
        }

    def _check_macd(self, df: pd.DataFrame, idx: int) -> Dict[str, Any]:
        """檢查MACD動能"""
        if idx < STRATEGY_PARAMS.macd_slow + 10:
            return {'bullish': False, 'confidence': 0}

        # 計算MACD
        close_series = pd.Series(df['c'].iloc[:idx+1].values)
        macd_line, signal_line, histogram = compute_macd(close_series)

        if len(macd_line) < 2:
            return {'bullish': False, 'confidence': 0}

        # 檢查MACD金叉 (線上穿信號線)
        macd_cross = (
            macd_line.iloc[-2] < signal_line.iloc[-2] and
            macd_line.iloc[-1] > signal_line.iloc[-1]
        )

        # 檢查MACD柱狀圖增長
        histogram_growing = (
            len(histogram) >= 2 and
            histogram.iloc[-1] > histogram.iloc[-2]
        )

        bullish = macd_cross or histogram_growing
        confidence = 40 if macd_cross else (20 if histogram_growing else 0)

        return {
            'bullish': bullish,
            'confidence': confidence,
            'macd_line': float(macd_line.iloc[-1]),
            'signal_line': float(signal_line.iloc[-1]),
        }

    def _check_vwap(self, df: pd.DataFrame, idx: int) -> Dict[str, Any]:
        """檢查VWAP確認"""
        if idx < 20:
            return {'above_vwap': False, 'confidence': 0}

        # 計算VWAP
        df_slice = df.iloc[:idx+1].copy()
        df_slice = df_slice.rename(columns={'o': 'open', 'h': 'high', 'l': 'low', 'c': 'close', 'v': 'volume'})
        vwap_values = compute_vwap(df_slice)

        if len(vwap_values) == 0:
            return {'above_vwap': False, 'confidence': 0}

        current_price = df.iloc[idx]['c']
        current_vwap = float(vwap_values.iloc[-1])

        # 檢查價格在VWAP上方
        above_vwap = current_price > current_vwap * (1 + STRATEGY_PARAMS.vwap_buffer_pct / 100)
        confidence = 30 if above_vwap else 0

        return {
            'above_vwap': above_vwap,
            'confidence': confidence,
            'vwap': current_vwap,
            'price_to_vwap': (current_price - current_vwap) / current_vwap * 100,
        }

    def _check_pullback(self, df: pd.DataFrame, idx: int) -> Dict[str, Any]:
        """檢查微觀拉回結構"""
        if idx < STRATEGY_PARAMS.pullback_lookback_bars + 5:
            return {'confirmed': False, 'confidence': 0}

        lookback = STRATEGY_PARAMS.pullback_lookback_bars
        recent_high = df.iloc[idx - lookback:idx]['h'].max()
        recent_low = df.iloc[idx - lookback:idx]['l'].min()
        range_size = recent_high - recent_low

        current_price = df.iloc[idx]['c']

        # 檢查價格接近最高點 (未超過50%回撤)
        retrace = (recent_high - current_price) / range_size if range_size > 0 else 1.0
        valid_pullback = retrace <= STRATEGY_PARAMS.pullback_max_retrace_pct

        confidence = 30 if valid_pullback else 0

        return {
            'confirmed': valid_pullback,
            'confidence': confidence,
            'recent_high': recent_high,
            'recent_low': recent_low,
            'retrace_pct': retrace * 100 if range_size > 0 else 0,
        }

    def _check_volume(self, df: pd.DataFrame, idx: int) -> Dict[str, Any]:
        """檢查成交量確認"""
        if idx < 20:
            return {'hot': False, 'confidence': 0}

        avg_volume = df.iloc[idx-20:idx]['v'].mean()
        current_volume = df.iloc[idx]['v']
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0

        hot = volume_ratio >= 2.0
        confidence = min(50, int(volume_ratio * 20)) if hot else 0

        return {
            'hot': hot,
            'confidence': confidence,
            'volume_ratio': volume_ratio,
            'current_volume': current_volume,
            'avg_volume': avg_volume,
        }


def create_backtest_signal_function(strategy: GapMomentumStrategy):
    """
    為回測創建信號函數

    Usage:
        strategy = GapMomentumStrategy()
        signal_func = create_backtest_signal_function(strategy)
        backtester.run(symbol, start_date, end_date, signal_func)
    """
    def signal_func(df: pd.DataFrame, idx: int) -> Optional[Dict[str, Any]]:
        return strategy.generate_signal(df, idx)

    return signal_func
