"""
倉位管理器 — 管理進場、止盈、止蝕、資金配置
確保風險管理一致、避免過度槓桿
"""
from dataclasses import dataclass
from typing import Optional

from config.settings import ACCOUNT_RISK, STRATEGY
from utils.logger import get_logger

log = get_logger("position_manager")


@dataclass
class RiskMetrics:
    """單筆交易的風險指標"""
    symbol: str
    entry_price: float
    stop_price: float
    target_price: float

    risk_per_share: float          # entry - stop
    position_size: int             # 買幾多股
    risk_amount: float             # risk_per_share * position_size
    reward_amount: float           # (target - entry) * position_size
    reward_risk_ratio: float       # reward / risk


class PositionManager:
    """倉位管理器"""

    def __init__(self):
        self.account_balance = ACCOUNT_RISK.account_size
        self.current_positions = {}         # symbol -> position_size
        self.day_pnl = 0.0
        self.day_trades = 0
        self.max_position_size = 0

    def calculate_position_size(self, entry_price: float, stop_price: float,
                               risk_amount: float = None) -> int:
        """根據風險計算持倉大小"""
        if risk_amount is None:
            risk_amount = ACCOUNT_RISK.max_loss_per_trade

        risk_per_share = entry_price - stop_price
        if risk_per_share <= 0:
            log.warning(f"止蝕價無效：entry={entry_price}, stop={stop_price}")
            return 0

        position_size = int(risk_amount / risk_per_share)

        # 檢查最大持倉百分比
        max_position_value = self.account_balance * ACCOUNT_RISK.max_position_pct_of_account
        current_position_value = position_size * entry_price

        if current_position_value > max_position_value:
            position_size = int(max_position_value / entry_price)
            log.warning(f"持倉超過最大百分比，調整為 {position_size}股")

        return max(1, position_size)

    def calculate_targets(self, entry_price: float, stop_price: float) -> dict:
        """計算止盈目標"""
        risk = entry_price - stop_price

        targets = {
            "stop": stop_price,
            "target_1": entry_price + (risk * STRATEGY.profit_take_1_rr),
            "target_2": entry_price + (risk * STRATEGY.profit_take_2_rr),
            "trailing_stop": entry_price + (risk * STRATEGY.trailing_stop_pct),
        }

        return targets

    def calculate_risk_metrics(self, symbol: str, entry_price: float, stop_price: float,
                              position_size: int) -> RiskMetrics:
        """計算單筆交易的風險指標"""
        risk_per_share = entry_price - stop_price
        target_price = entry_price + (risk_per_share * STRATEGY.target_reward_risk_ratio)

        risk_amount = risk_per_share * position_size
        reward_amount = (target_price - entry_price) * position_size
        rr_ratio = reward_amount / risk_amount if risk_amount > 0 else 0

        metrics = RiskMetrics(
            symbol=symbol,
            entry_price=entry_price,
            stop_price=stop_price,
            target_price=target_price,
            risk_per_share=risk_per_share,
            position_size=position_size,
            risk_amount=risk_amount,
            reward_amount=reward_amount,
            reward_risk_ratio=rr_ratio
        )

        return metrics

    def can_open_position(self, symbol: str) -> bool:
        """檢查係咪可以開新倉"""
        # 檢查是否已有倉位
        if symbol in self.current_positions:
            log.warning(f"{symbol} 已有倉位，唔可以重複開倉")
            return False

        # 檢查每日交易次數限制
        if self.day_trades >= ACCOUNT_RISK.max_trades_per_day:
            log.warning(f"已達到每日最多交易次數 ({ACCOUNT_RISK.max_trades_per_day})")
            return False

        # 檢查並行持倉限制
        if len(self.current_positions) >= ACCOUNT_RISK.max_concurrent_positions:
            log.warning(f"已達到最多並行持倉 ({ACCOUNT_RISK.max_concurrent_positions})")
            return False

        # 檢查每日累計虧損限制
        if self.day_pnl <= -ACCOUNT_RISK.max_loss_per_day:
            log.warning(f"已達到每日最大虧損限制 (${ACCOUNT_RISK.max_loss_per_day})")
            return False

        return True

    def open_position(self, symbol: str, position_size: int):
        """記錄開倉"""
        if not self.can_open_position(symbol):
            return False

        self.current_positions[symbol] = position_size
        self.day_trades += 1
        log.info(f"開倉 {symbol}: {position_size}股 (當日交易: {self.day_trades})")
        return True

    def close_position(self, symbol: str, pnl: float):
        """記錄平倉"""
        if symbol not in self.current_positions:
            log.warning(f"{symbol} 無倉位可平")
            return False

        del self.current_positions[symbol]
        self.day_pnl += pnl
        self.account_balance += pnl
        log.info(f"平倉 {symbol}: 盈虧 ${pnl:.2f} (日累計: ${self.day_pnl:.2f})")
        return True

    def status_summary(self) -> str:
        """狀態摘要"""
        summary = "\n【風險管理狀態】\n"
        summary += f"帳戶餘額: ${self.account_balance:.2f}\n"
        summary += f"今日損益: ${self.day_pnl:.2f}\n"
        summary += f"今日交易: {self.day_trades}/{ACCOUNT_RISK.max_trades_per_day}\n"
        summary += f"現有持倉: {len(self.current_positions)}/{ACCOUNT_RISK.max_concurrent_positions}\n"

        if self.current_positions:
            summary += "持倉清單:\n"
            for symbol, size in self.current_positions.items():
                summary += f"  - {symbol}: {size}股\n"

        return summary
