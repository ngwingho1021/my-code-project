import React, { useState, useEffect } from 'react';
import { BarChart, Bar, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { apiClient } from '../utils/api';
import '../styles/Statistics.css';

function Statistics() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [days, setDays] = useState(30);

  useEffect(() => {
    fetchStatistics();
  }, [days]);

  const fetchStatistics = async () => {
    try {
      setLoading(true);
      const res = await apiClient.get(`/api/statistics?days=${days}`);
      setStats(res.data);
      setError(null);
    } catch (err) {
      setError(err.message || '無法載入統計數據');
      console.error('Statistics error:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="statistics"><div className="loading">載入中...</div></div>;
  }

  if (error || !stats) {
    return (
      <div className="statistics">
        <div className="error-box">
          <p>{error || '無法載入統計數據'}</p>
          <button onClick={fetchStatistics}>重新載入</button>
        </div>
      </div>
    );
  }

  // 準備通道統計數據
  const channelData = Object.entries(stats.channel_stats || {}).map(([key, val]) => ({
    name: key === 'main' ? '📡 主通道' : '⚡ Spike',
    trades: val.trades,
    pnl: val.pnl,
    wins: val.wins,
  }));

  // 準備形態統計數據
  const patternData = Object.entries(stats.pattern_stats || {}).map(([key, val]) => ({
    name: key,
    trades: val.trades,
    pnl: val.pnl,
    wins: val.wins,
  }));

  // 圓餅圖顏色
  const COLORS = ['#667eea', '#764ba2', '#f093fb', '#4facfe', '#00f2fe'];

  return (
    <div className="statistics">
      <div className="header">
        <h2>📈 統計分析</h2>
        <div className="filter-buttons">
          <button
            className={days === 7 ? 'active' : ''}
            onClick={() => setDays(7)}
          >
            7天
          </button>
          <button
            className={days === 30 ? 'active' : ''}
            onClick={() => setDays(30)}
          >
            30天
          </button>
          <button
            className={days === 90 ? 'active' : ''}
            onClick={() => setDays(90)}
          >
            90天
          </button>
        </div>
      </div>

      {/* 核心指標 */}
      <div className="metrics-summary">
        <div className="metric-item">
          <div className="label">總成交</div>
          <div className="value">{stats.total_trades}</div>
        </div>
        <div className="metric-item">
          <div className="label">勝率</div>
          <div className="value">{stats.win_rate.toFixed(1)}%</div>
        </div>
        <div className="metric-item">
          <div className="label">總P&L</div>
          <div className={`value ${stats.total_pnl >= 0 ? 'positive' : 'negative'}`}>
            ${stats.total_pnl.toFixed(2)}
          </div>
        </div>
        <div className="metric-item">
          <div className="label">利潤因子</div>
          <div className="value">{stats.profit_factor.toFixed(2)}</div>
        </div>
        <div className="metric-item">
          <div className="label">最大回撤</div>
          <div className="value">${stats.max_drawdown.toFixed(2)}</div>
        </div>
        <div className="metric-item">
          <div className="label">平均勝利</div>
          <div className="value positive">${stats.avg_win.toFixed(2)}</div>
        </div>
        <div className="metric-item">
          <div className="label">平均虧損</div>
          <div className="value negative">${Math.abs(stats.avg_loss).toFixed(2)}</div>
        </div>
      </div>

      {/* 圖表區塊 */}
      <div className="charts-section">
        {/* 通道分析 */}
        <div className="chart-container">
          <h3>通道成交分佈</h3>
          {channelData.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={channelData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Bar dataKey="trades" fill="#667eea" name="成交筆數" />
                <Bar dataKey="wins" fill="#10b981" name="勝利筆數" />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <p>暫無數據</p>
          )}
        </div>

        {/* 通道P&L分析 */}
        <div className="chart-container">
          <h3>通道P&L分析</h3>
          {channelData.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={channelData.filter(d => d.pnl > 0)}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, pnl }) => `${name}: $${pnl.toFixed(0)}`}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="pnl"
                >
                  {channelData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip formatter={(value) => `$${value.toFixed(2)}`} />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <p>暫無盈利數據</p>
          )}
        </div>
      </div>

      {/* 形態統計表格 */}
      <div className="table-section">
        <h3>形態成交統計</h3>
        {patternData.length > 0 ? (
          <table className="stats-table">
            <thead>
              <tr>
                <th>形態</th>
                <th>成交筆數</th>
                <th>勝利筆數</th>
                <th>勝率</th>
                <th>總P&L</th>
                <th>平均P&L</th>
              </tr>
            </thead>
            <tbody>
              {patternData.map((pattern, idx) => (
                <tr key={idx}>
                  <td>{pattern.name}</td>
                  <td>{pattern.trades}</td>
                  <td>{pattern.wins}</td>
                  <td>{((pattern.wins / pattern.trades) * 100).toFixed(1)}%</td>
                  <td className={pattern.pnl >= 0 ? 'positive' : 'negative'}>
                    ${pattern.pnl.toFixed(2)}
                  </td>
                  <td className={pattern.pnl / pattern.trades >= 0 ? 'positive' : 'negative'}>
                    ${(pattern.pnl / pattern.trades).toFixed(2)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p>暫無數據</p>
        )}
      </div>

      {/* 通道統計表格 */}
      <div className="table-section">
        <h3>通道成交統計</h3>
        <table className="stats-table">
          <thead>
            <tr>
              <th>通道</th>
              <th>成交筆數</th>
              <th>勝利筆數</th>
              <th>勝率</th>
              <th>總P&L</th>
              <th>平均P&L</th>
            </tr>
          </thead>
          <tbody>
            {channelData.map((channel, idx) => (
              <tr key={idx}>
                <td>{channel.name}</td>
                <td>{channel.trades}</td>
                <td>{channel.wins}</td>
                <td>{((channel.wins / channel.trades) * 100).toFixed(1)}%</td>
                <td className={channel.pnl >= 0 ? 'positive' : 'negative'}>
                  ${channel.pnl.toFixed(2)}
                </td>
                <td className={channel.pnl / channel.trades >= 0 ? 'positive' : 'negative'}>
                  ${(channel.pnl / channel.trades).toFixed(2)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default Statistics;
