"""
訂單狀態機 — 防止卡單、確保訂單邏輯清晰
核心概念：每個訂單有明確的生命週期，避免重複下單或遺漏退出
"""
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from utils.logger import get_logger

log = get_logger("order_state_machine")


class OrderState(Enum):
    """訂單狀態流程"""
    PENDING = "pending"           # 待提交
    SUBMITTED = "submitted"       # 已提交
    ACCEPTED = "accepted"         # 已接受（IB確認）
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"             # 已成交
    CANCELLED = "cancelled"       # 已取消
    ERROR = "error"               # 錯誤


class PositionState(Enum):
    """持倉狀態流程"""
    ENTRY_PENDING = "entry_pending"        # 等待進場
    ENTRY_FILLED = "entry_filled"          # 已進場
    MANAGING = "managing"                  # 管理中（可能部分止盈）
    EXITING = "exiting"                    # 離場中
    EXITED = "exited"                      # 已完全離場
    ERROR = "error"                        # 錯誤狀態


@dataclass
class Order:
    """單筆訂單"""
    order_id: int
    symbol: str
    side: str                    # "BUY" or "SELL"
    quantity: int
    order_type: str              # "LIMIT", "STOP", "STOP_LIMIT", "MARKET"
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None

    state: OrderState = field(default=OrderState.PENDING)
    filled_qty: int = field(default=0)
    filled_price: Optional[float] = field(default=None)

    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    error_msg: Optional[str] = field(default=None)

    def is_complete(self) -> bool:
        """訂單係咪已完成（成交或取消）"""
        return self.state in (OrderState.FILLED, OrderState.CANCELLED, OrderState.ERROR)

    def is_pending(self) -> bool:
        """訂單係咪仲未成交"""
        return self.state in (OrderState.PENDING, OrderState.SUBMITTED, OrderState.ACCEPTED)

    def update_status(self, new_state: OrderState, filled_qty: int = 0, filled_price: Optional[float] = None, error_msg: Optional[str] = None):
        """更新訂單狀態"""
        self.state = new_state
        self.filled_qty = filled_qty
        if filled_price:
            self.filled_price = filled_price
        if error_msg:
            self.error_msg = error_msg
        self.updated_at = datetime.now()

        log.info(f"訂單 {self.order_id} ({self.symbol}): {new_state.value} "
                f"(成交: {filled_qty}/{self.quantity})")


@dataclass
class Position:
    """持倉"""
    symbol: str
    entry_price: float
    shares: int
    initial_stop: float

    state: PositionState = field(default=PositionState.ENTRY_PENDING)
    entry_order_id: Optional[int] = None
    stop_order_id: Optional[int] = None
    profit_orders: dict[int, float] = field(default_factory=dict)  # order_id -> price

    remaining_shares: int = field(default=0)
    profits_taken: float = field(default=0.0)

    created_at: datetime = field(default_factory=datetime.now)
    entered_at: Optional[datetime] = None
    exited_at: Optional[datetime] = None

    def mark_entered(self, order_id: int):
        """標記已進場"""
        self.state = PositionState.ENTRY_FILLED
        self.entry_order_id = order_id
        self.entered_at = datetime.now()
        self.remaining_shares = self.shares
        log.info(f"持倉 {self.symbol}: 已進場 @ {self.entry_price} ({self.shares}股)")

    def add_stop_order(self, order_id: int):
        """添加止蝕訂單"""
        self.stop_order_id = order_id

    def add_profit_order(self, order_id: int, price: float):
        """添加止盈訂單"""
        self.profit_orders[order_id] = price

    def take_profit(self, order_id: int, qty: int, price: float):
        """執行止盈"""
        self.remaining_shares -= qty
        self.profits_taken += qty * price
        if order_id in self.profit_orders:
            del self.profit_orders[order_id]
        log.info(f"持倉 {self.symbol}: 止盈 {qty}股 @ {price:.2f} (剩{self.remaining_shares}股)")

    def mark_exited(self, exit_price: float):
        """標記已離場"""
        self.state = PositionState.EXITED
        self.exited_at = datetime.now()
        pnl = (exit_price - self.entry_price) * self.shares
        log.info(f"持倉 {self.symbol}: 已離場 @ {exit_price:.2f} (盈虧: ${pnl:.2f})")


class OrderStateMachine:
    """訂單狀態機 — 管理所有訂單同持倉"""

    def __init__(self):
        self.orders: dict[int, Order] = {}           # order_id -> Order
        self.positions: dict[str, Position] = {}     # symbol -> Position
        self.next_order_id = 1

    def create_order(self, symbol: str, side: str, quantity: int, order_type: str,
                     limit_price: Optional[float] = None, stop_price: Optional[float] = None) -> Order:
        """創建新訂單"""
        order_id = self.next_order_id
        self.next_order_id += 1

        order = Order(
            order_id=order_id,
            symbol=symbol,
            side=side,
            quantity=quantity,
            order_type=order_type,
            limit_price=limit_price,
            stop_price=stop_price
        )
        self.orders[order_id] = order
        log.info(f"創建訂單 {order_id}: {side} {quantity} {symbol} @ {order_type}")
        return order

    def update_order_status(self, order_id: int, new_state: OrderState,
                           filled_qty: int = 0, filled_price: Optional[float] = None,
                           error_msg: Optional[str] = None) -> bool:
        """更新訂單狀態"""
        if order_id not in self.orders:
            log.warning(f"訂單 {order_id} 唔存在")
            return False

        order = self.orders[order_id]
        order.update_status(new_state, filled_qty, filled_price, error_msg)
        return True

    def create_position(self, symbol: str, entry_price: float, shares: int, initial_stop: float) -> Position:
        """創建新持倉"""
        pos = Position(
            symbol=symbol,
            entry_price=entry_price,
            shares=shares,
            initial_stop=initial_stop
        )
        self.positions[symbol] = pos
        log.info(f"創建持倉 {symbol}: {shares}股 @ {entry_price:.2f}, 止蝕 @ {initial_stop:.2f}")
        return pos

    def get_position(self, symbol: str) -> Optional[Position]:
        """獲取持倉"""
        return self.positions.get(symbol)

    def get_active_positions(self) -> list[Position]:
        """獲取所有活躍持倉"""
        return [p for p in self.positions.values() if p.state in (PositionState.ENTRY_FILLED, PositionState.MANAGING)]

    def get_pending_orders(self, symbol: Optional[str] = None) -> list[Order]:
        """獲取所有待處理訂單"""
        orders = [o for o in self.orders.values() if o.is_pending()]
        if symbol:
            orders = [o for o in orders if o.symbol == symbol]
        return orders

    def remove_position(self, symbol: str):
        """移除已完成嘅持倉"""
        if symbol in self.positions:
            del self.positions[symbol]
            log.info(f"持倉 {symbol} 已移除")

    def status_summary(self) -> str:
        """狀態摘要"""
        active_pos = self.get_active_positions()
        pending_orders = len(self.get_pending_orders())

        summary = f"\n【狀態摘要】\n"
        summary += f"活躍持倉: {len(active_pos)}\n"
        summary += f"待處理訂單: {pending_orders}\n"

        for pos in active_pos:
            summary += f"  - {pos.symbol}: {pos.remaining_shares}股 @ {pos.entry_price:.2f}, 止蝕 @ {pos.initial_stop:.2f}\n"

        return summary
