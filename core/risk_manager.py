"""
風控中樞：交易次數上限、同時持倉上限、單注/單日/單週虧損上限。
呢層一定要喺落單之前經過，任何策略訊號都要俾呢度否決權。
"""
from dataclasses import dataclass, field
from datetime import date, timedelta

from config.settings import ACCOUNT_RISK
from utils.logger import get_logger

log = get_logger("risk_manager")
trade_log = get_logger("trade")


@dataclass
class DailyStats:
    day: date
    trades_count: int = 0
    realized_pnl: float = 0.0


class RiskManager:
    def __init__(self):
        self.today = DailyStats(day=date.today())
        self.weekly_pnl_by_day: dict[date, float] = {}
        self.open_positions: dict[str, dict] = {}  # symbol -> {entry_price, shares, stop_price, ...}

    # ------------------------------------------------------------------
    def _roll_day_if_needed(self):
        if self.today.day != date.today():
            self.weekly_pnl_by_day[self.today.day] = self.today.realized_pnl
            self.today = DailyStats(day=date.today())
            self._prune_week()

    def _prune_week(self):
        cutoff = date.today() - timedelta(days=7)
        self.weekly_pnl_by_day = {d: p for d, p in self.weekly_pnl_by_day.items() if d >= cutoff}

    def weekly_pnl(self) -> float:
        self._roll_day_if_needed()
        return sum(self.weekly_pnl_by_day.values()) + self.today.realized_pnl

    # ------------------------------------------------------------------
    def can_open_new_trade(self, symbol: str, planned_risk_dollars: float) -> tuple[bool, str]:
        self._roll_day_if_needed()

        if symbol in self.open_positions:
            return False, f"{symbol} 已經有持倉，唔重複進場"

        if len(self.open_positions) >= ACCOUNT_RISK.max_concurrent_positions:
            return False, f"已達同時持倉上限 {ACCOUNT_RISK.max_concurrent_positions}"

        if self.today.trades_count >= ACCOUNT_RISK.max_trades_per_day:
            return False, f"已達每日交易次數上限 {ACCOUNT_RISK.max_trades_per_day}"

        if planned_risk_dollars > ACCOUNT_RISK.max_loss_per_trade:
            return False, f"單注風險 ${planned_risk_dollars:.2f} 超過上限 ${ACCOUNT_RISK.max_loss_per_trade}"

        if self.today.realized_pnl - planned_risk_dollars < -ACCOUNT_RISK.max_loss_per_day:
            return False, f"今日已realized虧損 ${-self.today.realized_pnl:.2f}，呢單會超每日虧損上限"

        if self.weekly_pnl() - planned_risk_dollars < -ACCOUNT_RISK.max_loss_per_week:
            return False, "呢單可能令本週虧損超過每週上限"

        if self.today.realized_pnl <= -ACCOUNT_RISK.max_loss_per_day:
            return False, "今日已觸發每日最大虧損，停止交易"

        if self.weekly_pnl() <= -ACCOUNT_RISK.max_loss_per_week:
            return False, "本週已觸發每週最大虧損，停止交易"

        return True, "OK"

    def position_size(self, entry_price: float, stop_price: float) -> int:
        """根據單注最大虧損同帳戶規模計算可買股數。"""
        risk_per_share = abs(entry_price - stop_price)
        if risk_per_share <= 0:
            return 0
        max_shares_by_risk = int(ACCOUNT_RISK.max_loss_per_trade / risk_per_share)
        max_dollar_position = ACCOUNT_RISK.account_size * ACCOUNT_RISK.max_position_pct_of_account
        max_shares_by_capital = int(max_dollar_position / entry_price)
        shares = max(0, min(max_shares_by_risk, max_shares_by_capital))
        return shares

    # ------------------------------------------------------------------
    def register_open(self, symbol: str, entry_price: float, shares: int, stop_price: float):
        self._roll_day_if_needed()
        self.today.trades_count += 1
        self.open_positions[symbol] = {
            "entry_price": entry_price,
            "shares": shares,
            "stop_price": stop_price,
            "remaining_shares": shares,
        }
        trade_log.info(
            f"OPEN {symbol} shares={shares} entry={entry_price:.4f} stop={stop_price:.4f} "
            f"risk=${abs(entry_price - stop_price) * shares:.2f}"
        )

    def register_partial_close(self, symbol: str, shares_closed: int, fill_price: float):
        pos = self.open_positions.get(symbol)
        if not pos:
            return
        pnl = (fill_price - pos["entry_price"]) * shares_closed
        self.today.realized_pnl += pnl
        pos["remaining_shares"] -= shares_closed
        trade_log.info(
            f"PARTIAL CLOSE {symbol} shares={shares_closed} @ {fill_price:.4f} pnl=${pnl:.2f} "
            f"remaining={pos['remaining_shares']}"
        )
        if pos["remaining_shares"] <= 0:
            del self.open_positions[symbol]

    def register_full_close(self, symbol: str, fill_price: float):
        pos = self.open_positions.get(symbol)
        if not pos:
            return
        pnl = (fill_price - pos["entry_price"]) * pos["remaining_shares"]
        self.today.realized_pnl += pnl
        trade_log.info(
            f"CLOSE {symbol} shares={pos['remaining_shares']} @ {fill_price:.4f} pnl=${pnl:.2f} "
            f"today_pnl=${self.today.realized_pnl:.2f}"
        )
        del self.open_positions[symbol]

    def status_summary(self) -> str:
        self._roll_day_if_needed()
        return (
            f"今日交易次數: {self.today.trades_count}/{ACCOUNT_RISK.max_trades_per_day} | "
            f"今日盈虧: ${self.today.realized_pnl:.2f} (上限 -${ACCOUNT_RISK.max_loss_per_day}) | "
            f"本週盈虧: ${self.weekly_pnl():.2f} (上限 -${ACCOUNT_RISK.max_loss_per_week}) | "
            f"持倉: {len(self.open_positions)}/{ACCOUNT_RISK.max_concurrent_positions}"
        )
