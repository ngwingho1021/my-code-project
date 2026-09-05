"""
【Pre-Market Momentum Trader】盤前專用交易機械人
交易視窗：07:00–09:20 EDT（只在盤前入場，09:25 前強制清倉）

與主力 bot (small_cap_momentum_bot_main.py) 共用同一 IBKR 帳戶，但：
- 只在盤前進場（07:00–09:20）
- 09:25 強制平倉，唔持倉過開市
- 全部訂單使用 outsideRth=True + 限價（盤前無市價單）
- 過濾條件較寬鬆（RSI/OBV/量能 bar 數不足，自動略過）
- 成交量下限 50,000（盤前遠低於盤中）
- Bid-Ask spread 上限 5%
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import time
from datetime import datetime, time as dt_time
from typing import Optional
import pytz

from config.settings import TRADING_HOURS, ACCOUNT_RISK, SCANNER, STRATEGY
from core.small_cap_momentum_bot_ibkr_client import IBKRClient
from core.small_cap_momentum_bot_order_state_machine import OrderStateMachine, PositionState
from core.small_cap_momentum_bot_position_manager import PositionManager
from utils.logger import get_logger

log = get_logger("premarket_main")
trade_log = get_logger("premarket_trades")

SCAN_INTERVAL_SEC = 60
MANAGE_INTERVAL_SEC = 1
MAX_WATCHLIST_SIZE = 10

# 盤前時間常數（EDT）
PREMARKET_ENTRY_START = dt_time(7, 0)    # 07:00 有量先入場（04:00-07:00 太薄）
PREMARKET_ENTRY_END   = dt_time(9, 20)   # 09:20 停止新進場（留時間退出）
PREMARKET_FORCE_CLOSE = dt_time(9, 25)   # 09:25 強制平倉，09:30 前清零
MARKET_OPEN           = dt_time(9, 30)   # 09:30 市場開市（參考）
EST = pytz.timezone('America/New_York')

# 盤前專用過濾參數（與主力 bot 有別）
PREMARKET_MIN_VOLUME  = 50_000   # 盤前成交量下限（遠低於盤中 300K）
PREMARKET_MAX_SPREAD  = 0.05     # Spread 上限 5%（盤前較闊）
PREMARKET_STOP_PCT    = 0.05     # 預設止蝕 5%（ATR 計算失敗時用）


class PreMarketEngine:
    """盤前交易引擎"""

    def __init__(self):
        self.ibkr = IBKRClient()
        self.ib = None
        self.order_sm = OrderStateMachine()
        self.position_mgr = PositionManager()
        self.watchlist = {}                  # symbol -> contract
        self.watchlist_scan_prices = {}      # symbol -> price at scan time
        self.watchlist_prev_closes = {}      # symbol -> previous day close
        self.tickers = {}                    # symbol -> streaming ticker
        self.rejected_symbols = set()
        self.running = False

    # ------------------------------------------------------------------ #
    # 時間檢查
    # ------------------------------------------------------------------ #

    def now_est(self) -> dt_time:
        return datetime.now(EST).time()

    def is_entry_window(self) -> bool:
        """07:00–09:20 可以新開倉"""
        t = self.now_est()
        return PREMARKET_ENTRY_START <= t < PREMARKET_ENTRY_END

    def is_premarket(self) -> bool:
        """07:00–09:30 在盤前範圍"""
        t = self.now_est()
        return PREMARKET_ENTRY_START <= t < MARKET_OPEN

    def is_force_close_window(self) -> bool:
        """09:25–09:30 強制平倉"""
        t = self.now_est()
        return PREMARKET_FORCE_CLOSE <= t < MARKET_OPEN

    def is_too_early(self) -> bool:
        """07:00 前太薄，唔掃描"""
        return self.now_est() < PREMARKET_ENTRY_START

    # ------------------------------------------------------------------ #
    # 主迴圈
    # ------------------------------------------------------------------ #

    def start(self):
        log.info("=" * 60)
        log.info("【Pre-Market Momentum Trader 啟動】")
        log.info(f"  入場視窗: {PREMARKET_ENTRY_START}–{PREMARKET_ENTRY_END} EDT")
        log.info(f"  強制平倉: {PREMARKET_FORCE_CLOSE} EDT")
        log.info("=" * 60)

        try:
            self.ibkr.connect()
            self.ib = self.ibkr.ib
            log.info("✅ IBKR 連接成功")
        except Exception as e:
            log.error(f"IBKR 連接失敗: {e}")
            return

        self.running = True
        last_scan = 0.0

        try:
            while self.running:
                now_t = self.now_est()

                # 開市後停止所有操作
                if now_t >= MARKET_OPEN:
                    log.info("🔔 09:30 開市，盤前 bot 停止（未平倉應已在09:25清空）")
                    break

                if self.is_too_early():
                    log.info(f"⏳ {now_t} 太早，等到 07:00 再掃描...")
                    time.sleep(60)
                    continue

                # 強制平倉視窗（09:25-09:30）
                if self.is_force_close_window():
                    self.force_close_all_positions()
                    time.sleep(5)
                    continue

                # 掃描（每60秒）
                elapsed = time.time() - last_scan
                if elapsed >= SCAN_INTERVAL_SEC and self.is_entry_window():
                    self.scan_watchlist()
                    last_scan = time.time()

                # 監控持倉（每2秒）
                if self.is_premarket():
                    self.manage_positions()

                time.sleep(MANAGE_INTERVAL_SEC)

        except KeyboardInterrupt:
            log.info("⚠️ 手動停止")
        finally:
            self.force_close_all_positions()
            try:
                self.ibkr.disconnect()
            except Exception:
                pass
            log.info("盤前 bot 已停止")

    # ------------------------------------------------------------------ #
    # 掃描監控名單
    # ------------------------------------------------------------------ #

    def scan_watchlist(self):
        current_watching = len(self.watchlist)
        if current_watching >= MAX_WATCHLIST_SIZE:
            return

        log.info(f"📊 盤前掃描 IBKR gap-up 股票... ({self.now_est()})")

        scan_results = self.ibkr.scan_for_gap_up_stocks(
            min_gap_pct=SCANNER.gap_up_pct_min,
            min_price=SCANNER.price_min,
            max_price=SCANNER.price_max
        )

        if not scan_results:
            return

        available_slots = MAX_WATCHLIST_SIZE - current_watching
        added = 0

        for result in scan_results:
            if added >= available_slots:
                break

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

            if symbol in self.watchlist or symbol in self.rejected_symbols:
                continue
            if self.order_sm.get_position(symbol):
                continue

            # 黑名單
            if symbol in SCANNER.banned_symbols:
                self.rejected_symbols.add(symbol)
                continue
            if any(symbol.endswith(sfx) for sfx in SCANNER.banned_suffixes):
                self.rejected_symbols.add(symbol)
                continue

            # 取掃描價 + 前收盤
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

            prev_close = self.ibkr.get_prev_close(contract)

            # Gap 下限
            if scan_price and prev_close and prev_close > 0:
                gap_pct = (scan_price - prev_close) / prev_close * 100
                if gap_pct < SCANNER.watchlist_min_gap_pct:
                    log.info(f"⏭️ 跳過 {symbol}: gap {gap_pct:.1f}% < {SCANNER.watchlist_min_gap_pct}%")
                    continue

            # 盤前成交量（比盤中低很多）
            pre_vol = 0.0
            if scan_ticker:
                try:
                    v = getattr(scan_ticker, 'volume', None)
                    if v is not None:
                        pre_vol = float(v)
                except (TypeError, ValueError):
                    pass
            if pre_vol > 0 and pre_vol < PREMARKET_MIN_VOLUME:
                log.info(f"⏭️ 跳過 {symbol}: 盤前量 {pre_vol:,.0f} < {PREMARKET_MIN_VOLUME:,.0f}")
                continue

            # Float
            float_shares = self.ibkr.get_float_shares(contract)
            if float_shares is not None and float_shares > SCANNER.float_shares_max:
                log.info(f"⏭️ 跳過 {symbol}: Float {float_shares/1e6:.1f}M > 20M")
                continue

            self.watchlist[symbol] = contract
            if scan_price:
                self.watchlist_scan_prices[symbol] = scan_price
            if prev_close:
                self.watchlist_prev_closes[symbol] = prev_close
            gap_str = f" gap={((scan_price - prev_close) / prev_close * 100):.1f}%" if (scan_price and prev_close) else ""
            log.info(f"✅ 加入盤前監控: {symbol} @ ${scan_price:.2f}{gap_str}" if scan_price else f"✅ 加入監控: {symbol}")
            added += 1

        log.info(f"盤前監控名單: {list(self.watchlist.keys())} ({len(self.watchlist)} 隻)")

    # ------------------------------------------------------------------ #
    # 監控持倉
    # ------------------------------------------------------------------ #

    def manage_positions(self):
        for symbol, contract in list(self.watchlist.items()):
            try:
                pos = self.order_sm.get_position(symbol)
                if pos is None:
                    if self.is_entry_window():
                        self.check_entry_signal(symbol, contract)
                elif pos.state == PositionState.ENTRY_FILLED:
                    self.check_exit_signal(symbol, contract, pos)
            except Exception as e:
                log.error(f"{symbol} 監控出錯: {e}")

    # ------------------------------------------------------------------ #
    # 入場訊號
    # ------------------------------------------------------------------ #

    def check_entry_signal(self, symbol: str, contract) -> bool:
        if symbol in self.rejected_symbols:
            return False

        # 持倉上限
        if len(self.position_mgr.current_positions) >= ACCOUNT_RISK.max_concurrent_positions:
            return False
        real_count = self.ibkr.get_small_cap_position_count(SCANNER.price_min, SCANNER.price_max)
        if real_count >= 0 and real_count >= ACCOUNT_RISK.max_concurrent_positions:
            return False
        if not self.position_mgr.can_open_position(symbol):
            return False

        ticker = self.ibkr.get_market_data(contract, timeout=2)
        if ticker is None:
            return False

        price = None
        for attr in ['last', 'bid']:
            val = getattr(ticker, attr, None)
            if val is not None:
                try:
                    v = float(val)
                    if v > 0:
                        price = round(v, 2)
                        break
                except (TypeError, ValueError):
                    pass

        if price is None or price <= 0:
            return False

        # 價格範圍
        if price < SCANNER.price_min or price > SCANNER.price_max:
            return False

        # 距日高
        day_high = None
        try:
            h = getattr(ticker, 'high', None)
            if h is not None:
                hf = float(h)
                if hf > 0 and hf == hf:
                    day_high = round(hf, 2)
        except (TypeError, ValueError):
            pass

        if day_high and price < day_high:
            drop_pct = (day_high - price) / day_high
            if drop_pct > SCANNER.max_drop_from_high_pct:
                log.info(f"{symbol}: 距日高 {drop_pct*100:.1f}% (>{SCANNER.max_drop_from_high_pct*100:.0f}%)，動能已過")
                return False
            log.info(f"  ✔ 日高距離: ${price:.2f} / ${day_high:.2f} ({drop_pct*100:.1f}%)")

        # 盤前成交量
        try:
            entry_vol = float(getattr(ticker, 'volume', 0) or 0)
        except (TypeError, ValueError):
            entry_vol = 0.0
        if entry_vol > 0 and entry_vol < PREMARKET_MIN_VOLUME:
            log.info(f"{symbol}: 盤前量 {entry_vol:,.0f} < {PREMARKET_MIN_VOLUME:,.0f}")
            return False
        if entry_vol > 0:
            log.info(f"  ✔ 盤前量: {entry_vol:,.0f}")

        # Bid-Ask spread（盤前較闊，上限 5%）
        try:
            bid_v = getattr(ticker, 'bid', None)
            ask_v = getattr(ticker, 'ask', None)
            if bid_v and ask_v:
                bid_f, ask_f = float(bid_v), float(ask_v)
                if bid_f > 0 and ask_f > bid_f and price > 0:
                    spread_pct = (ask_f - bid_f) / price
                    if spread_pct > PREMARKET_MAX_SPREAD:
                        log.info(f"{symbol}: spread {spread_pct*100:.1f}% > {PREMARKET_MAX_SPREAD*100:.0f}%，流動性不足")
                        return False
                    log.info(f"  ✔ Spread: {spread_pct*100:.2f}%")
        except (TypeError, ValueError):
            pass

        # Gap 仍然有效（唔可以跌穿掃描時gap的一半）
        prev_close = self.watchlist_prev_closes.get(symbol)
        if prev_close and prev_close > 0:
            gap_pct_now = (price - prev_close) / prev_close * 100
            if gap_pct_now < SCANNER.gap_up_pct_min:
                log.info(f"{symbol}: gap 回填至 {gap_pct_now:.1f}%（需 >= {SCANNER.gap_up_pct_min}%），跳過")
                return False
            scan_price = self.watchlist_scan_prices.get(symbol)
            if scan_price and scan_price > prev_close:
                gap_at_scan = (scan_price - prev_close) / prev_close * 100
                if gap_at_scan > 0 and gap_pct_now < gap_at_scan * 0.5:
                    log.info(f"{symbol}: gap 由 {gap_at_scan:.1f}% 縮至 {gap_pct_now:.1f}%（失血超一半），跳過")
                    return False
            log.info(f"  ✔ gap 仍強: {gap_pct_now:.1f}%")

        # 計算止蝕位（ATR-based，2%-8%）
        atr = self.ibkr.get_atr(contract)
        if atr and atr > 0:
            stop_distance = atr * 1.0
            stop_distance = max(stop_distance, price * 0.02)
            stop_distance = min(stop_distance, price * 0.08)
        else:
            stop_distance = price * PREMARKET_STOP_PCT
        stop_price = round(price - stop_distance, 2)

        # 盈虧比確認（至少 1:2，盤前 target = 2R 以內）
        risk = price - stop_price
        target_1r = price + risk
        target_2r = price + risk * 2
        if risk <= 0 or (target_2r - price) / price < 0.01:
            log.info(f"{symbol}: 盈虧比不達標，跳過")
            return False

        log.info(
            f"🎯 [{symbol}] @ ${price:.2f} | 止蝕 ${stop_price:.2f} ({stop_distance/price*100:.1f}%) "
            f"| 1R ${target_1r:.2f} | 2R ${target_2r:.2f}"
        )
        return self.execute_entry(symbol, contract, price, stop_price)

    # ------------------------------------------------------------------ #
    # 離場訊號（盤前限價單）
    # ------------------------------------------------------------------ #

    def check_exit_signal(self, symbol: str, contract, pos):
        try:
            ticker = self.tickers.get(symbol)
            if ticker is None:
                ticker = self.ibkr.get_market_data(contract, timeout=1)
            if ticker is None:
                return

            def _price(attrs):
                for attr in attrs:
                    val = getattr(ticker, attr, None)
                    try:
                        v = float(val)
                        if v > 0 and v == v:
                            return round(v, 2)
                    except (TypeError, ValueError):
                        pass
                return None

            bid   = _price(['bid'])
            price = _price(['last', 'bid'])
            if price is None or price <= 0 or pos.remaining_shares <= 0:
                return

            entry = pos.entry_price
            risk  = entry - pos.initial_stop
            t1r   = round(entry + risk, 2)
            t2r   = round(entry + risk * 2, 2)
            t3r   = round(entry + risk * 3, 2)

            if price > pos.highest_price:
                pos.highest_price = price

            # 止蝕（軟件追蹤，限價單在 bid-0.01 增加成交機會）
            current_stop = pos.trailing_stop if pos.trailing_stop > 0 else pos.initial_stop
            check_stop = bid if bid else price
            if check_stop <= current_stop:
                sell_price = round(check_stop - 0.01, 2)
                log.info(f"🛑 盤前止蝕: {symbol} bid=${check_stop:.2f} (止蝕線 ${current_stop:.2f}) → 落單 ${sell_price:.2f}")
                self._sell(symbol, contract, pos, sell_price, "premarket_stop", pos.remaining_shares)
                return

            # 1R 止盈 → 賣 50%，止蝕移到打和
            if price >= t1r and not pos.took_profit_1r:
                qty = max(1, int(pos.shares * 0.5))
                pos.took_profit_1r = True
                pos.trailing_stop = entry
                log.info(f"🎯 盤前 1R: {symbol} 賣 {qty}股 @ ${price:.2f}, 止蝕移打和 ${entry:.2f}")
                self._sell(symbol, contract, pos, price, "premarket_tp1r", qty)
                return

            # 2R 止盈 → 賣 30%，止蝕移到 1R
            if price >= t2r and not pos.took_profit_2r:
                qty = max(1, int(pos.shares * 0.3))
                pos.took_profit_2r = True
                pos.trailing_stop = t1r
                log.info(f"🎉 盤前 2R: {symbol} 賣 {qty}股 @ ${price:.2f}, 止蝕提到 ${t1r:.2f}")
                self._sell(symbol, contract, pos, price, "premarket_tp2r", qty)
                return

            # 3R 止盈 → 全部賣出
            if price >= t3r:
                log.info(f"🚀 盤前 3R: {symbol} 全部賣出 @ ${price:.2f}")
                self._sell(symbol, contract, pos, price, "premarket_tp3r", pos.remaining_shares)
                return

        except Exception as e:
            log.error(f"{symbol} 盤前離場檢查失敗: {e}")

    # ------------------------------------------------------------------ #
    # 強制平倉（09:25，盤前限價）
    # ------------------------------------------------------------------ #

    def force_close_all_positions(self):
        active = self.order_sm.get_active_positions()
        if not active:
            return

        log.warning(f"⚠️ 09:25 強制平倉（開市前清零）- {len(active)} 個持倉")
        for pos in active:
            symbol = pos.symbol
            contract = self.watchlist.get(symbol)
            if contract is None:
                continue
            try:
                ticker = self.ibkr.get_market_data(contract, timeout=2)
                exit_price = None
                if ticker:
                    for attr in ['bid', 'last']:
                        val = getattr(ticker, attr, None)
                        try:
                            v = float(val)
                            if v > 0:
                                exit_price = round(v, 2)
                                break
                        except (TypeError, ValueError):
                            pass
                if exit_price is None:
                    exit_price = pos.entry_price

                self._sell(symbol, contract, pos, exit_price, "force_close_premarket", pos.remaining_shares)
            except Exception as e:
                log.error(f"強制平倉 {symbol} 失敗: {e}")

    # ------------------------------------------------------------------ #
    # 執行入場
    # ------------------------------------------------------------------ #

    def execute_entry(self, symbol: str, contract, entry_price: float, stop_price: float):
        log.info(f"【盤前進場】{symbol} @ ${entry_price:.2f}, 止蝕 @ ${stop_price:.2f}")

        position_size = self.position_mgr.calculate_position_size(entry_price, stop_price)
        if position_size <= 0:
            return False
        if not self.position_mgr.can_open_position(symbol):
            return False

        try:
            trade = self.ibkr.place_buy_order(contract, position_size, entry_price)
            if trade is None:
                log.warning(f"❌ 盤前買單被拒: {symbol}")
                self.rejected_symbols.add(symbol)
                self.watchlist.pop(symbol, None)
                return False

            buy_order = self.order_sm.create_order(symbol, "BUY", position_size, "LIMIT", limit_price=entry_price)
            pos = self.order_sm.create_position(symbol, entry_price, position_size, stop_price)
            pos.mark_entered(buy_order.order_id)
            self.position_mgr.open_position(symbol, position_size)

            ticker = self.ibkr.subscribe_market_data(contract)
            if ticker:
                self.tickers[symbol] = ticker

            trade_log.info(f"📈 盤前進場: {symbol} | {position_size}股 @ ${entry_price:.2f} | 止蝕 ${stop_price:.2f}")
            return True
        except Exception as e:
            log.error(f"盤前進場失敗: {e}")
            return False

    # ------------------------------------------------------------------ #
    # 統一賣出（全部用盤前限價單）
    # ------------------------------------------------------------------ #

    def _sell(self, symbol: str, contract, pos, exit_price: float, reason: str, qty: int):
        qty = min(qty, pos.remaining_shares)
        if qty <= 0:
            return

        # 防做空：對比 IBKR 實際持股
        ibkr_qty = self.ibkr.get_position_shares(symbol)
        if ibkr_qty == 0:
            log.warning(f"⚠️ {symbol}: IBKR 無持倉，清理內部狀態（防做空）")
            pos.remaining_shares = 0
            pos.mark_exited(exit_price)
            self.position_mgr.current_positions.pop(symbol, None)
            self.watchlist.pop(symbol, None)
            self.order_sm.remove_position(symbol)
            if symbol in self.tickers:
                self.ibkr.unsubscribe_market_data(contract)
                del self.tickers[symbol]
            return
        if ibkr_qty > 0 and qty > ibkr_qty:
            log.warning(f"⚠️ {symbol}: 截頭賣出 {qty} → {ibkr_qty}（IBKR 實際持股）")
            qty = ibkr_qty

        trade = self.ibkr.place_premarket_sell_order(contract, qty, exit_price)
        if trade is None:
            log.warning(f"❌ 盤前賣單被拒: {symbol} {qty}股")
            return

        pnl = (exit_price - pos.entry_price) * qty
        pos.remaining_shares -= qty
        pos.profits_taken += pnl
        self.position_mgr.day_pnl += pnl
        self.position_mgr.account_balance += pnl

        trade_log.info(
            f"{'📈' if pnl > 0 else '📉'} 盤前離場: {symbol} | {qty}股 @ ${exit_price:.2f} "
            f"| PnL: ${pnl:.2f} | 原因: {reason} | 剩餘: {pos.remaining_shares}股"
        )

        if pos.remaining_shares <= 0:
            pos.mark_exited(exit_price)
            self.position_mgr.current_positions.pop(symbol, None)
            self.watchlist.pop(symbol, None)
            self.order_sm.remove_position(symbol)
            if symbol in self.tickers:
                self.ibkr.unsubscribe_market_data(contract)
                del self.tickers[symbol]


# ------------------------------------------------------------------ #
# 入口
# ------------------------------------------------------------------ #

if __name__ == "__main__":
    engine = PreMarketEngine()
    engine.start()
