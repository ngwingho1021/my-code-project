"""
V2 Backtest 框架 - 用歷史數據驗證 Ross Cameron 5支柱策略
"""
import pandas as pd
from dataclasses import dataclass
from typing import List

from utils.logger import get_logger

log = get_logger("backtest_v2")


@dataclass
class Trade:
    """單筆交易記錄"""
    symbol: str
    entry_date: str
    entry_price: float
    exit_date: str
    exit_price: float
    shares: int
    exit_reason: str

    @property
    def pnl(self) -> float:
        return (self.exit_price - self.entry_price) * self.shares

    @property
    def pnl_pct(self) -> float:
        return ((self.exit_price - self.entry_price) / self.entry_price) * 100

    @property
    def is_winner(self) -> bool:
        return self.pnl > 0


class V2Backtester:
    """V2 回測器"""

    def __init__(self, initial_capital: float = 5000.0):
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.trades: List[Trade] = []
        self.peak_capital = initial_capital
        self.max_drawdown = 0.0

    def add_trade(self, symbol: str, entry_date: str, entry_price: float,
                 exit_date: str, exit_price: float, shares: int,
                 exit_reason: str = "manual"):
        """添加交易"""
        trade = Trade(
            symbol=symbol,
            entry_date=entry_date,
            entry_price=entry_price,
            exit_date=exit_date,
            exit_price=exit_price,
            shares=shares,
            exit_reason=exit_reason
        )

        self.trades.append(trade)
        self.capital += trade.pnl

        # 計算最大回撤
        if self.capital > self.peak_capital:
            self.peak_capital = self.capital
        else:
            dd = (self.peak_capital - self.capital) / self.peak_capital
            if dd > self.max_drawdown:
                self.max_drawdown = dd

    def get_metrics(self) -> dict:
        """計算績效指標"""
        if not self.trades:
            return {}

        winners = sum(1 for t in self.trades if t.is_winner)
        losers = len(self.trades) - winners
        total_pnl = sum(t.pnl for t in self.trades)
        win_pnl = sum(t.pnl for t in self.trades if t.is_winner)
        loss_pnl = sum(t.pnl for t in self.trades if not t.is_winner)

        win_rate = (winners / len(self.trades)) * 100
        profit_factor = abs(win_pnl / loss_pnl) if loss_pnl != 0 else float('inf')

        return {
            "total_trades": len(self.trades),
            "winners": winners,
            "losers": losers,
            "win_rate_pct": win_rate,
            "profit_factor": profit_factor,
            "total_pnl": total_pnl,
            "avg_win": (win_pnl / winners) if winners > 0 else 0,
            "avg_loss": (loss_pnl / losers) if losers > 0 else 0,
            "max_drawdown_pct": self.max_drawdown * 100,
            "final_capital": self.capital,
            "roi_pct": ((self.capital - self.initial_capital) / self.initial_capital) * 100
        }

    def print_summary(self):
        """打印摘要"""
        metrics = self.get_metrics()
        if not metrics:
            log.info("無交易記錄")
            return

        log.info("\n" + "=" * 70)
        log.info("【Small-Cap Momentum Trader - 回測結果】")
        log.info("=" * 70)
        log.info(f"總交易數: {metrics['total_trades']}")
        log.info(f"勝場/敗場: {metrics['winners']}/{metrics['losers']}")
        log.info(f"勝率: {metrics['win_rate_pct']:.1f}%")
        log.info(f"利潤因子: {metrics['profit_factor']:.2f}")
        log.info(f"總盈虧: ${metrics['total_pnl']:.2f}")
        log.info(f"平均贏利: ${metrics['avg_win']:.2f}")
        log.info(f"平均虧損: ${metrics['avg_loss']:.2f}")
        log.info(f"最大回撤: {metrics['max_drawdown_pct']:.1f}%")
        log.info(f"收益率: {metrics['roi_pct']:+.1f}% (初始: ${self.initial_capital:.0f}, 最終: ${metrics['final_capital']:.0f})")
        log.info("=" * 70)

    def export_trades_csv(self, filename: str = "backtest_trades.csv"):
        """導出交易到 CSV"""
        if not self.trades:
            log.info("無交易可導出")
            return

        data = []
        for t in self.trades:
            data.append({
                "Symbol": t.symbol,
                "Entry": t.entry_date,
                "Entry Price": f"${t.entry_price:.2f}",
                "Exit": t.exit_date,
                "Exit Price": f"${t.exit_price:.2f}",
                "Shares": t.shares,
                "PnL": f"${t.pnl:.2f}",
                "PnL %": f"{t.pnl_pct:+.1f}%",
                "Reason": t.exit_reason
            })

        df = pd.DataFrame(data)
        df.to_csv(filename, index=False)
        log.info(f"✅ 交易記錄已導出: {filename}")
