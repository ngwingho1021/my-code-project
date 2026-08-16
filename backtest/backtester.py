"""核心回測引擎 - 按時間順序執行策略並跟蹤表現"""

import asyncio
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.data_fetcher import DataFetcher
from config.settings import STRATEGY, ACCOUNT_RISK
from backtest.portfolio import VirtualPortfolio


class Backtester:
    """
    回測引擎：
    1. 加載歷史K線數據
    2. 按照策略信號執行進場/離場
    3. 虛擬執行訂單（考慮滑點、成交量）
    4. 跟蹤績效指標
    """

    def __init__(self, initial_capital: float = 25000.0, slippage_pct: float = 0.5):
        self.initial_capital = initial_capital
        self.slippage_pct = slippage_pct

        self.portfolio = VirtualPortfolio(initial_capital)
        self.data_fetcher = DataFetcher()

        self.ohlcv_data: Dict[str, pd.DataFrame] = {}  # symbol -> OHLCV DataFrame
        self.equity_curve: List[tuple] = []

    async def load_bars(self, symbol: str, start_date: str, end_date: str,
                       timeframe: str = "1Min") -> pd.DataFrame:
        """加載歷史K線數據"""
        try:
            df = await self.data_fetcher.get_bars_dataframe(
                symbol=symbol,
                start=start_date,
                end=end_date,
                timeframe=timeframe
            )

            if df.empty:
                print(f"⚠️  {symbol} 無數據 ({start_date} to {end_date})")
                return pd.DataFrame()

            # 確保列名正確
            df = df.rename(columns={
                'open': 'o', 'high': 'h', 'low': 'l', 'close': 'c', 'volume': 'v'
            })

            self.ohlcv_data[symbol] = df
            print(f"✅ {symbol}: {len(df)} 根K線 ({df.index[0]} to {df.index[-1]})")
            return df

        except Exception as e:
            print(f"❌ 加載 {symbol} 數據失敗: {e}")
            return pd.DataFrame()

    def apply_slippage(self, price: float, is_buy: bool = True) -> float:
        """模擬滑點"""
        slippage = price * (self.slippage_pct / 100)
        return price + slippage if is_buy else price - slippage

    def run(self, symbol: str, start_date: str, end_date: str,
           signal_func: Callable[[pd.DataFrame, int], Dict[str, Any]]) -> Dict:
        """
        執行回測

        signal_func: 策略信號函數，輸入 (df, current_bar_idx) -> Dict
                    返回值應包含: {
                        'action': 'buy' / 'sell' / 'hold' / 'exit',
                        'entry_price': float (if action=='buy'),
                        'tp1': float, 'tp2': float, 'tp3': float,
                        'stop_loss': float,
                        'exit_price': float (if action=='sell'/'exit'),
                        'exit_reason': str
                    }
        """

        # 1. 加載數據
        print(f"\n{'='*80}")
        print(f"🔄 回測: {symbol} ({start_date} to {end_date})")
        print(f"{'='*80}")

        loop = asyncio.run(self.load_bars(symbol, start_date, end_date))
        if loop.empty:
            return {"error": "No data loaded"}

        df = self.ohlcv_data[symbol].copy()

        # 2. 逐根K線遍歷
        for i in range(len(df)):
            bar_time = df.index[i]
            current_price = df.iloc[i]['c']  # 收盤價

            # 3. 更新現有持倉市價
            if symbol in self.portfolio.positions:
                self.portfolio.update_position_price(symbol, current_price, bar_time)

            # 4. 檢查止盈/止損
            if symbol in self.portfolio.positions:
                pos = self.portfolio.positions[symbol]

                # 止損檢查
                if pos.stop_loss and current_price <= pos.stop_loss:
                    exit_price = self.apply_slippage(pos.stop_loss, is_buy=False)
                    self.portfolio.exit_position(symbol, exit_price, pos.shares, bar_time, "sl")
                    print(f"  🛑 止損觸發 @ {exit_price:.2f}")
                    continue

                # TP1 檢查
                if (pos.tp1_price and current_price >= pos.tp1_price and
                        not pos.tp1_executed and pos.shares > 0):
                    exit_shares = int(pos.shares * 0.5)  # 50% 倉位
                    exit_price = self.apply_slippage(pos.tp1_price, is_buy=False)
                    self.portfolio.exit_position(symbol, exit_price, exit_shares, bar_time, "tp1")
                    pos.tp1_executed = True
                    print(f"  ✅ TP1 (50%) 止盈 @ {exit_price:.2f}")

                # TP2 檢查
                if (pos.tp2_price and current_price >= pos.tp2_price and
                        not pos.tp2_executed and pos.shares > 0):
                    exit_shares = int(pos.shares * 0.3 / 0.5)  # 30% of original
                    exit_price = self.apply_slippage(pos.tp2_price, is_buy=False)
                    self.portfolio.exit_position(symbol, exit_price, exit_shares, bar_time, "tp2")
                    pos.tp2_executed = True
                    print(f"  ✅ TP2 (30%) 止盈 @ {exit_price:.2f}")

            # 5. 獲取策略信號
            try:
                signal = signal_func(df, i)
            except Exception as e:
                print(f"  ⚠️  信號生成失敗 @ {bar_time}: {e}")
                continue

            if not signal:
                continue

            action = signal.get('action', 'hold')

            # 6. 執行信號
            if action == 'buy' and symbol not in self.portfolio.positions:
                entry_price = signal.get('entry_price', current_price)
                entry_price = self.apply_slippage(entry_price, is_buy=True)

                # 計算倉位大小
                risk_per_trade = ACCOUNT_RISK.max_loss_per_trade
                stop_loss = signal.get('stop_loss')

                if stop_loss:
                    risk_per_share = entry_price - stop_loss
                    if risk_per_share > 0:
                        shares = int(risk_per_trade / risk_per_share)
                        shares = min(shares, int(self.portfolio.available_capital / entry_price))
                    else:
                        shares = int(self.portfolio.available_capital / entry_price * 0.1)
                else:
                    shares = int(self.portfolio.available_capital / entry_price * 0.1)

                if shares > 0:
                    try:
                        self.portfolio.enter_position(
                            symbol=symbol,
                            shares=shares,
                            price=entry_price,
                            timestamp=bar_time,
                            tp1=signal.get('tp1'),
                            tp2=signal.get('tp2'),
                            tp3=signal.get('tp3'),
                            sl=stop_loss
                        )
                        print(f"📈 買入 {shares} 股 @ {entry_price:.2f} ({bar_time})")
                    except ValueError as e:
                        print(f"  ❌ 買入失敗: {e}")

            elif action == 'exit' and symbol in self.portfolio.positions:
                exit_price = signal.get('exit_price', current_price)
                pos = self.portfolio.positions[symbol]
                exit_price = self.apply_slippage(exit_price, is_buy=False)
                self.portfolio.exit_position(symbol, exit_price, pos.shares, bar_time,
                                           signal.get('exit_reason', 'manual'))
                print(f"📉 全部平倉 @ {exit_price:.2f} ({bar_time})")

            # 7. 記錄每日淨值
            self.portfolio.record_equity_snapshot(bar_time)

        # 8. 平倉所有剩余持倉
        if symbol in self.portfolio.positions and self.portfolio.positions[symbol].shares > 0:
            final_price = df.iloc[-1]['c']
            pos = self.portfolio.positions[symbol]
            self.portfolio.exit_position(symbol, final_price, pos.shares, df.index[-1], "eod")
            print(f"📉 回測結束平倉 @ {final_price:.2f}")

        # 9. 生成統計
        return self._generate_report()

    def _generate_report(self) -> Dict:
        """生成回測報告"""
        stats = self.portfolio.get_trade_stats()

        report = {
            "summary": {
                "initial_capital": self.portfolio.initial_capital,
                "final_equity": self.portfolio.total_equity,
                "total_return": self.portfolio.total_equity - self.portfolio.initial_capital,
                "total_return_pct": self.portfolio.return_pct,
            },
            "trading_stats": stats,
            "equity_curve": self.portfolio.equity_curve,
        }

        # 計算最大回撤
        if self.portfolio.equity_curve:
            equities = [e[1] for e in self.portfolio.equity_curve]
            peak = equities[0]
            max_dd = 0
            for eq in equities:
                dd = (peak - eq) / peak * 100 if peak > 0 else 0
                max_dd = max(max_dd, dd)
            report["summary"]["max_drawdown_pct"] = max_dd

        return report
