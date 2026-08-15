"""Simple backtest engine for Ross Cameron strategy."""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import List, Dict
import json


@dataclass
class Trade:
    """單筆交易記錄"""
    symbol: str
    entry_date: datetime
    entry_price: float
    entry_bar: int  # K線索引
    quantity: int
    stop_price: float
    tp1_price: float
    tp2_price: float

    exit_date: datetime = None
    exit_price: float = 0.0
    exit_type: str = None  # 'tp1', 'tp2', 'runner', 'stop', 'close'

    def pnl(self) -> float:
        """交易淨利潤（$）"""
        if self.exit_price == 0:
            return 0
        return (self.exit_price - self.entry_price) * self.quantity

    def pnl_pct(self) -> float:
        """交易收益率（%）"""
        if self.entry_price == 0:
            return 0
        return (self.exit_price - self.entry_price) / self.entry_price * 100 if self.exit_price > 0 else 0


class SimpleBacktester:
    def __init__(self,
                 initial_cash: float = 10000,
                 risk_per_trade: float = 100,  # 每筆風險 $100
                 max_daily_trades: int = 12,
                 gap_threshold: float = 20.0,
                 float_max: float = 30e6,
                 rvol_min: float = 5.0):
        self.initial_cash = initial_cash
        self.cash = initial_cash
        self.risk_per_trade = risk_per_trade
        self.max_daily_trades = max_daily_trades

        # 策略參數
        self.gap_threshold = gap_threshold
        self.float_max = float_max
        self.rvol_min = rvol_min

        self.trades: List[Trade] = []
        self.daily_pnl: Dict[str, float] = {}
        self.positions: Dict[str, Trade] = {}  # 當前持倉

    def run(self, symbols_by_date: Dict[str, List[str]],
            data_loader, all_dates: List[str]) -> Dict:
        """
        逐日回測

        Args:
            symbols_by_date: {日期: [股票列表]}
            data_loader: DataLoader 實例
            all_dates: 所有交易日期列表

        Returns:
            績效統計字典
        """
        print('\n【回測開始】')
        print(f'  初始資金: ${self.initial_cash:.2f}')
        print(f'  風險參數: 每筆 ${self.risk_per_trade:.2f}')
        print(f'  策略參數:')
        print(f'    - Gap Up ≥ {self.gap_threshold}%')
        print(f'    - Float ≤ ${self.float_max/1e6:.0f}M')
        print(f'    - RVol ≥ {self.rvol_min}x')

        daily_trade_count = 0
        last_date = None

        for current_date_str in all_dates:
            current_date = pd.to_datetime(current_date_str)

            # 每天重置交易計數
            if last_date is None or (current_date.date() != last_date.date()):
                daily_trade_count = 0
                self.daily_pnl[current_date_str] = 0

            last_date = current_date

            # 檢查當日是否有候選股
            symbols = symbols_by_date.get(current_date_str, [])
            if not symbols:
                continue

            print(f'\n[{current_date_str}] 候選股: {symbols}')

            # 逐個股票處理
            for symbol in symbols:
                if daily_trade_count >= self.max_daily_trades:
                    break

                # 載入該股票數據
                try:
                    # 簡單起見，載入整個月份的數據
                    month_start = (current_date - timedelta(days=30)).strftime('%Y-%m-%d')
                    bars = data_loader.get_daily_bars(symbol, month_start, current_date_str)

                    if bars.empty or len(bars) < 2:
                        continue

                    # 簡化邏輯：假設今天是 gap up 日
                    today_idx = len(bars) - 1
                    today_bar = bars.iloc[today_idx]
                    prev_bar = bars.iloc[today_idx - 1]

                    # 計算 gap
                    prev_close = prev_bar['Close']
                    today_open = today_bar['Open']
                    gap_pct = (today_open - prev_close) / prev_close * 100 if prev_close > 0 else 0

                    # 過濾：gap up ≥ threshold
                    if gap_pct < self.gap_threshold:
                        continue

                    # 簡單的進場邏輯：假設開市時進場
                    entry_price = today_open
                    entry_high = today_bar['High']

                    # 止蝕：盤中低點 - $0.05
                    stop_price = today_bar['Low'] - 0.05

                    # 計算風險
                    risk = entry_price - stop_price
                    if risk <= 0:
                        continue

                    # 計算數量（風險固定）
                    qty = int(self.risk_per_trade / risk)
                    if qty <= 0:
                        continue

                    # 計算止盈
                    tp1_price = entry_price + risk * 2.0  # +2R
                    tp2_price = entry_price + risk * 3.0  # +3R

                    # 簡化止盈邏輯：假設當天能達到 tp1 或 stop
                    # 實際應該看盤中高低點
                    today_high = today_bar['High']
                    today_low = today_bar['Low']
                    today_close = today_bar['Close']

                    exit_price = entry_price
                    exit_type = 'close'

                    if today_high >= tp2_price:
                        exit_price = tp2_price
                        exit_type = 'tp2'
                    elif today_high >= tp1_price:
                        exit_price = tp1_price
                        exit_type = 'tp1'
                    elif today_low <= stop_price:
                        exit_price = stop_price
                        exit_type = 'stop'
                    else:
                        exit_price = today_close  # 沒觸發，用收盤價平倉

                    # 建立交易記錄
                    trade = Trade(
                        symbol=symbol,
                        entry_date=current_date,
                        entry_price=entry_price,
                        entry_bar=today_idx,
                        quantity=qty,
                        stop_price=stop_price,
                        tp1_price=tp1_price,
                        tp2_price=tp2_price,
                        exit_date=current_date,
                        exit_price=exit_price,
                        exit_type=exit_type,
                    )

                    pnl = trade.pnl()
                    pnl_pct = trade.pnl_pct()

                    # 更新資金
                    self.cash += pnl
                    self.daily_pnl[current_date_str] += pnl

                    # 記錄交易
                    self.trades.append(trade)
                    daily_trade_count += 1

                    # 打印
                    status = '✅' if pnl > 0 else '❌'
                    print(
                        f'  {status} {symbol}: entry ${entry_price:.2f} → exit ${exit_price:.2f} '
                        f'({exit_type}) | qty={qty} | pnl=${pnl:.2f} ({pnl_pct:+.1f}%) | '
                        f'剩餘資金: ${self.cash:.2f}'
                    )

                except Exception as e:
                    print(f'  ⚠️ {symbol} 處理出錯: {e}')
                    continue

        # 計算績效指標
        return self._calculate_metrics()

    def _calculate_metrics(self) -> Dict:
        """計算績效指標"""
        if not self.trades:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0,
                'total_pnl': 0,
                'total_pnl_pct': 0,
                'avg_win': 0,
                'avg_loss': 0,
                'max_loss': 0,
                'profit_factor': 0,
                'sharpe_ratio': 0,
                'max_drawdown': 0,
                'final_nav': self.cash,
            }

        wins = [t for t in self.trades if t.pnl() > 0]
        losses = [t for t in self.trades if t.pnl() < 0]

        total_pnl = sum(t.pnl() for t in self.trades)
        total_pnl_pct = (total_pnl / self.initial_cash) * 100

        avg_win = np.mean([t.pnl() for t in wins]) if wins else 0
        avg_loss = np.mean([t.pnl() for t in losses]) if losses else 0
        max_loss = min([t.pnl() for t in losses]) if losses else 0

        profit_factor = abs(sum(t.pnl() for t in wins) / sum(t.pnl() for t in losses)) \
            if losses else float('inf')

        # 計算最大回撤
        nav_curve = [self.initial_cash]
        for trade in self.trades:
            nav_curve.append(nav_curve[-1] + trade.pnl())
        peak = nav_curve[0]
        max_dd = 0
        for nav in nav_curve:
            if nav > peak:
                peak = nav
            dd = (peak - nav) / peak
            if dd > max_dd:
                max_dd = dd

        # Sharpe 比率（簡化：用日收益率）
        daily_returns = list(self.daily_pnl.values())
        if len(daily_returns) > 1:
            sharpe = np.mean(daily_returns) / (np.std(daily_returns) + 1e-6) * np.sqrt(252)
        else:
            sharpe = 0

        return {
            'total_trades': len(self.trades),
            'winning_trades': len(wins),
            'losing_trades': len(losses),
            'win_rate': (len(wins) / len(self.trades) * 100) if self.trades else 0,
            'total_pnl': total_pnl,
            'total_pnl_pct': total_pnl_pct,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'max_loss': max_loss,
            'profit_factor': profit_factor,
            'sharpe_ratio': sharpe,
            'max_drawdown': max_dd * 100,
            'final_nav': self.cash,
        }
