import React, { useState, useEffect } from 'react';
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { AlertCircle, TrendingUp, TrendingDown, Activity } from 'lucide-react';
import { apiClient } from '../utils/api';
import '../styles/Dashboard.css';

function Dashboard() {
  const [metrics, setMetrics] = useState(null);
  const [tradeSummary, setTradeSummary] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastUpdate, setLastUpdate] = useState(new Date());

  useEffect(() => {
    fetchDashboardData();
    const interval = setInterval(fetchDashboardData, 30000); // 30秒更新一次
    return () => clearInterval(interval);
  }, []);

  const fetchDashboardData = async () => {
    try {
      setError(null);
      const [metricsRes, summaryRes] = await Promise.all([
        apiClient.get('/api/metrics'),
        apiClient.get('/api/trades/summary?days=7'),
      ]);

      setMetrics(metricsRes.data);
      setTradeSummary(summaryRes.data.summary || []);
      setLastUpdate(new Date());
    } catch (err) {
      setError(err.message || '無法載入數據');
      console.error('Dashboard error:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="dashboard">
        <div className="loading">
          <div className="spinner"></div>
          <p>正在載入數據...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="dashboard">
        <div className="error-box">
          <AlertCircle />
          <p>{error}</p>
          <button onClick={fetchDashboardData}>重新載入</button>
        </div>
      </div>
    );
  }

  if (!metrics) {
    return <div className="dashboard"><p>無法載入數據</p></div>;
  }

  const isProfitable = metrics.daily_pnl >= 0;
  const pnlClass = isProfitable ? 'positive' : 'negative';
  const pnlIcon = isProfitable ? <TrendingUp /> : <TrendingDown />;

  return (
    <div className="dashboard">
      {/* 狀態欄 */}
      <div className="status-bar">
        <div className="status-info">
          <span>🟢 即時連線</span>
          <span>|</span>
          <span>更新時間: {lastUpdate.toLocaleTimeString('zh-HK')}</span>
        </div>
        <button className="refresh-btn" onClick={fetchDashboardData}>
          🔄 重新整理
        </button>
      </div>

      {/* 風控狀態警告 */}
      {metrics.risk_status.includes('🚨') && (
        <div className="alert-box warning">
          <AlertCircle />
          <div>
            <strong>⚠️ 風控熔斷</strong>
            <p>{metrics.risk_status}</p>
          </div>
        </div>
      )}

      {/* 主要指標卡片 */}
      <div className="metrics-grid">
        {/* P&L 卡片 */}
        <div className={`metric-card ${pnlClass}`}>
          <div className="card-header">
            <h3>今日 P&L</h3>
            {pnlIcon}
          </div>
          <div className="card-value">
            ${metrics.daily_pnl.toFixed(2)}
          </div>
          <div className="card-detail">
            {metrics.daily_peak_pnl > 0 && (
              <span>峰值: ${metrics.daily_peak_pnl.toFixed(2)}</span>
            )}
            {metrics.daily_loss_limit && (
              <span>上限: -${metrics.daily_loss_limit.toFixed(2)}</span>
            )}
          </div>
        </div>

        {/* 勝率卡片 */}
        <div className="metric-card info">
          <div className="card-header">
            <h3>勝率</h3>
            <Activity />
          </div>
          <div className="card-value">
            {metrics.win_rate.toFixed(1)}%
          </div>
          <div className="card-detail">
            {metrics.winning_trades}勝 / {metrics.losing_trades}負
          </div>
        </div>

        {/* 成交筆數卡片 */}
        <div className="metric-card success">
          <div className="card-header">
            <h3>成交筆數</h3>
            <span className="icon">📊</span>
          </div>
          <div className="card-value">
            {metrics.total_trades}
          </div>
          <div className="card-detail">
            今日交易
          </div>
        </div>

        {/* 利潤因子卡片 */}
        <div className="metric-card">
          <div className="card-header">
            <h3>利潤因子</h3>
            <span className="icon">💰</span>
          </div>
          <div className="card-value">
            {metrics.profit_factor.toFixed(2)}
          </div>
          <div className="card-detail">
            勝利/虧損比
          </div>
        </div>

        {/* 最大回撤卡片 */}
        <div className="metric-card">
          <div className="card-header">
            <h3>最大回撤</h3>
            <span className="icon">📉</span>
          </div>
          <div className="card-value">
            ${metrics.max_drawdown.toFixed(2)}
          </div>
          <div className="card-detail">
            峰值到谷底
          </div>
        </div>

        {/* 平均勝利卡片 */}
        <div className="metric-card positive">
          <div className="card-header">
            <h3>平均勝利</h3>
            <TrendingUp />
          </div>
          <div className="card-value">
            ${metrics.avg_win.toFixed(2)}
          </div>
          <div className="card-detail">
            每筆平均盈利
          </div>
        </div>

        {/* 平均虧損卡片 */}
        <div className="metric-card negative">
          <div className="card-header">
            <h3>平均虧損</h3>
            <TrendingDown />
          </div>
          <div className="card-value">
            ${Math.abs(metrics.avg_loss).toFixed(2)}
          </div>
          <div className="card-detail">
            每筆平均損失
          </div>
        </div>

        {/* 本週P&L卡片 */}
        <div className={`metric-card ${metrics.weekly_pnl >= 0 ? 'positive' : 'negative'}`}>
          <div className="card-header">
            <h3>本週 P&L</h3>
            <span className="icon">📅</span>
          </div>
          <div className="card-value">
            ${metrics.weekly_pnl.toFixed(2)}
          </div>
          <div className="card-detail">
            累計收益
          </div>
        </div>
      </div>

      {/* 圖表區塊 */}
      <div className="charts-container">
        {/* P&L走勢圖 */}
        <div className="chart-box">
          <h3>7天 P&L 走勢</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={tradeSummary}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" />
              <YAxis />
              <Tooltip
                contentStyle={{ backgroundColor: '#1a1a2e', border: '1px solid #667eea' }}
                formatter={(value) => `$${value.toFixed(2)}`}
              />
              <Legend />
              <Bar
                dataKey="pnl"
                fill="#667eea"
                radius={[8, 8, 0, 0]}
                name="每日P&L"
              />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* 交易次數趨勢 */}
        <div className="chart-box">
          <h3>7天成交趨勢</h3>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={tradeSummary}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" />
              <YAxis />
              <Tooltip
                contentStyle={{ backgroundColor: '#1a1a2e', border: '1px solid #667eea' }}
              />
              <Legend />
              <Line
                type="monotone"
                dataKey="trades"
                stroke="#667eea"
                name="成交筆數"
                strokeWidth={2}
              />
              <Line
                type="monotone"
                dataKey="wins"
                stroke="#10b981"
                name="勝利筆數"
                strokeWidth={2}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* 詳細指標表格 */}
      <div className="details-box">
        <h3>詳細指標</h3>
        <div className="details-grid">
          <div className="detail-item">
            <span className="label">風控狀態</span>
            <span className="value">{metrics.risk_status}</span>
          </div>
          <div className="detail-item">
            <span className="label">現有持倉</span>
            <span className="value">{metrics.active_positions} 隻</span>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Dashboard;
