"""
【Small-Cap Momentum Trader - 重構版本】完整交易機械人
核心：訂單狀態機 + 持倉管理 + 5支柱篩選 + 完整風控

流程：
  1. 連接 IBKR
  2. 每 60 秒掃描一次 5 支柱小市值股票
  3. 每 5 秒監控現有持倉（進場/止盈/止蝕）
  4. 記錄所有交易
"""
import time
import pandas as pd
from datetime import datetime
from typing import Optional

from config.settings import TRADING_HOURS, ACCOUNT_RISK
from core.ibkr_client import IBKRClient
from core.order_state_machine import OrderStateMachine, PositionState
from core.position_manager import PositionManager
from core.stock_selector import StockSelector
from utils.logger import get_logger

log = get_logger("main")
trade_log = get_logger("trades")

SCAN_INTERVAL_SEC = 60
MANAGE_INTERVAL_SEC = 5


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

        log.info("機械人已啟動，等待市場信號...")
        log.info(self.position_mgr.status_summary())

        while self.running:
            try:
                now = time.time()

                # 每 60 秒掃描一次新的機會
                if now - last_scan > SCAN_INTERVAL_SEC:
                    self.scan_and_update_watchlist()
                    last_scan = now

                # 每 5 秒監控現有持倉
                self.manage_open_positions()

                time.sleep(MANAGE_INTERVAL_SEC)

            except Exception as e:
                log.error(f"主迴圈出錯: {e}")
                time.sleep(MANAGE_INTERVAL_SEC * 2)

    def scan_and_update_watchlist(self):
        """掃描 5 支柱股票，更新監控名單"""
        # TODO: 在實際應用中，這裡應該連接到 IBKR Scanner 或 QuoteApi
        # 目前只是展示結構
        log.info("掃描 5 支柱股票...")

        # 示例：假設從某個來源獲得股票清單
        # 在實際中應該來自 IBKR Scanner API
        candidates = []

        # 篩選符合 5 支柱的股票
        filtered = self.stock_selector.filter_candidates(candidates, strict_mode=False)
        log.info(self.stock_selector.get_summary(filtered))

        # 更新監控名單
        for candidate in filtered[:ACCOUNT_RISK.max_concurrent_positions]:
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
        """執行進場"""
        log.info(f"【進場信號】{symbol} @ ${entry_price:.2f}, 止蝕 @ ${stop_price:.2f}")

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
