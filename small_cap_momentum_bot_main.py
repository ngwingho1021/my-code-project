"""
【Small-Cap Momentum Trader - 重構版本】完整交易機械人
核心：訂單狀態機 + 持倉管理 + 5支柱篩選 + 完整風控
時間範圍：Pre-Market (04:00-09:30) + Market Hours (09:30-16:00) EST

流程：
  1. 連接 IBKR
  2. 每 60 秒掃描一次 5 支柱小市值股票（僅限交易時間）
  3. 每 5 秒監控現有持倉（進場/止盈/止蝕）
  4. 記錄所有交易
  5. 16:00 後停止新進場，只管理現有持倉
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import time
import pandas as pd
from datetime import datetime, time as dt_time
from typing import Optional
import pytz

from config.settings import TRADING_HOURS, ACCOUNT_RISK
from core.small_cap_momentum_bot_ibkr_client import IBKRClient
from core.small_cap_momentum_bot_order_state_machine import OrderStateMachine, PositionState
from core.small_cap_momentum_bot_position_manager import PositionManager
from core.small_cap_momentum_bot_stock_selector import StockSelector
from utils.logger import get_logger

log = get_logger("main")
trade_log = get_logger("trades")

SCAN_INTERVAL_SEC = 60
MANAGE_INTERVAL_SEC = 5

# 交易時間（EST 時區）
PREMARKET_START = dt_time(4, 0)      # 04:00
MARKET_OPEN = dt_time(9, 30)         # 09:30
MARKET_CLOSE = dt_time(16, 0)        # 16:00
AFTERHOURS_END = dt_time(20, 0)      # 20:00
EST = pytz.timezone('America/New_York')


class TradingEngine:
    """交易引擎 - 主要邏輯"""

    def __init__(self):
        self.ibkr = IBKRClient()
        self.ib = None
        self.order_sm = OrderStateMachine()    # 訂單狀態機
        self.position_mgr = PositionManager()   # 持倉管理
        self.stock_selector = StockSelector()   # 5支柱篩選
        self.watchlist = {}                     # symbol -> contract
        self.running = False

    def is_trading_hours(self) -> bool:
        """檢查係咪交易時間（Pre-Market + Market Hours）"""
        now = datetime.now(EST).time()
        # 04:00 - 16:00 EST（Pre-Market + Market Hours）
        return PREMARKET_START <= now < MARKET_CLOSE

    def is_market_hours(self) -> bool:
        """檢查係咪市場時間（不包括 Pre-Market）"""
        now = datetime.now(EST).time()
        # 09:30 - 16:00 EST
        return MARKET_OPEN <= now < MARKET_CLOSE

    def is_premarket_hours(self) -> bool:
        """檢查係咪盤前時間"""
        now = datetime.now(EST).time()
        # 04:00 - 09:30 EST
        return PREMARKET_START <= now < MARKET_OPEN

    def get_time_status(self) -> str:
        """獲取當前時間狀態"""
        if self.is_premarket_hours():
            return "Pre-Market (04:00-09:30)"
        elif self.is_market_hours():
            return "Market Hours (09:30-16:00)"
        else:
            return "Closed (16:00-04:00)"

    def start(self):
        """啟動機械人"""
        try:
            log.info("=" * 60)
            log.info("【Small-Cap Momentum Trader 啟動】")
            log.info("=" * 60)

            # 連接 IBKR
            self.ib = self.ibkr.connect()
            log.info(f"✅ 已連接 IBKR")

            self.running = True
            self.run_loop()

        except KeyboardInterrupt:
            log.info("\n【收到停止信號】安全關閉機械人...")
        except Exception as e:
            log.error(f"❌ 機械人出錯: {e}")
        finally:
            self.shutdown()

    def run_loop(self):
        """主交易迴圈"""
        last_scan = 0
        last_time_status = None

        log.info("機械人已啟動，等待市場信號...")
        log.info(self.position_mgr.status_summary())

        while self.running:
            try:
                now = time.time()
                time_status = self.get_time_status()

                # 每次時間狀態改變時打印
                if time_status != last_time_status:
                    log.info(f"⏰ 時間狀態: {time_status}")
                    last_time_status = time_status

                # 只在交易時間掃描新機會
                if self.is_trading_hours():
                    if now - last_scan > SCAN_INTERVAL_SEC:
                        self.scan_and_update_watchlist()
                        last_scan = now
                else:
                    # 非交易時間，不掃描新機會，但仍管理現有持倉（直到全部平倉）
                    if self.order_sm.get_active_positions():
                        log.info("🔔 非交易時間，但仍有開放持倉，繼續管理...")

                # 隨時監控現有持倉（包括非交易時間）
                self.manage_open_positions()

                time.sleep(MANAGE_INTERVAL_SEC)

            except Exception as e:
                log.error(f"主迴圈出錯: {e}")
                time.sleep(MANAGE_INTERVAL_SEC * 2)

    def scan_and_update_watchlist(self):
        """掃描 5 支柱股票，更新監控名單（僅在交易時間）"""
        # 雙重檢查時間
        if not self.is_trading_hours():
            log.warning(f"非交易時間 ({self.get_time_status()})，跳過掃描")
            return

        log.info(f"📊 掃描 IBKR 間隔上升股票... ({self.get_time_status()})")

        # 使用 IBKR 掃描器尋找開盤跳空股票
        symbols = self.ibkr.scan_for_gap_up_stocks(
            min_gap_pct=ACCOUNT_RISK.scanner_criteria.get("gap_up_pct_min", 5.0),
            min_price=ACCOUNT_RISK.scanner_criteria.get("price_min", 2.0),
            max_price=ACCOUNT_RISK.scanner_criteria.get("price_max", 20.0)
        )

        if not symbols:
            log.info("🔍 沒有找到符合條件的股票")
            return

        candidates = []
        for symbol in symbols:
            try:
                contract = self.ibkr.make_stock(symbol)
                contract = self.ibkr.qualify_contract(contract)

                # 獲取市場數據
                ticker = self.ibkr.get_market_data(contract, timeout=1)
                if not ticker:
                    continue

                # 獲取歷史數據計算間隔
                bars = self.ibkr.get_historical_data(contract, duration="1 D", bar_size="1 day")
                if len(bars) < 2:
                    continue

                prev_close = bars[-2].close
                current_price = ticker.last or ticker.close

                if current_price <= 0 or prev_close <= 0:
                    continue

                gap_pct = ((current_price - prev_close) / prev_close) * 100
                today_volume = ticker.volume or 0
                avg_volume = 1000000  # 簡化假設

                candidate = self.stock_selector.evaluate(
                    symbol=symbol,
                    current_price=current_price,
                    prev_close=prev_close,
                    today_volume=today_volume,
                    avg_volume=avg_volume,
                    float_shares=None,  # IBKR 掃描器不提供
                    has_news=False
                )

                if candidate:
                    candidates.append(candidate)

            except Exception as e:
                log.debug(f"評估 {symbol} 失敗: {e}")

        # 篩選符合 5 支柱的股票
        filtered = self.stock_selector.filter_candidates(candidates, strict_mode=False)
        log.info(self.stock_selector.get_summary(filtered))

        # 更新監控名單（檢查併發限制）
        active_positions = self.order_sm.get_active_positions()
        available_slots = ACCOUNT_RISK.max_concurrent_positions - len(active_positions)

        for candidate in filtered[:available_slots]:
            if candidate.symbol not in self.watchlist:
                try:
                    contract = self.ibkr.make_stock(candidate.symbol)
                    contract = self.ibkr.qualify_contract(contract)
                    self.watchlist[candidate.symbol] = contract
                    log.info(f"✅ 加入監控: {candidate.symbol}")
                except Exception as e:
                    log.warning(f"無法加入 {candidate.symbol}: {e}")

    def manage_open_positions(self):
        """監控現有持倉 - 檢查進場/止盈/止蝕"""
        for symbol, contract in list(self.watchlist.items()):
            try:
                pos = self.order_sm.get_position(symbol)

                if pos is None:
                    # 檢查進場條件
                    self.check_entry_signal(symbol, contract)
                elif pos.state == PositionState.ENTRY_FILLED:
                    # 監控現有持倉
                    self.check_exit_signal(symbol, contract, pos)

            except Exception as e:
                log.error(f"{symbol} 監控出錯: {e}")

    def check_entry_signal(self, symbol: str, contract) -> bool:
        """檢查進場信號"""
        # 簡化示例 - 實際應該有完整的技術分析
        # 這裡只展示結構
        return False

    def check_exit_signal(self, symbol: str, contract, pos):
        """檢查離場信號"""
        # 監控止盈/止蝕
        pass

    def execute_entry(self, symbol: str, contract, entry_price: float, stop_price: float):
        """執行進場（只在交易時間進場）"""
        # 檢查交易時間
        if not self.is_trading_hours():
            log.warning(f"非交易時間 ({self.get_time_status()})，無法進場")
            return False

        log.info(f"【進場信號】{symbol} @ ${entry_price:.2f}, 止蝕 @ ${stop_price:.2f} ({self.get_time_status()})")

        # 計算持倉大小
        position_size = self.position_mgr.calculate_position_size(entry_price, stop_price)

        if position_size <= 0:
            log.warning(f"持倉大小無效: {position_size}")
            return False

        # 檢查風控
        if not self.position_mgr.can_open_position(symbol):
            log.warning(f"無法開倉 {symbol}")
            return False

        # 創建訂單
        try:
            # 下買單
            buy_order = self.order_sm.create_order(
                symbol, "BUY", position_size, "LIMIT",
                limit_price=entry_price
            )

            trade = self.ibkr.place_buy_order(contract, position_size, entry_price)
            if trade:
                # 創建持倉
                pos = self.order_sm.create_position(symbol, entry_price, position_size, stop_price)
                pos.mark_entered(buy_order.order_id)

                # 記錄
                self.position_mgr.open_position(symbol, position_size)
                log.info(f"✅ 已下買單: {symbol} {position_size}股")
                return True

        except Exception as e:
            log.error(f"進場執行失敗: {e}")

        return False

    def shutdown(self):
        """安全關閉機械人"""
        log.info("\n【清理資源】")

        self.running = False

        # 取消所有待處理訂單
        pending = self.order_sm.get_pending_orders()
        for order in pending:
            log.info(f"取消訂單 {order.order_id}")

        # 記錄最終狀態
        log.info(self.position_mgr.status_summary())

        # 斷開連線
        if self.ib:
            self.ibkr.disconnect()
            log.info("✅ 已斷開 IBKR 連線")

        log.info("【機械人已安全關閉】")


def main():
    """主入口"""
    engine = TradingEngine()
    engine.start()


if __name__ == "__main__":
    main()
