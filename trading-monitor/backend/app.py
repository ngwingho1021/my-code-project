"""
Trading Monitor API - 實時監控服務後端
用FastAPI提供REST API + 每日郵件報告
"""

from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo
import json
import os
import asyncio
from typing import Optional
import secrets
import logging

# ── 郵件相關 ────────────────────────────────────────────────────
try:
    import aiosmtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
except ImportError:
    aiosmtplib = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Trading Monitor API", version="1.0.0")

# ── CORS配置（允許Vercel前端訪問）────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "https://trading-monitor.vercel.app",
        os.environ.get("FRONTEND_URL", ""),
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── 認證 ────────────────────────────────────────────────────────
security = HTTPBasic()

DASHBOARD_PASSWORD = os.environ.get("DASHBOARD_PASSWORD", "monitor123")


def verify_password(credentials: HTTPBasicCredentials = Depends(security)):
    """驗證密碼"""
    # 簡單驗證（用戶名任意，密碼為DASHBOARD_PASSWORD）
    correct_password = secrets.compare_digest(
        credentials.password,
        DASHBOARD_PASSWORD
    )
    if not correct_password:
        raise HTTPException(
            status_code=401,
            detail="Invalid password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials


# ── 數據模型 ────────────────────────────────────────────────────
class TradeRecord(BaseModel):
    date: str
    time: str
    symbol: str
    channel: str
    pattern: str
    entry: float
    exit: float
    shares: int
    pnl: float
    pnl_pct: float


class DashboardMetrics(BaseModel):
    """Dashboard 主要指標"""
    daily_pnl: float
    weekly_pnl: float
    total_trades: int
    win_rate: float
    winning_trades: int
    losing_trades: int
    max_drawdown: float
    avg_win: float
    avg_loss: float
    profit_factor: float
    active_positions: int
    daily_peak_pnl: float
    daily_loss_limit: float
    risk_status: str


class PositionDetail(BaseModel):
    """持倉詳情"""
    symbol: str
    shares: int
    entry_price: float
    current_price: float
    unrealized_pnl: float
    pnl_pct: float
    entry_time: str


# ── 數據讀取函數 ────────────────────────────────────────────────
def get_est_now() -> datetime:
    """取得美東時間"""
    return datetime.now(ZoneInfo('America/New_York'))


def load_trade_log() -> list:
    """讀取daily_trade_log.json"""
    log_file = 'daily_trade_log.json'
    if not os.path.exists(log_file):
        return []
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            return json.load(f) or []
    except Exception as e:
        logger.error(f"讀取交易日誌失敗: {e}")
        return []


def load_risk_tracker() -> dict:
    """讀取weekly_risk_tracker.json"""
    tracker_file = 'weekly_risk_tracker.json'
    if not os.path.exists(tracker_file):
        return {}
    try:
        with open(tracker_file, 'r', encoding='utf-8') as f:
            return json.load(f) or {}
    except Exception as e:
        logger.error(f"讀取風控追蹤失敗: {e}")
        return {}


def calculate_metrics(trades: list) -> dict:
    """計算績效指標"""
    if not trades:
        return {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'win_rate': 0.0,
            'total_pnl': 0.0,
            'avg_win': 0.0,
            'avg_loss': 0.0,
            'profit_factor': 0.0,
            'max_drawdown': 0.0,
        }

    total_pnl = sum(t.get('pnl', 0) for t in trades)
    wins = [t for t in trades if t.get('pnl', 0) > 0]
    losses = [t for t in trades if t.get('pnl', 0) < 0]

    winning_pnl = sum(t.get('pnl', 0) for t in wins)
    losing_pnl = sum(t.get('pnl', 0) for t in losses)

    avg_win = winning_pnl / len(wins) if wins else 0.0
    avg_loss = losing_pnl / len(losses) if losses else 0.0
    profit_factor = abs(winning_pnl / losing_pnl) if losing_pnl != 0 else 0.0

    # 最大回撤（簡化計算）
    max_drawdown = 0.0
    cumulative = 0.0
    peak = 0.0
    for t in trades:
        cumulative += t.get('pnl', 0)
        if cumulative > peak:
            peak = cumulative
        drawdown = peak - cumulative
        max_drawdown = max(max_drawdown, drawdown)

    return {
        'total_trades': len(trades),
        'winning_trades': len(wins),
        'losing_trades': len(losses),
        'win_rate': len(wins) / len(trades) * 100 if trades else 0.0,
        'total_pnl': total_pnl,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'profit_factor': profit_factor,
        'max_drawdown': max_drawdown,
    }


# ── API 端點 ────────────────────────────────────────────────────

@app.get("/api/health")
async def health_check():
    """健康檢查"""
    return {"status": "ok", "timestamp": get_est_now().isoformat()}


@app.get("/api/metrics", response_model=DashboardMetrics)
async def get_metrics(credentials: HTTPBasicCredentials = Depends(verify_password)):
    """取得Dashboard指標"""
    trades = load_trade_log()
    risk_data = load_risk_tracker()
    est_now = get_est_now()
    today_str = date.today().isoformat()

    # 篩選今日交易
    today_trades = [t for t in trades if t.get('date') == today_str]
    today_metrics = calculate_metrics(today_trades)

    # 本週交易
    current_year, current_week, _ = date.today().isocalendar()
    weekly_data = risk_data.get('daily', {})
    weekly_pnl = sum(
        v for k, v in weekly_data.items()
        if date.fromisoformat(k).isocalendar()[:2] == (current_year, current_week)
    )

    # 讀取風控上限
    MAX_DAILY_LOSS = 300.0
    daily_pnl = today_metrics['total_pnl']

    # 讀取峰值PnL
    peak_key = f'peak_pnl_{today_str}'
    peak_pnl = risk_data.get(peak_key, max(daily_pnl, 0.0))

    return DashboardMetrics(
        daily_pnl=daily_pnl,
        weekly_pnl=weekly_pnl,
        total_trades=today_metrics['total_trades'],
        win_rate=today_metrics['win_rate'],
        winning_trades=today_metrics['winning_trades'],
        losing_trades=today_metrics['losing_trades'],
        max_drawdown=today_metrics['max_drawdown'],
        avg_win=today_metrics['avg_win'],
        avg_loss=today_metrics['avg_loss'],
        profit_factor=today_metrics['profit_factor'],
        active_positions=0,  # 需要從IBKR讀取
        daily_peak_pnl=peak_pnl,
        daily_loss_limit=MAX_DAILY_LOSS,
        risk_status="✅ 正常" if daily_pnl > -MAX_DAILY_LOSS else "🚨 風控熔斷",
    )


@app.get("/api/trades")
async def get_trades(
    days: int = 1,
    credentials: HTTPBasicCredentials = Depends(verify_password)
):
    """取得交易紀錄（最近N天）"""
    trades = load_trade_log()

    # 篩選日期
    if days > 0:
        target_date = date.today() - timedelta(days=days-1)
        trades = [
            t for t in trades
            if date.fromisoformat(t.get('date', '')) >= target_date
        ]

    return {
        "total": len(trades),
        "trades": trades[-50:],  # 最多回傳50筆
    }


@app.get("/api/trades/summary")
async def get_trades_summary(
    days: int = 7,
    credentials: HTTPBasicCredentials = Depends(verify_password)
):
    """取得交易統計（按日期分組）"""
    trades = load_trade_log()

    # 篩選日期
    if days > 0:
        target_date = date.today() - timedelta(days=days-1)
        trades = [
            t for t in trades
            if date.fromisoformat(t.get('date', '')) >= target_date
        ]

    # 按日期分組
    summary = {}
    for t in trades:
        date_str = t.get('date', '')
        if date_str not in summary:
            summary[date_str] = {
                'date': date_str,
                'trades': 0,
                'pnl': 0.0,
                'wins': 0,
                'losses': 0,
            }
        summary[date_str]['trades'] += 1
        summary[date_str]['pnl'] += t.get('pnl', 0)
        if t.get('pnl', 0) > 0:
            summary[date_str]['wins'] += 1
        else:
            summary[date_str]['losses'] += 1

    return {
        "summary": [summary[k] for k in sorted(summary.keys())],
    }


@app.get("/api/statistics")
async def get_statistics(
    days: int = 30,
    credentials: HTTPBasicCredentials = Depends(verify_password)
):
    """取得詳細統計"""
    trades = load_trade_log()
    risk_data = load_risk_tracker()

    # 篩選日期
    if days > 0:
        target_date = date.today() - timedelta(days=days-1)
        trades = [
            t for t in trades
            if date.fromisoformat(t.get('date', '')) >= target_date
        ]

    metrics = calculate_metrics(trades)

    # 按channel分類
    channel_stats = {}
    for t in trades:
        ch = t.get('channel', 'unknown')
        if ch not in channel_stats:
            channel_stats[ch] = {'trades': 0, 'pnl': 0.0, 'wins': 0}
        channel_stats[ch]['trades'] += 1
        channel_stats[ch]['pnl'] += t.get('pnl', 0)
        if t.get('pnl', 0) > 0:
            channel_stats[ch]['wins'] += 1

    # 按pattern分類
    pattern_stats = {}
    for t in trades:
        pt = t.get('pattern', 'unknown')
        if pt not in pattern_stats:
            pattern_stats[pt] = {'trades': 0, 'pnl': 0.0, 'wins': 0}
        pattern_stats[pt]['trades'] += 1
        pattern_stats[pt]['pnl'] += t.get('pnl', 0)
        if t.get('pnl', 0) > 0:
            pattern_stats[pt]['wins'] += 1

    return {
        **metrics,
        "channel_stats": channel_stats,
        "pattern_stats": pattern_stats,
        "risk_data": risk_data,
    }


# ── 每日郵件報告 ────────────────────────────────────────────────

async def send_daily_email_report(
    recipient_email: str,
    trades: list,
    metrics: dict,
    risk_data: dict,
):
    """發送每日郵件報告"""
    if not aiosmtplib or not os.environ.get("SMTP_PASSWORD"):
        logger.warning("郵件服務未配置，跳過發送")
        return

    est_now = get_est_now()
    today_str = date.today().isoformat()

    # 構建郵件內容
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: 'Segoe UI', Arial; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; }}
            .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                       color: white; padding: 20px; border-radius: 8px 8px 0 0; }}
            .content {{ background: #f9f9f9; padding: 20px; }}
            .metric {{ display: inline-block; width: 48%; margin: 10px 1%;
                       background: white; padding: 15px; border-radius: 8px;
                       box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
            .metric-value {{ font-size: 24px; font-weight: bold; color: #667eea; }}
            .metric-label {{ font-size: 12px; color: #999; margin-top: 5px; }}
            .positive {{ color: #10b981; }}
            .negative {{ color: #ef4444; }}
            .section {{ margin: 20px 0; }}
            .section-title {{ font-size: 16px; font-weight: bold;
                             border-bottom: 2px solid #667eea; padding-bottom: 10px; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
            th, td {{ text-align: left; padding: 10px; border-bottom: 1px solid #ddd; }}
            th {{ background: #f0f0f0; font-weight: bold; }}
            tr:hover {{ background: #f9f9f9; }}
            .footer {{ background: #f0f0f0; padding: 15px; text-align: center;
                       font-size: 12px; color: #999; border-radius: 0 0 8px 8px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2>📊 AI Trading Bot - 每日報告</h2>
                <p>日期: {today_str} | 生成時間: {est_now.strftime('%H:%M:%S %Z')}</p>
            </div>
            <div class="content">
                <div class="section">
                    <div class="metric">
                        <div class="metric-value {'positive' if metrics['total_pnl'] >= 0 else 'negative'}">
                            ${metrics['total_pnl']:.2f}
                        </div>
                        <div class="metric-label">今日P&L</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value">{metrics['win_rate']:.1f}%</div>
                        <div class="metric-label">勝率</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value">{metrics['total_trades']}</div>
                        <div class="metric-label">成交筆數</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value">{metrics['winning_trades']}-{metrics['losing_trades']}</div>
                        <div class="metric-label">勝-負</div>
                    </div>
                </div>

                <div class="section">
                    <div class="section-title">📈 績效指標</div>
                    <div class="metric">
                        <div class="metric-value">${metrics['avg_win']:.2f}</div>
                        <div class="metric-label">平均勝利</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value">${abs(metrics['avg_loss']):.2f}</div>
                        <div class="metric-label">平均虧損</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value">{metrics['profit_factor']:.2f}</div>
                        <div class="metric-label">利潤因子</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value">${metrics['max_drawdown']:.2f}</div>
                        <div class="metric-label">最大回撤</div>
                    </div>
                </div>

                <div class="section">
                    <div class="section-title">📜 今日成交紀錄</div>
                    <table>
                        <tr>
                            <th>時間</th>
                            <th>股票</th>
                            <th>數量</th>
                            <th>進場</th>
                            <th>出場</th>
                            <th>P&L</th>
                        </tr>
                        {''.join(f'''
                        <tr>
                            <td>{t.get("time", "")}</td>
                            <td>{t.get("symbol", "")}</td>
                            <td>{t.get("shares", 0)}</td>
                            <td>${t.get("entry", 0):.2f}</td>
                            <td>${t.get("exit", 0):.2f}</td>
                            <td class="{'positive' if t.get("pnl", 0) >= 0 else 'negative'}">
                                ${t.get("pnl", 0):.2f}
                            </td>
                        </tr>
                        ''' for t in trades[:20])}
                    </table>
                </div>

                <div class="section">
                    <div class="section-title">🛡️ 風控狀態</div>
                    <p><strong>每日上限:</strong> -$300.00</p>
                    <p><strong>當前P&L:</strong> <span class="{'positive' if metrics['total_pnl'] >= 0 else 'negative'}">
                        ${metrics['total_pnl']:.2f}
                    </span></p>
                    <p><strong>狀態:</strong> ✅ 正常</p>
                </div>
            </div>
            <div class="footer">
                <p>🤖 AI Trading Bot Monitor | Real-time Dashboard: https://trading-monitor.vercel.app</p>
                <p>此郵件由自動系統生成 | Generated by Automated System</p>
            </div>
        </div>
    </body>
    </html>
    """

    # 發送郵件
    try:
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart

        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"【AI交易機器人】每日報告 - {today_str}"
        msg['From'] = os.environ.get("SMTP_FROM", "noreply@trading-monitor.app")
        msg['To'] = recipient_email

        msg.attach(MIMEText(html_content, 'html'))

        async with aiosmtplib.SMTP(
            hostname=os.environ.get("SMTP_HOST", "smtp.gmail.com"),
            port=int(os.environ.get("SMTP_PORT", "587")),
        ) as smtp:
            await smtp.login(
                os.environ.get("SMTP_USER", ""),
                os.environ.get("SMTP_PASSWORD", "")
            )
            await smtp.send_message(msg)

        logger.info(f"郵件已發送到 {recipient_email}")

    except Exception as e:
        logger.error(f"發送郵件失敗: {e}")


@app.post("/api/send-daily-report")
async def send_daily_report(
    background_tasks: BackgroundTasks,
    credentials: HTTPBasicCredentials = Depends(verify_password),
):
    """手動觸發每日報告"""
    email = os.environ.get("REPORT_EMAIL", "")
    if not email:
        raise HTTPException(status_code=400, detail="未配置郵件地址")

    trades = load_trade_log()
    today_str = date.today().isoformat()
    today_trades = [t for t in trades if t.get('date') == today_str]
    metrics = calculate_metrics(today_trades)
    risk_data = load_risk_tracker()

    background_tasks.add_task(send_daily_email_report, email, today_trades, metrics, risk_data)

    return {"message": "郵件報告已排隊發送"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
