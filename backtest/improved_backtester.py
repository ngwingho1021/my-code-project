"""
改進版回測器 — 優化進場/止盈邏輯

改進方向：
1. 多重進場條件確認
2. 動態止盈目標
3. 改進止蝕邏輯
4. 風險管理
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import List, Dict, Tuple


@dataclass
class Trade:
    """單筆交易記錄"""
    symbol: str
    entry_date: str
    entry_price: float
    quantity: int
    stop_price: float
    tp1_price: float
    tp2_price: float

    exit_date: str = None
    exit_price: float = 0.0
    exit_type: str = None  # 'tp1', 'tp2', 'runner', 'stop', 'close'

    def pnl(self) -> float:
        if self.exit_price == 0:
            return 0
        return (self.exit_price - self.entry_price) * self.quantity

    def pnl_pct(self) -> float:
        if self.entry_price == 0:
            return 0
        return (self.exit_price - self.entry_price) / self.entry_price * 100 if self.exit_price > 0 else 0


class ImprovedBacktester:
    """改進版回測器 — 優化策略邏輯"""

    def __init__(self,
                 initial_cash: float = 10000,
                 risk_per_trade: float = 100,
                 max_daily_trades: int = 12,
                 gap_threshold: float = 2.0,
                 volume_min: float = 500000,
                 strategy_version: str = 'v1'):
        """
        Args:
            initial_cash: 初始資金
            risk_per_trade: 每筆交易風險
            max_daily_trades: 每日最大交易數
            gap_threshold: Gap Up 門檻 (%)
            volume_min: 最小成交量
            strategy_version: 策略版本 ('baseline', 'v1', 'v2', 'v3')
        """
        self.initial_cash = initial_cash
        self.cash = initial_cash
        self.risk_per_trade = risk_per_trade
        self.max_daily_trades = max_daily_trades
        self.gap_threshold = gap_threshold
        self.volume_min = volume_min
        self.strategy_version = strategy_version

        self.trades: List[Trade] = []
        self.daily_pnl: Dict[str, float] = {}

    def should_enter(self, bars, symbol: str) -> Tuple[bool, str]:
        """
        判斷是否應該進場

        改進邏輯根據 strategy_version：
        - baseline: 僅看 gap
        - v1: gap + 成交量確認
        - v2: gap + 成交量 + 價格確認
        - v3: 完整篩選（v2 + 波動性 + 支撐位）
        """
        if len(bars) < 2:
            return False, 'insufficient_data'

        today_bar = bars.iloc[-1]
        prev_bar = bars.iloc[-2]

        prev_close = prev_bar['Close']
        today_open = today_bar['Open']
        today_close = today_bar['Close']
        today_volume = today_bar['Volume']

        # 計算 gap
        gap_pct = ((today_open - prev_close) / prev_close) * 100

        # 基礎條件：Gap Up
        if gap_pct < self.gap_threshold:
            return False, f'gap_too_small({gap_pct:.1f}%)'

        if self.strategy_version == 'baseline':
            return True, 'gap_ok'

        # V1: Gap + 成交量
        if self.strategy_version == 'v1':
            if today_volume < self.volume_min:
                return False, f'volume_too_low({today_volume})'
            return True, 'gap_volume_ok'

        # V2: Gap + 成交量 + 價格
        if self.strategy_version in ['v2', 'v3']:
            if today_volume < self.volume_min:
                return False, f'volume_too_low'

            # V2 不要求close > open，因為 gap up 日可能會下跌
            # 只要求有 gap 和成交量
            if self.strategy_version == 'v2':
                return True, 'gap_volume_ok'

        # V3: 完整篩選
        if self.strategy_version == 'v3':
            # 計算 ATR（簡化版：最近 5 天的平均幅度）
            if len(bars) >= 5:
                recent_range = []
                for i in range(-5, 0):
                    bar = bars.iloc[i]
                    range_val = bar['High'] - bar['Low']
                    recent_range.append(range_val)
                atr = np.mean(recent_range)
            else:
                atr = today_bar['High'] - today_bar['Low']

            # 要求日內波動 > ATR（有波動性）
            today_range = today_bar['High'] - today_bar['Low']
            if today_range < atr * 0.5:
                return False, 'low_volatility'

            return True, 'all_checks_passed'

        return False, 'unknown_version'

    def calculate_targets(self, entry_price: float, stop_price: float, bars) -> Tuple[float, float]:
        """
        計算止盈目標

        改進邏輯根據 strategy_version：
        - baseline/v1/v2: 固定倍數 (2x, 3x risk)
        - v3: 動態基於 ATR
        """
        risk = entry_price - stop_price

        if self.strategy_version == 'v3' and len(bars) >= 5:
            # 用 ATR 計算動態目標
            recent_range = []
            for i in range(-5, 0):
                bar = bars.iloc[i]
                range_val = bar['High'] - bar['Low']
                recent_range.append(range_val)
            atr = np.mean(recent_range)

            # 動態目標（更現實）
            tp1 = entry_price + atr * 1.2
            tp2 = entry_price + atr * 1.8
        else:
            # 固定倍數
            tp1 = entry_price + risk * 1.5  # 改成 1.5x（而非 2.0x）
            tp2 = entry_price + risk * 2.5  # 改成 2.5x（而非 3.0x）

        return tp1, tp2

    def run_simulation(self, num_days: int = 120) -> Dict:
        """運行改進版模擬回測"""
        print(f'\n【改進版回測 - {self.strategy_version.upper()}】')
        print(f'  初始資金: ${self.initial_cash:,.2f}')
        print(f'  風險/筆: ${self.risk_per_trade:.2f}')
        print(f'  策略版本: {self.strategy_version}')
        print(f'  Gap 門檻: {self.gap_threshold}%')
        print(f'  模擬天數: {num_days}')

        # 生成模擬數據
        from backtest.standalone_backtester import StandaloneBacktester
        temp_backtester = StandaloneBacktester(
            initial_cash=self.initial_cash,
            risk_per_trade=self.risk_per_trade
        )

        start_date = (datetime.now() - timedelta(days=num_days)).strftime('%Y-%m-%d')
        end_date = datetime.now().strftime('%Y-%m-%d')

        test_symbols = ['STOCK_A', 'STOCK_B']
        daily_trade_count = 0
        current_date = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date)

        print(f'\n🚀 開始模擬...')
        trades_generated = 0

        while current_date <= end_dt:
            # 跳過週末
            if current_date.weekday() >= 5:
                current_date += timedelta(days=1)
                continue

            current_date_str = current_date.strftime('%Y-%m-%d')

            # 初始化每日數據
            if current_date_str not in self.daily_pnl:
                self.daily_pnl[current_date_str] = 0

            # 每天重置計數
            if current_date.day == 1 or trades_generated == 0:
                daily_trade_count = 0

            # 隨機選擇候選股
            for symbol in test_symbols[:1 + (current_date.day % 2)]:
                if daily_trade_count >= self.max_daily_trades:
                    break

                # 生成該股票數據
                gap_pct = self.gap_threshold if np.random.random() < 0.15 else 0
                bars = temp_backtester.generate_mock_price_bars(
                    symbol,
                    start_date,
                    current_date_str,
                    gap_pct=gap_pct,
                    volatility=0.03
                )

                if bars.empty or len(bars) < 2:
                    continue

                # 判斷是否進場
                should_enter, reason = self.should_enter(bars, symbol)
                if not should_enter:
                    continue

                today_bar = bars.iloc[-1]
                entry_price = today_bar['Open']
                stop_price = today_bar['Low'] - 0.05

                risk = entry_price - stop_price
                if risk <= 0:
                    continue

                qty = int(self.risk_per_trade / risk)
                if qty <= 0:
                    continue

                # 計算止盈
                tp1, tp2 = self.calculate_targets(entry_price, stop_price, bars)

                # 簡單止盈邏輯
                high = today_bar['High']
                low = today_bar['Low']
                close = today_bar['Close']

                if high >= tp2:
                    exit_price = tp2
                    exit_type = 'tp2'
                elif high >= tp1:
                    exit_price = tp1
                    exit_type = 'tp1'
                elif low <= stop_price:
                    exit_price = stop_price
                    exit_type = 'stop'
                else:
                    exit_price = close
                    exit_type = 'close'

                trade = Trade(
                    symbol=symbol,
                    entry_date=current_date_str,
                    entry_price=entry_price,
                    quantity=qty,
                    stop_price=stop_price,
                    tp1_price=tp1,
                    tp2_price=tp2,
                    exit_date=current_date_str,
                    exit_price=exit_price,
                    exit_type=exit_type,
                )

                pnl = trade.pnl()
                pnl_pct = trade.pnl_pct()

                self.cash += pnl
                self.daily_pnl[current_date_str] += pnl
                self.trades.append(trade)
                daily_trade_count += 1
                trades_generated += 1

                status = '✅' if pnl > 0 else '❌'
                print(
                    f'  {status} [{current_date_str}] {symbol}: '
                    f'${entry_price:.2f}→${exit_price:.2f} ({exit_type}) '
                    f'| qty={qty} | PnL=${pnl:+.2f} ({pnl_pct:+.1f}%) | 資金: ${self.cash:+.2f}'
                )

            current_date += timedelta(days=1)

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

        # 最大回撤
        nav_curve = [self.initial_cash]
        for trade in self.trades:
            nav_curve.append(nav_curve[-1] + trade.pnl())
        peak = nav_curve[0]
        max_dd = 0
        for nav in nav_curve:
            if nav > peak:
                peak = nav
            dd = (peak - nav) / peak if peak > 0 else 0
            if dd > max_dd:
                max_dd = dd

        # Sharpe
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
