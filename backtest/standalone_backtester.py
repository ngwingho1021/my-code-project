"""
獨立版回測引擎 — 不依賴外部網絡
用模擬數據進行回測，用戶可自己調整參數驗證策略邏輯
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
    exit_type: str = None  # 'tp1', 'tp2', 'runner', 'stop'

    def pnl(self) -> float:
        if self.exit_price == 0:
            return 0
        return (self.exit_price - self.entry_price) * self.quantity

    def pnl_pct(self) -> float:
        if self.entry_price == 0:
            return 0
        return (self.exit_price - self.entry_price) / self.entry_price * 100 if self.exit_price > 0 else 0


class StandaloneBacktester:
    """獨立版回測器 - 模擬數據"""

    def __init__(self,
                 initial_cash: float = 10000,
                 risk_per_trade: float = 100,
                 max_daily_trades: int = 12,
                 gap_threshold: float = 20.0,
                 float_max: float = 30e6,
                 rvol_min: float = 5.0):
        self.initial_cash = initial_cash
        self.cash = initial_cash
        self.risk_per_trade = risk_per_trade
        self.max_daily_trades = max_daily_trades

        self.gap_threshold = gap_threshold
        self.float_max = float_max
        self.rvol_min = rvol_min

        self.trades: List[Trade] = []
        self.daily_pnl: Dict[str, float] = {}

    def generate_mock_price_bars(self,
                                 symbol: str,
                                 start_date: str,
                                 end_date: str,
                                 gap_pct: float = 0,
                                 volatility: float = 0.03) -> pd.DataFrame:
        """
        生成更逼真的模擬股票價格數據

        改進點：
        - Gap 動作確實實現
        - 更真實的日內波動（高和低）
        - 成交量與價格變動相關
        - 偶爾極端波動（模擬低流動性）
        - 可能的反向走勢

        Args:
            symbol: 股票代號
            start_date: 開始日期
            end_date: 結束日期
            gap_pct: Gap Up 百分比 (%)
            volatility: 波動率

        Returns:
            包含 OHLCV 的 DataFrame
        """
        start = pd.to_datetime(start_date)
        end = pd.to_datetime(end_date)

        dates = pd.bdate_range(start=start, end=end)
        n_bars = len(dates)

        # 決定性隨機種子
        np.random.seed(hash(symbol + start_date) % 2**32)

        # 基礎價格（$5-20）
        base_price = 10 + np.random.random() * 10

        closes = [base_price]
        for i in range(n_bars):
            # 動量趨勢 + 隨機波動
            momentum = np.random.normal(0, 0.01)  # 小概率有趨勢
            volatility_mult = 1 + np.random.normal(0, volatility)
            new_close = closes[-1] * (1 + momentum + np.random.normal(0, volatility_mult * 0.02))
            closes.append(max(new_close, 0.5))

        closes = closes[1:]

        # 構建 OHLCV
        data = []
        for i, date in enumerate(dates):
            close = closes[i]

            # ===== Open 價格 =====
            if i == 0 and gap_pct > 0:
                # Gap up 案例
                open_price = close * (1 - gap_pct / 100)
            else:
                # 正常情況：open 接近昨日 close（±1%）
                prev_close = closes[i-1] if i > 0 else close
                open_price = prev_close * (1 + np.random.normal(0, 0.01))

            # ===== High / Low（更真實的日內波動）=====
            # 波動幅度取決於今日是否是 gap up
            if i == 0 and gap_pct > 0:
                # Gap up 日通常有較大的日內波動
                intraday_volatility = abs(np.random.normal(0, 0.04))
            else:
                # 普通日
                intraday_volatility = abs(np.random.normal(0, 0.02))

            # High 和 Low 基於 Open 和 Close
            price_range = [open_price, close]
            base_high = max(price_range)
            base_low = min(price_range)

            high = base_high * (1 + intraday_volatility)
            low = base_low * (1 - intraday_volatility)

            # 偶爾出現極端波動（模擬低流動性或突發消息）
            if np.random.random() < 0.1:  # 10% 機率
                extreme_move = np.random.normal(0, 0.08)
                if extreme_move > 0:
                    high *= (1 + abs(extreme_move))
                else:
                    low *= (1 + extreme_move)

            # ===== Volume =====
            # 成交量與波動性相關
            base_volume = 500000 + np.random.randint(-100000, 500000)
            # Gap up 日通常成交量大
            if i == 0 and gap_pct > 0:
                volume = int(base_volume * (1 + gap_pct / 20))
            else:
                volume = int(base_volume)

            # 確保 High > Low
            high = max(high, low * 1.001)

            data.append({
                'Date': date,
                'Open': open_price,
                'High': high,
                'Low': low,
                'Close': close,
                'Volume': max(volume, 10000),  # 最小成交量
            })

        df = pd.DataFrame(data)
        df.set_index('Date', inplace=True)
        return df

    def run_simulation(self, num_days: int = 60) -> Dict:
        """
        運行模擬回測

        Args:
            num_days: 模擬交易天數

        Returns:
            績效指標字典
        """
        print('\n【獨立版回測 - 模擬數據】')
        print(f'  初始資金: ${self.initial_cash:,.2f}')
        print(f'  風險/筆: ${self.risk_per_trade:.2f}')
        print(f'  策略參數:')
        print(f'    - Gap Up ≥ {self.gap_threshold}%')
        print(f'    - Float ≤ ${self.float_max/1e6:.0f}M')
        print(f'    - RVol ≥ {self.rvol_min}x')
        print(f'  模擬天數: {num_days}')

        # 模擬候選股票
        test_symbols = ['STOCK_A', 'STOCK_B', 'STOCK_C', 'STOCK_D']

        start_date = (datetime.now() - timedelta(days=num_days)).strftime('%Y-%m-%d')
        end_date = datetime.now().strftime('%Y-%m-%d')

        daily_trade_count = 0
        current_date = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date)

        print(f'\n🚀 開始模擬...')

        day_count = 0
        while current_date <= end_dt:
            # 跳過週末
            if current_date.weekday() >= 5:
                current_date += timedelta(days=1)
                continue

            day_count += 1
            current_date_str = current_date.strftime('%Y-%m-%d')

            # 初始化或重置每日記錄
            if current_date_str not in self.daily_pnl:
                self.daily_pnl[current_date_str] = 0

            # 每天重置計數
            if current_date.day == 1 or day_count == 1:
                daily_trade_count = 0

            # 隨機選 1-2 隻候選股
            n_candidates = 1 + (day_count % 2)
            candidates = test_symbols[:(n_candidates)]

            for symbol in candidates:
                if daily_trade_count >= self.max_daily_trades:
                    break

                # 生成模擬數據（20% gap up 概率）
                gap_pct = self.gap_threshold if np.random.random() < 0.2 else 0

                bars = self.generate_mock_price_bars(
                    symbol,
                    start_date,
                    current_date_str,
                    gap_pct=gap_pct,
                    volatility=0.03
                )

                if bars.empty or len(bars) < 1:
                    continue

                today_bar = bars.iloc[-1]
                prev_close = bars.iloc[-2]['Close'] if len(bars) > 1 else today_bar['Open']

                # 檢查 gap up
                actual_gap = (today_bar['Open'] - prev_close) / prev_close * 100

                if actual_gap < self.gap_threshold:
                    continue

                # 進場邏輯：開市時進場
                entry_price = today_bar['Open']
                stop_price = today_bar['Low'] - 0.05

                risk = entry_price - stop_price
                if risk <= 0:
                    continue

                qty = int(self.risk_per_trade / risk)
                if qty <= 0:
                    continue

                # 止盈
                tp1 = entry_price + risk * 2.0
                tp2 = entry_price + risk * 3.0

                # 簡單止盈邏輯：看當日高低點
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
