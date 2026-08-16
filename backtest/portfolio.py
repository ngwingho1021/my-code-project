"""虛擬投資組合管理 - 跟蹤現金、持倉、交易歷史"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime
import json


@dataclass
class Position:
    """單一持倉"""
    symbol: str
    shares: int
    entry_price: float
    entry_time: datetime

    # 止盈設定
    tp1_price: Optional[float] = None
    tp1_executed: bool = False
    tp2_price: Optional[float] = None
    tp2_executed: bool = False
    tp3_price: Optional[float] = None

    # 止損設定
    stop_loss: Optional[float] = None

    # 實時市價追蹤
    current_price: float = field(default=0.0)
    highest_price: float = field(default=0.0)

    @property
    def unrealized_pnl(self) -> float:
        """未實現損益"""
        return (self.current_price - self.entry_price) * self.shares

    @property
    def unrealized_pnl_pct(self) -> float:
        """未實現損益百分比"""
        if self.entry_price == 0:
            return 0.0
        return (self.current_price - self.entry_price) / self.entry_price * 100

    @property
    def profit_loss_ratio(self) -> float:
        """目前利潤/風險比"""
        if not self.stop_loss or self.stop_loss == 0:
            return 0.0

        profit = (self.tp3_price - self.entry_price) if self.tp3_price else self.highest_price - self.entry_price
        risk = self.entry_price - self.stop_loss

        if risk == 0:
            return 0.0
        return profit / risk


@dataclass
class Trade:
    """單筆交易記錄"""
    symbol: str
    entry_time: datetime
    entry_price: float
    entry_shares: int
    exit_time: Optional[datetime] = None
    exit_price: Optional[float] = None
    exit_reason: Optional[str] = None  # "tp1" / "tp2" / "tp3" / "sl" / "manual"

    exit_shares: int = field(default=0)
    realized_pnl: float = field(default=0.0)
    realized_pnl_pct: float = field(default=0.0)

    holding_minutes: int = field(default=0)

    def complete(self, exit_time: datetime, exit_price: float, exit_shares: int, exit_reason: str):
        """標記交易完成"""
        self.exit_time = exit_time
        self.exit_price = exit_price
        self.exit_shares = exit_shares
        self.exit_reason = exit_reason

        self.realized_pnl = (exit_price - self.entry_price) * exit_shares
        self.realized_pnl_pct = (exit_price - self.entry_price) / self.entry_price * 100 if self.entry_price > 0 else 0
        self.holding_minutes = int((exit_time - self.entry_time).total_seconds() / 60)


class VirtualPortfolio:
    """虛擬投資組合跟蹤"""

    def __init__(self, initial_capital: float = 25000.0):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions: Dict[str, Position] = {}  # symbol -> Position
        self.trades: List[Trade] = []
        self.equity_curve: List[tuple] = []  # [(datetime, equity)]

    @property
    def total_equity(self) -> float:
        """總資產 = 現金 + 持倉總值"""
        position_value = sum(p.current_price * p.shares for p in self.positions.values() if p.shares > 0)
        return self.cash + position_value

    @property
    def used_capital(self) -> float:
        """被佔用的資本"""
        return sum(p.entry_price * p.shares for p in self.positions.values() if p.shares > 0)

    @property
    def available_capital(self) -> float:
        """可用資本"""
        return self.cash

    @property
    def num_open_positions(self) -> int:
        """開倉數量"""
        return sum(1 for p in self.positions.values() if p.shares > 0)

    @property
    def total_unrealized_pnl(self) -> float:
        """所有持倉未實現損益"""
        return sum(p.unrealized_pnl for p in self.positions.values() if p.shares > 0)

    @property
    def return_pct(self) -> float:
        """總回報率 %"""
        if self.initial_capital == 0:
            return 0.0
        return (self.total_equity - self.initial_capital) / self.initial_capital * 100

    def enter_position(self, symbol: str, shares: int, price: float, timestamp: datetime,
                      tp1: Optional[float] = None, tp2: Optional[float] = None,
                      tp3: Optional[float] = None, sl: Optional[float] = None):
        """開倉"""
        cost = shares * price
        if cost > self.cash:
            raise ValueError(f"資金不足。需要 ${cost:.2f}，可用 ${self.cash:.2f}")

        if symbol in self.positions and self.positions[symbol].shares > 0:
            raise ValueError(f"{symbol} 已有開倉，不支持加倉")

        self.cash -= cost

        position = Position(
            symbol=symbol,
            shares=shares,
            entry_price=price,
            entry_time=timestamp,
            tp1_price=tp1,
            tp2_price=tp2,
            tp3_price=tp3,
            stop_loss=sl,
            current_price=price,
            highest_price=price
        )

        self.positions[symbol] = position

        # 記錄進場交易
        trade = Trade(
            symbol=symbol,
            entry_time=timestamp,
            entry_price=price,
            entry_shares=shares
        )
        self.trades.append(trade)

    def update_position_price(self, symbol: str, price: float, timestamp: datetime):
        """更新持倉市價"""
        if symbol in self.positions and self.positions[symbol].shares > 0:
            pos = self.positions[symbol]
            pos.current_price = price
            if price > pos.highest_price:
                pos.highest_price = price

    def exit_position(self, symbol: str, exit_price: float, exit_shares: int,
                     timestamp: datetime, reason: str = "manual"):
        """平倉"""
        if symbol not in self.positions or self.positions[symbol].shares < exit_shares:
            raise ValueError(f"持倉不足。請求平 {exit_shares} 股，實際持倉 {self.positions[symbol].shares if symbol in self.positions else 0}")

        pos = self.positions[symbol]

        # 現金增加
        self.cash += exit_price * exit_shares

        # 更新持倉
        pos.shares -= exit_shares

        # 記錄平倉
        if self.trades:
            # 找最後一筆未平倉的交易
            for trade in reversed(self.trades):
                if trade.symbol == symbol and trade.exit_time is None:
                    trade.complete(timestamp, exit_price, exit_shares, reason)
                    break

        # 如果全部平倉，刪除持倉
        if pos.shares == 0:
            del self.positions[symbol]

    def record_equity_snapshot(self, timestamp: datetime):
        """記錄淨值快照"""
        self.equity_curve.append((timestamp, self.total_equity))

    def get_trade_stats(self) -> Dict:
        """計算交易統計"""
        if not self.trades:
            return {
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0.0,
                "total_profit": 0.0,
                "total_loss": 0.0,
                "avg_trade_pnl": 0.0,
                "largest_win": 0.0,
                "largest_loss": 0.0,
                "avg_holding_time_minutes": 0,
            }

        completed_trades = [t for t in self.trades if t.exit_time is not None]

        if not completed_trades:
            return {
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0.0,
                "total_profit": 0.0,
                "total_loss": 0.0,
                "avg_trade_pnl": 0.0,
                "largest_win": 0.0,
                "largest_loss": 0.0,
                "avg_holding_time_minutes": 0,
            }

        pnls = [t.realized_pnl for t in completed_trades]
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p < 0]

        return {
            "total_trades": len(completed_trades),
            "winning_trades": len(wins),
            "losing_trades": len(losses),
            "win_rate": len(wins) / len(completed_trades) * 100 if completed_trades else 0,
            "total_profit": sum(wins),
            "total_loss": sum(losses),
            "avg_trade_pnl": sum(pnls) / len(pnls) if pnls else 0,
            "largest_win": max(wins) if wins else 0,
            "largest_loss": min(losses) if losses else 0,
            "avg_holding_time_minutes": int(sum(t.holding_minutes for t in completed_trades) / len(completed_trades)) if completed_trades else 0,
        }

    def to_dict(self) -> dict:
        """序列化投資組合"""
        return {
            "initial_capital": self.initial_capital,
            "current_equity": self.total_equity,
            "cash": self.cash,
            "used_capital": self.used_capital,
            "positions": {
                sym: {
                    "shares": pos.shares,
                    "entry_price": pos.entry_price,
                    "current_price": pos.current_price,
                    "unrealized_pnl": pos.unrealized_pnl,
                    "unrealized_pnl_pct": pos.unrealized_pnl_pct,
                }
                for sym, pos in self.positions.items()
            },
            "stats": self.get_trade_stats(),
        }
