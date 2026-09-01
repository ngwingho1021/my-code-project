"""
全部策略/風控參數集中喺呢度。唔識code都可以安全咁改呢個檔案入面嘅數值。
"""
import os
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# IBKR 連線設定
# ---------------------------------------------------------------------------
IB_HOST = os.getenv("IB_HOST", "127.0.0.1")
IB_PORT = int(os.getenv("IB_PORT", "7497"))       # 7497 = TWS Paper, 7496 = TWS Live
                                                    # 4002 = IB Gateway Paper, 4001 = IB Gateway Live
IB_CLIENT_ID = int(os.getenv("IB_CLIENT_ID", "17"))

PAPER_TRADING = True   # 一定要保持 True，直至你完全信得過個系統為止


@dataclass
class AccountRisk:
    account_size: float = 5000.0
    max_trades_per_day: int = 12
    max_concurrent_positions: int = 4   # HARD LIMIT: 最多 4 個位（靠 IBKR 實時查詢）
    max_loss_per_trade: float = 100.0
    max_loss_per_day: float = 300.0
    max_loss_per_week: float = 800.0
    # 單一持倉最多用幾多百分比本金（避免一注獨大）
    max_position_pct_of_account: float = 0.35
    # 防止 scanner 發瘋：只掃描呢啲特定股票
    scan_only_symbols: list = None  # None = 動態掃描; 或設做 ['NVDA','AMD',...] 用手控名單


@dataclass
class ScannerCriteria:
    price_min: float = 2.0
    price_max: float = 20.0
    float_shares_max: float = 20_000_000
    gap_up_pct_min: float = 5.0           # 入場時最低 gap%（允許由高位略為回落）
    watchlist_min_gap_pct: float = 10.0   # 加入監控名單最低 gap%（只追最強動能）
    rel_volume_min: float = 2.0
    min_avg_volume: float = 300_000      # 過濾完全冇流動性嘅股
    require_catalyst: bool = False        # False = 冇新聞都可以進場（只係降低信心分）
    max_drop_from_high_pct: float = 0.20  # 現價距日高超過 20% = 動能已過，唔入場
    # 唔交易呢類證券（ETF/ETN、SPAC unit/warrant/rights）
    banned_symbols: tuple = ('DGZ', 'GDXD', 'GLDX', 'JDST', 'DUST', 'NUGT', 'UVXY', 'SQQQ', 'TQQQ')
    banned_suffixes: tuple = ('U', 'W', 'WS', 'R')  # SPAC unit/warrant/rights 後綴


@dataclass
class StrategyParams:
    # K 線設定
    primary_bar_size: str = "1 min"
    micro_bar_size: str = "10 secs"

    # MACD 參數（用喺 1 分鐘圖）
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9

    # VWAP
    require_price_above_vwap: bool = True
    vwap_buffer_pct: float = 0.0   # 價需要高於 vwap 幾多 % 先當「穩守」

    # Micro pullback 定義
    pullback_lookback_bars: int = 5
    pullback_max_retrace_pct: float = 0.5   # 拉回幅度唔可以超過前一段升浪嘅 50%

    # Topping tail / 動能衰減偵測
    topping_tail_wick_ratio: float = 0.6     # 上影線佔全根K線幅度 >= 60% 就當 topping tail
    momentum_decay_lookback: int = 3         # 用幾多根 bar 嚟判斷量能/動能係咪衰減

    # 盈虧比
    min_reward_risk_ratio: float = 2.0        # 最少 1:2，理想 1:3
    target_reward_risk_ratio: float = 3.0

    # 分批止盈設定（成交比例）
    profit_take_1_rr: float = 1.0    # 賺到 1R 先食第一批
    profit_take_1_pct: float = 0.5   # 食返 50% 倉位
    profit_take_2_rr: float = 2.0    # 賺到 2R 再食第二批
    profit_take_2_pct: float = 0.3   # 再食 30%
    # 剩低 20% 用 trailing stop 跟到尾

    trailing_stop_pct: float = 0.5    # 尾段用 VWAP / 前低 作 trailing stop 參考百分比

    # 橫行離場（無方向超過 N 分鐘就退場）
    sideways_timeout_min: int = 15        # 持倉幾多分鐘後開始檢查橫行
    sideways_range_pct: float = 0.03     # 高低波幅 < 3% = 橫行


@dataclass
class ExecutionSafety:
    # 防滑價 / 熔斷穿價
    max_slippage_pct: float = 1.5        # 落市價止蝕單前，先check個skip唔會超過呢個百分比
    use_stop_limit_not_stop_market: bool = True
    stop_limit_offset_pct: float = 0.8    # STP LMT 嘅limit价 = stop價 - offset%（沽單）
    halt_poll_interval_sec: int = 2
    resume_confirmation_ticks: int = 3     # 復牌後要連續幾多個報價先確認市場返正常
    resume_max_wait_sec: int = 600         # 熔斷最多等幾耐，過咗就自動棄用呢單（唔會盲追）
    post_halt_volatility_guard_pct: float = 8.0  # 復牌後首幾秒波幅超過呢個%就先觀望


@dataclass
class Level2Params:
    imbalance_lookback_ticks: int = 20
    liquidity_decay_ratio: float = 0.4     # 買盤總量跌到得返高峰嘅 40% 以下 = 流動性衰減
    ask_pull_alert_levels: int = 2          # 監控 top N 檔 ask 消失嘅速度
    tape_speed_window_sec: int = 5          # time & sales 用嚟計「秒速」嘅時間窗


ACCOUNT_RISK = AccountRisk()
SCANNER = ScannerCriteria()
STRATEGY = StrategyParams()
EXEC_SAFETY = ExecutionSafety()
LEVEL2 = Level2Params()

TRADING_HOURS = {
    "premarket_start": "04:00",
    "market_open": "09:30",
    "market_close": "16:00",
    "afterhours_end": "20:00",
    "timezone": "America/New_York",
}

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
