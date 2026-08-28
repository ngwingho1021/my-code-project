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

from config.settings import TRADING_HOURS, ACCOUNT_RISK, SCANNER
from core.small_cap_momentum_bot_ibkr_client import IBKRClient
from core.small_cap_momentum_bot_order_state_machine import OrderStateMachine, PositionState
from core.small_cap_momentum_bot_position_manager import PositionManager
from core.small_cap_momentum_bot_stock_selector import StockSelector
from utils.logger import get_logger

log = get_logger("main")
trade_log = get_logger("trades")

SCAN_INTERVAL_SEC = 60
MANAGE_INTERVAL_SEC = 1
MAX_WATCHLIST_SIZE = 15
STOP_LOSS_PCT = 0.05

# 交易時間（EST 時區）
PREMARKET_START = dt_time(4, 0)      # 04:00
MARKET_OPEN = dt_time(9, 30)         # 09:30
FORCE_CLOSE_TIME = dt_time(15, 55)   # 15:55 強制平倉
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
        self.watchlist_scan_prices = {}         # symbol -> price at scan time
        self.tickers = {}                       # symbol -> streaming ticker
        self.rejected_symbols = set()           # 被 IBKR 拒絕嘅股票
        self.running = False

    def is_trading_hours(self) -> bool:
        """檢查係咪交易時間（Pre-Market + Market Hours）"""
        now = datetime.now(EST).time()
        return PREMARKET_START <= now < MARKET_CLOSE

    def is_market_hours(self) -> bool:
        """檢查係咪市場時間（不包括 Pre-Market）"""
        now = datetime.now(EST).time()
        return MARKET_OPEN <= now < MARKET_CLOSE

    def is_premarket_hours(self) -> bool:
        """檢查係咪盤前時間"""
        now = datetime.now(EST).time()
        return PREMARKET_START <= now < MARKET_OPEN

    def is_force_close_window(self) -> bool:
        """收盤前 5 分鐘強制平倉視窗"""
        now = datetime.now(EST).time()
        return FORCE_CLOSE_TIME <= now < MARKET_CLOSE

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

                if time_status != last_time_status:
                    log.info(f"⏰ 時間狀態: {time_status}")
                    last_time_status = time_status

                    # 每日重置：新的交易日清空監控名單
                    if time_status.startswith("Pre-Market"):
                        self.watchlist.clear()
                        self.watchlist_scan_prices.clear()
                        log.info("🔄 新交易日，清空監控名單")

                # 只在交易時間掃描新機會
                if self.is_trading_hours():
                    if now - last_scan > SCAN_INTERVAL_SEC:
                        self.scan_and_update_watchlist()
                        last_scan = now
                else:
                    if self.order_sm.get_active_positions():
                        log.info("🔔 非交易時間，但仍有開放持倉，繼續管理...")

                # 隨時監控現有持倉（包括非交易時間）
                self.manage_open_positions()

                time.sleep(MANAGE_INTERVAL_SEC)

            except Exception as e:
                log.error(f"主迴圈出錯: {e}")
                import traceback
                traceback.print_exc()
                time.sleep(MANAGE_INTERVAL_SEC * 2)

    def cleanup_watchlist(self):
        """清理監控名單：移除未持倉且不再符合入場條件嘅股票"""
        to_remove = []
        for symbol, contract in list(self.watchlist.items()):
            if self.order_sm.get_position(symbol):
                continue  # 有持倉，唔清除

            ticker = self.tickers.get(symbol)
            if ticker is None:
                ticker = self.ibkr.get_market_data(contract, timeout=1)

            price = None
            if ticker:
                for attr in ['last', 'bid']:
                    val = getattr(ticker, attr, None)
                    try:
                        v = float(val)
                        if v > 0 and v == v:
                            price = round(v, 2)
                            break
                    except (TypeError, ValueError):
                        pass

            if price is None:
                continue

            reason = None

            # 條件 1：價格超出 $2-$20 範圍
            if price < SCANNER.price_min or price > SCANNER.price_max:
                reason = f"股價 ${price:.2f} 超出範圍"

            # 條件 2：距離掃描時價格太遠（動能消失或已跑太遠）
            if reason is None and symbol in self.watchlist_scan_prices:
                scan_price = self.watchlist_scan_prices[symbol]
                drop_pct = (scan_price - price) / scan_price        # 跌幅
                run_pct = (price - scan_price) / scan_price          # 升幅

                if drop_pct >= STOP_LOSS_PCT:                        # 跌 >= 5%：動能消失
                    reason = f"較掃描價 ${scan_price:.2f} 跌 {drop_pct*100:.1f}%，動能消失"
                elif run_pct >= 0.20:                                 # 升 >= 20%：已跑太遠，入場係追貨
                    reason = f"較掃描價 ${scan_price:.2f} 升 {run_pct*100:.1f}%，已跑太遠"

            if reason:
                to_remove.append(symbol)
                log.info(f"🗑️ 清出監控名單: {symbol} — {reason}")

        for symbol in to_remove:
            del self.watchlist[symbol]
            self.watchlist_scan_prices.pop(symbol, None)

        if to_remove:
            log.info(f"監控名單清理完成，移除 {len(to_remove)} 隻，剩餘 {len(self.watchlist)} 隻")

    def scan_and_update_watchlist(self):
        """掃描 5 支柱股票，更新監控名單（僅在交易時間）"""
        if not self.is_trading_hours():
            log.warning(f"非交易時間 ({self.get_time_status()})，跳過掃描")
            return

        # 先清理名單中已不符合條件嘅股票
        self.cleanup_watchlist()

        # 檢查是否還有空位
        active_positions = self.order_sm.get_active_positions()
        current_watching = len(self.watchlist)
        current_positions = len(active_positions)

        if current_positions >= ACCOUNT_RISK.max_concurrent_positions:
            log.info(f"已達最大持倉數 ({current_positions}/{ACCOUNT_RISK.max_concurrent_positions})，跳過掃描")
            return

        if current_watching >= MAX_WATCHLIST_SIZE:
            log.info(f"監控名單已滿 ({current_watching}/{MAX_WATCHLIST_SIZE})，跳過掃描")
            return

        log.info(f"📊 掃描 IBKR 間隔上升股票... ({self.get_time_status()})")

        scan_results = self.ibkr.scan_for_gap_up_stocks(
            min_gap_pct=SCANNER.gap_up_pct_min,
            min_price=SCANNER.price_min,
            max_price=SCANNER.price_max
        )

        if not scan_results:
            log.info("🔍 沒有找到符合條件的股票")
            return

        available_slots = MAX_WATCHLIST_SIZE - current_watching
        added = 0

        for result in scan_results:
            if added >= available_slots:
                break

            # 兼容字符串或字典格式
            if isinstance(result, dict):
                symbol = result["symbol"]
                contract = result["contract"]
            else:
                symbol = str(result)
                contract = self.ibkr.make_stock(symbol)
                try:
                    contract = self.ibkr.qualify_contract(contract)
                except Exception:
                    continue

            if symbol in self.watchlist:
                continue

            if symbol in self.rejected_symbols:
                continue

            if self.order_sm.get_position(symbol):
                continue

            # 記錄掃描時嘅價格，用嚟日後判斷係咪仍接近入場條件
            scan_ticker = self.ibkr.get_market_data(contract, timeout=1)
            scan_price = None
            if scan_ticker:
                for attr in ['last', 'bid']:
                    val = getattr(scan_ticker, attr, None)
                    try:
                        v = float(val)
                        if v > 0 and v == v:
                            scan_price = round(v, 2)
                            break
                    except (TypeError, ValueError):
                        pass

            self.watchlist[symbol] = contract
            if scan_price:
                self.watchlist_scan_prices[symbol] = scan_price
            log.info(f"✅ 加入監控: {symbol} @ ${scan_price:.2f}" if scan_price else f"✅ 加入監控: {symbol}")
            added += 1

        log.info(f"監控名單: {list(self.watchlist.keys())} ({len(self.watchlist)} 隻)")

    def force_close_all_positions(self):
        """收盤前 5 分鐘強制市價平倉所有持倉"""
        active = self.order_sm.get_active_positions()
        if not active:
            return

        log.warning(f"⚠️ 15:55 強制平倉 - {len(active)} 個持倉")
        for pos in active:
            symbol = pos.symbol
            contract = self.watchlist.get(symbol)
            if contract is None:
                continue
            if pos.remaining_shares <= 0:
                continue
            try:
                log.warning(f"🔴 強制平倉: {symbol} {pos.remaining_shares}股 (市價)")
                trade = self.ibkr.place_market_sell_order(contract, pos.remaining_shares)
                if trade:
                    # 用最後已知 bid 價估算 PnL 記錄
                    ticker = self.tickers.get(symbol)
                    exit_price = pos.entry_price  # 保守估算，實際以成交為準
                    if ticker:
                        for attr in ['last', 'bid']:
                            val = getattr(ticker, attr, None)
                            try:
                                v = float(val)
                                if v > 0 and v == v:
                                    exit_price = round(v, 2)
                                    break
                            except (TypeError, ValueError):
                                pass
                    self.execute_exit(symbol, contract, pos, exit_price, "force_close_eod", pos.remaining_shares)
            except Exception as e:
                log.error(f"強制平倉 {symbol} 失敗: {e}")

    def manage_open_positions(self):
        """監控現有持倉 - 檢查進場/止盈/止蝕"""
        # 收盤前 5 分鐘：強制市價平倉，唔留過夜
        if self.is_force_close_window():
            self.force_close_all_positions()
            return

        for symbol, contract in list(self.watchlist.items()):
            try:
                pos = self.order_sm.get_position(symbol)

                if pos is None:
                    self.check_entry_signal(symbol, contract)
                elif pos.state == PositionState.ENTRY_FILLED:
                    if self.is_market_hours():
                        self.check_exit_signal(symbol, contract, pos)
                    elif self.is_premarket_hours():
                        self.check_premarket_exit_signal(symbol, contract, pos)

            except Exception as e:
                log.error(f"{symbol} 監控出錯: {e}")

    def check_entry_signal(self, symbol: str, contract) -> bool:
        """檢查進場信號 - 只在正常交易時間進場（09:30-16:00）"""
        if not self.is_market_hours():
            return False

        if symbol in self.rejected_symbols:
            return False

        # 查 IBKR 帳戶真實小市值持倉（同一帳戶有其他 bot）
        real_count = self.ibkr.get_small_cap_position_count(SCANNER.price_min, SCANNER.price_max)
        if real_count >= 0 and real_count >= ACCOUNT_RISK.max_concurrent_positions:
            log.info(f"帳戶真實小市值持倉 {real_count}/{ACCOUNT_RISK.max_concurrent_positions}，跳過進場")
            return False

        if not self.position_mgr.can_open_position(symbol):
            return False

        # 嘗試獲取價格快照
        try:
            ticker = self.ibkr.get_market_data(contract, timeout=2)

            if ticker is None:
                log.debug(f"{symbol}: 無法獲取市場數據")
                return False

            price = None
            for attr in ['last', 'close', 'bid', 'ask']:
                val = getattr(ticker, attr, None)
                if val is not None and val > 0:
                    price = round(float(val), 2)
                    break

            if price is None or price <= 0:
                log.debug(f"{symbol}: 無有效價格")
                return False

            # 價格範圍檢查
            if price < SCANNER.price_min or price > SCANNER.price_max:
                log.debug(f"{symbol}: 價格 ${price:.2f} 超出範圍")
                return False

            # 計算止蝕價格（5% 止損）
            stop_price = round(price * (1 - STOP_LOSS_PCT), 2)

            log.info(f"🎯 發現進場機會: {symbol} @ ${price:.2f}, 止蝕 @ ${stop_price:.2f}")

            # 執行進場
            return self.execute_entry(symbol, contract, price, stop_price)

        except Exception as e:
            log.debug(f"{symbol}: 進場檢查失敗: {e}")
            return False

    def check_premarket_exit_signal(self, symbol: str, contract, pos):
        """盤前離場 - 純 polling，限價單執行（盤前唔支援 stop order）"""
        try:
            ticker = self.tickers.get(symbol)
            if ticker is None:
                # 未有串流，用 snapshot 補救
                ticker = self.ibkr.get_market_data(contract, timeout=1)
            if ticker is None:
                return

            def _get_price(attrs):
                for attr in attrs:
                    val = getattr(ticker, attr, None)
                    try:
                        v = float(val)
                        if v > 0 and v == v:
                            return round(v, 2)
                    except (TypeError, ValueError):
                        pass
                return None

            stop_price = _get_price(['bid', 'last'])
            current_price = _get_price(['last', 'bid'])
            price = current_price or stop_price

            if price is None or price <= 0:
                return

            if pos.remaining_shares <= 0:
                return

            entry_price = pos.entry_price
            risk = entry_price - pos.initial_stop
            target_1r = round(entry_price + risk, 2)
            target_2r = round(entry_price + (risk * 2), 2)
            target_3r = round(entry_price + (risk * 3), 2)

            # 止蝕觸發（bid 優先，即刻落限價單）
            current_stop = pos.trailing_stop if pos.trailing_stop > 0 else pos.initial_stop
            check_stop = stop_price if stop_price else price
            if check_stop <= current_stop:
                reason = "premarket_stop"
                log.info(f"🛑 盤前止蝕: {symbol} bid=${check_stop:.2f} (止蝕線: ${current_stop:.2f})")
                self.execute_exit(symbol, contract, pos, current_stop, reason, pos.remaining_shares)
                return

            # 1R → 賣 50%，止蝕線移到打和位（software 追蹤）
            if price >= target_1r and not pos.took_profit_1r:
                qty = max(1, int(pos.shares * 0.5))
                pos.took_profit_1r = True
                pos.trailing_stop = entry_price
                log.info(f"🎯 盤前 1R: {symbol} 賣 {qty}股 @ ${price:.2f}, 止蝕移打和 ${entry_price:.2f}")
                self.execute_exit(symbol, contract, pos, price, "premarket_tp1r", qty)
                return

            # 2R → 賣 30%，止蝕線提到 1R（software 追蹤）
            if price >= target_2r and not pos.took_profit_2r:
                qty = max(1, int(pos.shares * 0.3))
                pos.took_profit_2r = True
                pos.trailing_stop = target_1r
                log.info(f"🎉 盤前 2R: {symbol} 賣 {qty}股 @ ${price:.2f}, 止蝕升到 ${target_1r:.2f}")
                self.execute_exit(symbol, contract, pos, price, "premarket_tp2r", qty)
                return

            # 3R → 全部賣出
            if price >= target_3r and not pos.took_profit_3r:
                qty = pos.remaining_shares
                pos.took_profit_3r = True
                log.info(f"🚀 盤前 3R: {symbol} 全出 {qty}股 @ ${price:.2f}")
                self.execute_exit(symbol, contract, pos, price, "premarket_tp3r", qty)
                return

        except Exception as e:
            log.error(f"{symbol} 盤前離場檢查失敗: {e}")

    def check_exit_signal(self, symbol: str, contract, pos):
        """盤中離場 - 分批止盈 + trailing stop"""
        try:
            ticker = self.tickers.get(symbol)
            if ticker is None:
                ticker = self.ibkr.get_market_data(contract, timeout=1)
            if ticker is None:
                return

            # 止蝕用 bid（即時，急跌更準），唔用 close（昨日收市）
            def _get_price(attrs):
                for attr in attrs:
                    val = getattr(ticker, attr, None)
                    try:
                        v = float(val)
                        if v > 0 and v == v:  # v==v 排除 nan
                            return round(v, 2)
                    except (TypeError, ValueError):
                        pass
                return None

            stop_price = _get_price(['bid', 'last'])      # 止蝕用 bid 優先
            current_price = _get_price(['last', 'bid'])   # 止盈用 last 優先
            price = current_price or stop_price

            if price is None or price <= 0:
                return

            if pos.remaining_shares <= 0:
                return

            entry_price = pos.entry_price
            risk = entry_price - pos.initial_stop
            target_1r = round(entry_price + risk, 2)
            target_2r = round(entry_price + (risk * 2), 2)

            # 更新最高價
            if price > pos.highest_price:
                pos.highest_price = price

            # 更新 trailing stop（只升唔跌）
            if pos.took_profit_1r:
                trail = round(entry_price + (pos.highest_price - entry_price) * 0.5, 2)
                new_stop = max(entry_price, trail)
                if new_stop > pos.trailing_stop:
                    pos.trailing_stop = new_stop

            # 止蝕/Trailing stop 觸發 → 用 bid 價格確認，即刻全部賣出
            check_stop = stop_price if stop_price else price
            if check_stop <= pos.trailing_stop:
                reason = "trailing_stop" if pos.took_profit_1r else "stop_loss"
                log.info(f"🛑 {reason}: {symbol} bid=${check_stop:.2f} (止蝕線: ${pos.trailing_stop:.2f})")
                self.execute_exit(symbol, contract, pos, check_stop, reason, pos.remaining_shares)
                return

            # 1R 止盈 → 賣 50%
            if price >= target_1r and not pos.took_profit_1r:
                qty = int(pos.shares * 0.5)
                if qty < 1:
                    qty = 1
                pos.took_profit_1r = True
                pos.trailing_stop = entry_price
                log.info(f"🎯 1R 止盈: {symbol} 賣 {qty}股 @ ${price:.2f}, 止蝕移到打和 ${entry_price:.2f}")
                self.execute_exit(symbol, contract, pos, price, "take_profit_1r", qty)
                return

            # 2R 止盈 → 賣 30%
            if price >= target_2r and not pos.took_profit_2r:
                qty = int(pos.shares * 0.3)
                if qty < 1:
                    qty = 1
                pos.took_profit_2r = True
                pos.trailing_stop = max(pos.trailing_stop, target_1r)
                log.info(f"🎉 2R 止盈: {symbol} 賣 {qty}股 @ ${price:.2f}, 止蝕提升到 ${pos.trailing_stop:.2f}")
                self.execute_exit(symbol, contract, pos, price, "take_profit_2r", qty)
                return

        except Exception as e:
            log.error(f"{symbol} 離場檢查失敗: {e}")

    def execute_entry(self, symbol: str, contract, entry_price: float, stop_price: float):
        """執行進場（只在正常交易時間進場 09:30-16:00）"""
        if not self.is_market_hours():
            log.warning(f"非正常交易時間 ({self.get_time_status()})，唔進場")
            return False

        log.info(f"【進場信號】{symbol} @ ${entry_price:.2f}, 止蝕 @ ${stop_price:.2f} ({self.get_time_status()})")

        position_size = self.position_mgr.calculate_position_size(entry_price, stop_price)

        if position_size <= 0:
            log.warning(f"持倉大小無效: {position_size}")
            return False

        if not self.position_mgr.can_open_position(symbol):
            log.warning(f"無法開倉 {symbol}")
            return False

        try:
            buy_order = self.order_sm.create_order(
                symbol, "BUY", position_size, "LIMIT",
                limit_price=entry_price
            )

            trade = self.ibkr.place_buy_order(contract, position_size, entry_price)
            if trade is None:
                log.warning(f"❌ 買單被拒絕或取消: {symbol}，加入黑名單")
                self.rejected_symbols.add(symbol)
                if symbol in self.watchlist:
                    del self.watchlist[symbol]
                return False

            pos = self.order_sm.create_position(symbol, entry_price, position_size, stop_price)
            pos.mark_entered(buy_order.order_id)

            self.position_mgr.open_position(symbol, position_size)

            # 訂閱串流數據（進場後持續更新，唔需要每次 snapshot）
            ticker = self.ibkr.subscribe_market_data(contract)
            if ticker:
                self.tickers[symbol] = ticker

            # 盤前：唔掛止蝕單（限價單會即刻成交），改靠 poll 監控

            trade_log.info(f"📈 進場: {symbol} | {position_size}股 @ ${entry_price:.2f} | 止蝕 ${stop_price:.2f}")
            log.info(f"✅ 已下買單: {symbol} {position_size}股 @ ${entry_price:.2f}")
            return True

        except Exception as e:
            log.error(f"進場執行失敗: {e}")

        return False

    def execute_exit(self, symbol: str, contract, pos, exit_price: float, reason: str, qty: int = None):
        """執行離場（支持分批賣出）"""
        try:
            if qty is None:
                qty = pos.remaining_shares
            qty = min(qty, pos.remaining_shares)
            if qty <= 0:
                return

            if reason in ("stop_loss", "trailing_stop"):
                trade = self.ibkr.place_market_sell_order(contract, qty)
            elif reason == "premarket_stop_loss":
                trade = self.ibkr.place_sell_order(contract, qty, exit_price)
            else:
                trade = self.ibkr.place_sell_order(contract, qty, exit_price)

            if trade is None:
                log.warning(f"❌ 賣單被拒絕: {symbol} {qty}股")
                return

            pnl = (exit_price - pos.entry_price) * qty
            pos.remaining_shares -= qty
            pos.profits_taken += pnl

            trade_log.info(f"{'📈' if pnl > 0 else '📉'} 離場: {symbol} | {qty}股 @ ${exit_price:.2f} | PnL: ${pnl:.2f} | 原因: {reason} | 剩餘: {pos.remaining_shares}股")
            log.info(f"{'✅' if pnl > 0 else '⚠️'} {reason}: {symbol} 賣{qty}股 PnL: ${pnl:.2f} (剩{pos.remaining_shares}股)")

            self.position_mgr.day_pnl += pnl
            self.position_mgr.account_balance += pnl

            if pos.remaining_shares <= 0:
                pos.mark_exited(exit_price)
                if symbol in self.position_mgr.current_positions:
                    del self.position_mgr.current_positions[symbol]
                if symbol in self.watchlist:
                    del self.watchlist[symbol]
                self.order_sm.remove_position(symbol)
                # 退訂串流數據
                if symbol in self.tickers:
                    self.ibkr.unsubscribe_market_data(contract)
                    del self.tickers[symbol]
                log.info(f"📊 {symbol} 完全離場, 總 PnL: ${pos.profits_taken:.2f}")

        except Exception as e:
            log.error(f"離場執行失敗 {symbol}: {e}")

    def shutdown(self):
        """安全關閉機械人"""
        log.info("\n【清理資源】")

        self.running = False

        pending = self.order_sm.get_pending_orders()
        for order in pending:
            log.info(f"取消訂單 {order.order_id}")

        log.info(self.position_mgr.status_summary())

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
