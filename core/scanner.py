"""
用 IBKR TWS 內建 Scanner 揾出符合 Ross Cameron 5 核心條件嘅股票：
  1) 股價 $2-20
  2) 流通股本 (float) < 20M
  3) Gap up >= 5%
  4) 有催化劑（新聞）— 用 core.news 另外驗證
  5) 相對成交量 >= 2 倍

IBKR scanner 本身冇 float 呢個欄位，所以用 reqScannerSubscription 揀
"TOP_PERC_GAIN" / "HIGH_OPT_IMP_VOLAT" 類 scanCode 做初篩，
再用 reqFundamentalData / reqMktData 去補齊 float 同 rel volume 做二次過濾。
"""
import math
from dataclasses import dataclass

from ib_async import ScannerSubscription, TagValue, Stock

from config.settings import SCANNER
from utils.logger import get_logger

log = get_logger("scanner")


@dataclass
class ScanResult:
    symbol: str
    price: float
    gap_pct: float
    rel_volume: float
    float_shares: float | None
    avg_volume: float


class MomentumScanner:
    def __init__(self, ib):
        self.ib = ib

    def _build_subscription(self) -> ScannerSubscription:
        sub = ScannerSubscription()
        sub.instrument = "STK"
        sub.locationCode = "STK.US.MAJOR"
        sub.scanCode = "TOP_PERC_GAIN"
        sub.abovePrice = SCANNER.price_min
        sub.belowPrice = SCANNER.price_max
        sub.aboveVolume = int(SCANNER.min_avg_volume)
        return sub

    def scan_gap_up_candidates(self, max_results: int = 50) -> list[str]:
        sub = self._build_subscription()
        tag_values = [
            TagValue("changePercAbove", str(SCANNER.gap_up_pct_min)),
        ]
        log.info("向 IBKR 發送 scanner 請求...")
        data = self.ib.reqScannerData(sub, [], tag_values)
        symbols = [d.contractDetails.contract.symbol for d in data[:max_results]]
        log.info(f"Scanner 初篩結果 ({len(symbols)} 隻): {symbols}")
        return symbols

    def enrich_and_filter(self, symbols: list[str]) -> list[ScanResult]:
        """對初篩名單逐隻攞 fundamental / market data，用 5 核心條件做二次過濾。"""
        results: list[ScanResult] = []
        for sym in symbols:
            try:
                contract = Stock(sym, "SMART", "USD")
                self.ib.qualifyContracts(contract)

                ticker = self.ib.reqMktData(contract, "", False, False)
                self.ib.sleep(1.5)

                price = ticker.last if ticker.last and not math.isnan(ticker.last) else ticker.close
                if price is None or math.isnan(price):
                    continue

                prev_close = ticker.close
                if not prev_close or math.isnan(prev_close) or prev_close <= 0:
                    continue
                gap_pct = (price - prev_close) / prev_close * 100

                avg_volume = self._get_avg_volume(contract)
                today_volume = ticker.volume or 0
                rel_volume = (today_volume / avg_volume) if avg_volume else 0

                float_shares = self._get_float_shares(contract)

                self.ib.cancelMktData(contract)

                if not (SCANNER.price_min <= price <= SCANNER.price_max):
                    continue
                if gap_pct < SCANNER.gap_up_pct_min:
                    continue
                if rel_volume < SCANNER.rel_volume_min:
                    continue
                if float_shares is not None and float_shares > SCANNER.float_shares_max:
                    continue

                results.append(ScanResult(
                    symbol=sym, price=price, gap_pct=gap_pct,
                    rel_volume=rel_volume, float_shares=float_shares,
                    avg_volume=avg_volume,
                ))
            except Exception as e:
                log.warning(f"處理 {sym} 時出錯，跳過: {e}")
                continue

        log.info(f"二次過濾後符合 5 核心條件: {[r.symbol for r in results]}")
        return results

    def _get_avg_volume(self, contract) -> float:
        bars = self.ib.reqHistoricalData(
            contract, endDateTime="", durationStr="10 D",
            barSizeSetting="1 day", whatToShow="TRADES", useRTH=True,
        )
        if not bars:
            return 0
        vols = [b.volume for b in bars if b.volume]
        return sum(vols) / len(vols) if vols else 0

    def _get_float_shares(self, contract) -> float | None:
        try:
            data = self.ib.reqFundamentalData(contract, "ReportSnapshot")
            if not data:
                return None
            import re
            match = re.search(r"SharesFloat[^>]*>([\d.]+)", data)
            if match:
                return float(match.group(1))
        except Exception:
            pass
        return None
