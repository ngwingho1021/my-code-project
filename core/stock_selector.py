"""
Stock Selection with 5 Pillars (Ross Cameron)
支柱 1: Gap Up (開盤跳空 >= 5%)
支柱 2: 新聞催化劑
支柱 3: Low Float (流通股本 < 20M)
支柱 4: RVOL 大增 (相對成交量 >= 2x)
支柱 5: 股價範圍 ($2-20)
"""
import math
from dataclasses import dataclass
from typing import Optional

from utils.logger import get_logger

log = get_logger("stock_selector")


@dataclass
class StockCandidate:
    """符合5支柱的股票候選"""
    symbol: str
    current_price: float
    prev_close: float
    gap_pct: float

    float_shares: Optional[float]
    rel_volume: float
    avg_volume: float
    today_volume: float

    has_news: bool
    news_headline: Optional[str] = None

    def get_score(self) -> float:
        """計算綜合評分（0-100）"""
        score = 0

        # 支柱1: Gap Up（權重：25分）
        if self.gap_pct >= 10:
            score += 25
        elif self.gap_pct >= 5:
            score += 20
        elif self.gap_pct >= 2:
            score += 10

        # 支柱2: 新聞催化劑（權重：20分）
        if self.has_news:
            score += 20

        # 支柱3: Low Float（權重：20分）
        if self.float_shares and self.float_shares < 10_000_000:
            score += 20
        elif self.float_shares and self.float_shares < 20_000_000:
            score += 15

        # 支柱4: RVOL 大增（權重：20分）
        if self.rel_volume >= 3:
            score += 20
        elif self.rel_volume >= 2:
            score += 15

        # 支柱5: 股價範圍（權重：15分）
        if 2 <= self.current_price <= 20:
            score += 15

        return min(score, 100)

    def passes_filters(self, min_gap: float = 5.0, min_rvol: float = 2.0,
                       require_news: bool = False, require_float: bool = True) -> bool:
        """檢查係咪通過所有篩選條件"""
        # 支柱1: Gap Up
        if self.gap_pct < min_gap:
            return False

        # 支柱4: RVOL
        if self.rel_volume < min_rvol:
            return False

        # 支柱2: 新聞（可選）
        if require_news and not self.has_news:
            return False

        # 支柱3: Low Float
        if require_float and self.float_shares and self.float_shares > 20_000_000:
            return False

        # 支柱5: 股價範圍
        if not (2 <= self.current_price <= 20):
            return False

        return True

    def __str__(self) -> str:
        float_str = f"{self.float_shares/1e6:.1f}M" if self.float_shares else "N/A"
        news_str = f" [新聞: {self.news_headline}]" if self.has_news else ""
        return (f"{self.symbol}: gap={self.gap_pct:.1f}% RVOL={self.rel_volume:.1f}x "
                f"float={float_str} price=${self.current_price:.2f}{news_str}")


class StockSelector:
    """5支柱篩選器"""

    def __init__(self):
        self.min_gap_pct = 5.0          # 最少跳空 5%
        self.min_rvol = 2.0             # 最少相對成交量 2x
        self.min_price = 2.0            # 最低股價
        self.max_price = 20.0           # 最高股價
        self.max_float = 20_000_000     # 最高流通股本 20M
        self.require_news = False       # 新聞係可選的

    def evaluate(self, symbol: str, current_price: float, prev_close: float,
                 today_volume: float, avg_volume: float, float_shares: Optional[float],
                 has_news: bool = False, news_headline: Optional[str] = None) -> Optional[StockCandidate]:
        """評估單隻股票"""

        # 計算 gap %
        if prev_close <= 0:
            log.warning(f"{symbol}: 前收盤價無效 ({prev_close})")
            return None

        gap_pct = (current_price - prev_close) / prev_close * 100

        # 計算相對成交量
        if avg_volume <= 0:
            log.warning(f"{symbol}: 平均成交量無效 ({avg_volume})")
            return None

        rel_volume = today_volume / avg_volume if avg_volume > 0 else 0

        candidate = StockCandidate(
            symbol=symbol,
            current_price=current_price,
            prev_close=prev_close,
            gap_pct=gap_pct,
            float_shares=float_shares,
            rel_volume=rel_volume,
            avg_volume=avg_volume,
            today_volume=today_volume,
            has_news=has_news,
            news_headline=news_headline
        )

        return candidate

    def filter_candidates(self, candidates: list[StockCandidate],
                         strict_mode: bool = False) -> list[StockCandidate]:
        """篩選候選股票"""
        filtered = []

        for candidate in candidates:
            # 寬鬆模式：只要 gap + rvol + 股價範圍
            if not strict_mode:
                if candidate.passes_filters(
                    min_gap=self.min_gap_pct,
                    min_rvol=self.min_rvol,
                    require_news=False,
                    require_float=False
                ):
                    filtered.append(candidate)
            # 嚴格模式：所有支柱都要符合
            else:
                if candidate.passes_filters(
                    min_gap=self.min_gap_pct,
                    min_rvol=self.min_rvol,
                    require_news=self.require_news,
                    require_float=True
                ):
                    filtered.append(candidate)

        # 按評分排序
        filtered.sort(key=lambda c: c.get_score(), reverse=True)

        return filtered

    def rank_candidates(self, candidates: list[StockCandidate], top_n: int = 5) -> list[StockCandidate]:
        """排名前 N 隻"""
        return candidates[:top_n]

    def get_summary(self, candidates: list[StockCandidate]) -> str:
        """生成摘要"""
        if not candidates:
            return "無符合條件的股票"

        summary = f"\n【{len(candidates)} 隻符合 5 支柱的股票】\n"
        for i, c in enumerate(candidates[:10], 1):
            summary += f"{i}. {c} (評分: {c.get_score():.0f}/100)\n"
        return summary
