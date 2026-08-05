"""
用 IBKR 自帶新聞 feed 判斷隻股票係咪有「催化劑」(catalyst)。
IBKR 新聞源要喺 TWS -> Global Configuration -> News 入面訂閱（大部分 Broad Tape 免費）。
"""
import re
from dataclasses import dataclass

from utils.logger import get_logger

log = get_logger("news")

CATALYST_KEYWORDS = [
    "fda", "approval", "clinical", "trial", "phase", "merger", "acquisition",
    "acquire", "partnership", "contract", "earnings", "beat", "guidance",
    "upgrade", "buyout", "patent", "offering", "uplist", "spin-off",
    "record revenue", "breakthrough", "award", "outbreak", "recall",
    "short squeeze", "reverse split", "ceo", "resign", "sec", "investigation",
]


@dataclass
class CatalystInfo:
    symbol: str
    has_catalyst: bool
    headlines: list[str]


class NewsChecker:
    def __init__(self, ib):
        self.ib = ib

    def get_catalyst(self, symbol: str, contract, lookback_hours: int = 20) -> CatalystInfo:
        headlines: list[str] = []
        try:
            providers = self.ib.reqNewsProviders()
            codes = "+".join(p.code for p in providers) if providers else ""
            articles = self.ib.reqHistoricalNews(
                contract.conId, codes, "", "", 20
            )
            for a in articles:
                headlines.append(a.headline)
        except Exception as e:
            log.warning(f"{symbol} 攞新聞出錯: {e}")

        has_catalyst = any(self._matches_keyword(h) for h in headlines)
        return CatalystInfo(symbol=symbol, has_catalyst=has_catalyst, headlines=headlines)

    @staticmethod
    def _matches_keyword(headline: str) -> bool:
        h = headline.lower()
        return any(re.search(rf"\b{kw}\b", h) for kw in CATALYST_KEYWORDS)
