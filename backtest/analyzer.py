"""回測結果分析 - 生成視覺化報告和統計"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
import numpy as np


class BacktestAnalyzer:
    """
    分析回測結果並生成報告
    - HTML視覺化報告
    - JSON數據導出
    - 風險指標計算
    """

    def __init__(self, report_dir: str = "backtest_reports"):
        self.report_dir = Path(report_dir)
        self.report_dir.mkdir(exist_ok=True)

    def generate_html_report(self, backtest_result: Dict, symbol: str,
                           start_date: str, end_date: str) -> str:
        """生成HTML報告"""

        summary = backtest_result.get("summary", {})
        stats = backtest_result.get("trading_stats", {})
        equity_curve = backtest_result.get("equity_curve", [])

        # 計算風險指標
        metrics = self._calculate_metrics(equity_curve, stats)

        html_content = f"""
        <!DOCTYPE html>
        <html lang="zh-CN">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>回測報告 - {symbol}</title>
            <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/3.9.1/chart.min.js"></script>
            <style>
                * {{
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                }}
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    min-height: 100vh;
                    padding: 20px;
                }}
                .container {{
                    max-width: 1200px;
                    margin: 0 auto;
                    background: white;
                    border-radius: 12px;
                    box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                    padding: 40px;
                }}
                h1 {{
                    color: #667eea;
                    margin-bottom: 10px;
                    font-size: 2em;
                }}
                .subtitle {{
                    color: #666;
                    margin-bottom: 30px;
                    font-size: 0.95em;
                }}
                .section {{
                    margin-bottom: 40px;
                }}
                .section-title {{
                    font-size: 1.3em;
                    color: #764ba2;
                    margin-bottom: 20px;
                    border-bottom: 2px solid #667eea;
                    padding-bottom: 10px;
                }}
                .metrics-grid {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                    gap: 20px;
                    margin-bottom: 30px;
                }}
                .metric-card {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 20px;
                    border-radius: 8px;
                    box-shadow: 0 4px 15px rgba(0,0,0,0.1);
                }}
                .metric-label {{
                    font-size: 0.85em;
                    opacity: 0.9;
                    margin-bottom: 5px;
                }}
                .metric-value {{
                    font-size: 1.5em;
                    font-weight: bold;
                }}
                .positive {{
                    color: #10b981;
                }}
                .negative {{
                    color: #ef4444;
                }}
                .neutral {{
                    color: #f59e0b;
                }}
                .chart-container {{
                    position: relative;
                    height: 400px;
                    margin-bottom: 40px;
                }}
                .stats-table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin-bottom: 20px;
                }}
                .stats-table th {{
                    background: #667eea;
                    color: white;
                    padding: 12px;
                    text-align: left;
                    font-weight: 600;
                }}
                .stats-table td {{
                    padding: 12px;
                    border-bottom: 1px solid #eee;
                }}
                .stats-table tr:hover {{
                    background: #f5f5f5;
                }}
                .footer {{
                    margin-top: 40px;
                    padding-top: 20px;
                    border-top: 1px solid #eee;
                    color: #999;
                    font-size: 0.9em;
                    text-align: center;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>📊 回測報告</h1>
                <p class="subtitle">{symbol} | {start_date} 至 {end_date}</p>

                <!-- 總體績效 -->
                <div class="section">
                    <div class="section-title">📈 總體績效</div>
                    <div class="metrics-grid">
                        <div class="metric-card">
                            <div class="metric-label">初始資本</div>
                            <div class="metric-value">${summary.get('initial_capital', 0):,.2f}</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-label">最終淨值</div>
                            <div class="metric-value">${summary.get('final_equity', 0):,.2f}</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-label">淨收益</div>
                            <div class="metric-value {self._get_class(summary.get('total_return', 0))}">${summary.get('total_return', 0):,.2f}</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-label">回報率</div>
                            <div class="metric-value {self._get_class(summary.get('total_return_pct', 0))}">{summary.get('total_return_pct', 0):.2f}%</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-label">最大回撤</div>
                            <div class="metric-value negative">{summary.get('max_drawdown_pct', 0):.2f}%</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-label">夏普比率</div>
                            <div class="metric-value">{metrics.get('sharpe_ratio', 0):.2f}</div>
                        </div>
                    </div>
                </div>

                <!-- 交易統計 -->
                <div class="section">
                    <div class="section-title">📊 交易統計</div>
                    <div class="metrics-grid">
                        <div class="metric-card">
                            <div class="metric-label">總交易數</div>
                            <div class="metric-value">{stats.get('total_trades', 0)}</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-label">勝利交易</div>
                            <div class="metric-value positive">{stats.get('winning_trades', 0)}</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-label">失敗交易</div>
                            <div class="metric-value negative">{stats.get('losing_trades', 0)}</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-label">勝率</div>
                            <div class="metric-value positive">{stats.get('win_rate', 0):.1f}%</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-label">平均盈利</div>
                            <div class="metric-value positive">${stats.get('total_profit', 0):,.2f}</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-label">平均虧損</div>
                            <div class="metric-value negative">${stats.get('total_loss', 0):,.2f}</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-label">單筆平均損益</div>
                            <div class="metric-value {self._get_class(stats.get('avg_trade_pnl', 0))}">${stats.get('avg_trade_pnl', 0):,.2f}</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-label">最大單筆盈利</div>
                            <div class="metric-value positive">${stats.get('largest_win', 0):,.2f}</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-label">最大單筆虧損</div>
                            <div class="metric-value negative">${stats.get('largest_loss', 0):,.2f}</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-label">平均持倉時間</div>
                            <div class="metric-value">{stats.get('avg_holding_time_minutes', 0)} 分鐘</div>
                        </div>
                    </div>
                </div>

                <!-- 淨值曲線 -->
                <div class="section">
                    <div class="section-title">📈 淨值曲線</div>
                    <div class="chart-container">
                        <canvas id="equityChart"></canvas>
                    </div>
                </div>

                <!-- 月度收益 (如果有足夠數據) -->
                <div class="section" id="monthly-section" style="display: none;">
                    <div class="section-title">📅 月度收益</div>
                    <div class="chart-container">
                        <canvas id="monthlyChart"></canvas>
                    </div>
                </div>

                <div class="footer">
                    Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} |
                    Pre-Market Gap-Up Momentum Trading System
                </div>
            </div>

            <script>
                // 淨值曲線
                const equityData = {json.dumps([e[1] for e in equity_curve])};
                const equityDates = {json.dumps([str(e[0]) for e in equity_curve])};

                const equityCtx = document.getElementById('equityChart').getContext('2d');
                new Chart(equityCtx, {{
                    type: 'line',
                    data: {{
                        labels: equityDates,
                        datasets: [{{
                            label: '賬戶淨值',
                            data: equityData,
                            borderColor: '#667eea',
                            backgroundColor: 'rgba(102, 126, 234, 0.1)',
                            borderWidth: 2,
                            fill: true,
                            tension: 0.4,
                            pointRadius: 0,
                            pointHoverRadius: 6,
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {{
                            legend: {{
                                display: true,
                                labels: {{
                                    font: {{ size: 12 }},
                                    color: '#666'
                                }}
                            }}
                        }},
                        scales: {{
                            y: {{
                                beginAtZero: false,
                                ticks: {{
                                    callback: function(value) {{
                                        return '$' + value.toLocaleString();
                                    }}
                                }},
                                grid: {{
                                    color: 'rgba(0,0,0,0.05)'
                                }}
                            }},
                            x: {{
                                display: true,
                                grid: {{
                                    display: false
                                }}
                            }}
                        }}
                    }}
                }});
            </script>
        </body>
        </html>
        """

        # 保存HTML文件
        filename = f"backtest_{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        filepath = self.report_dir / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)

        print(f"\n✅ HTML報告已生成: {filepath}")
        return str(filepath)

    def generate_json_report(self, backtest_result: Dict, symbol: str) -> str:
        """導出JSON報告"""
        filename = f"backtest_{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = self.report_dir / filename

        # 轉換datetime為字符串
        json_result = {
            "symbol": symbol,
            "timestamp": datetime.now().isoformat(),
            "summary": backtest_result.get("summary", {}),
            "trading_stats": backtest_result.get("trading_stats", {}),
            "equity_curve": [
                {"timestamp": str(e[0]), "equity": e[1]}
                for e in backtest_result.get("equity_curve", [])
            ]
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(json_result, f, indent=2, ensure_ascii=False)

        print(f"✅ JSON報告已生成: {filepath}")
        return str(filepath)

    def _calculate_metrics(self, equity_curve: List[tuple], stats: Dict) -> Dict:
        """計算風險指標"""
        if not equity_curve:
            return {"sharpe_ratio": 0.0}

        equities = np.array([e[1] for e in equity_curve])
        returns = np.diff(equities) / equities[:-1]

        # 夏普比率 (假設年化252個交易日)
        daily_return = np.mean(returns)
        daily_std = np.std(returns)

        if daily_std > 0:
            sharpe = (daily_return * 252) / (daily_std * np.sqrt(252))
        else:
            sharpe = 0.0

        return {
            "sharpe_ratio": sharpe,
            "daily_return_mean": np.mean(returns),
            "daily_return_std": np.std(returns),
        }

    def _get_class(self, value: float) -> str:
        """根據數值返回CSS類名"""
        if value > 0:
            return "positive"
        elif value < 0:
            return "negative"
        else:
            return "neutral"
