import React, { useState, useEffect } from 'react';
import { apiClient } from '../utils/api';
import '../styles/TradeHistory.css';

function TradeHistory() {
  const [trades, setTrades] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [days, setDays] = useState(1);

  useEffect(() => {
    fetchTrades();
  }, [days]);

  const fetchTrades = async () => {
    try {
      setLoading(true);
      const res = await apiClient.get(`/api/trades?days=${days}`);
      setTrades(res.data.trades || []);
      setError(null);
    } catch (err) {
      setError(err.message || '無法載入成交紀錄');
      console.error('TradeHistory error:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="trade-history"><div className="loading">載入中...</div></div>;
  }

  if (error) {
    return (
      <div className="trade-history">
        <div className="error-box">
          <p>{error}</p>
          <button onClick={fetchTrades}>重新載入</button>
        </div>
      </div>
    );
  }

  return (
    <div className="trade-history">
      <div className="header">
        <h2>📜 成交紀錄</h2>
        <div className="filter-buttons">
          <button
            className={days === 1 ? 'active' : ''}
            onClick={() => setDays(1)}
          >
            今日
          </button>
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
            本月
          </button>
        </div>
      </div>

      {trades.length === 0 ? (
        <div className="empty-state">
          <p>暫無成交紀錄</p>
        </div>
      ) : (
        <div className="trades-table-container">
          <table className="trades-table">
            <thead>
              <tr>
                <th>日期</th>
                <th>時間</th>
                <th>股票</th>
                <th>通道</th>
                <th>形態</th>
                <th>數量</th>
                <th>進場價</th>
                <th>出場價</th>
                <th>P&L</th>
                <th>收益率</th>
              </tr>
            </thead>
            <tbody>
              {trades.map((trade, idx) => (
                <tr key={idx} className={trade.pnl >= 0 ? 'profit' : 'loss'}>
                  <td>{trade.date}</td>
                  <td>{trade.time}</td>
                  <td className="symbol">{trade.symbol}</td>
                  <td>
                    <span className={`channel ${trade.channel}`}>
                      {trade.channel === 'main' ? '📡 主通道' : '⚡ Spike'}
                    </span>
                  </td>
                  <td>
                    <span className="pattern">{trade.pattern}</span>
                  </td>
                  <td>{trade.shares}</td>
                  <td>${trade.entry.toFixed(2)}</td>
                  <td>${trade.exit.toFixed(2)}</td>
                  <td className={trade.pnl >= 0 ? 'positive' : 'negative'}>
                    ${trade.pnl.toFixed(2)}
                  </td>
                  <td className={trade.pnl_pct >= 0 ? 'positive' : 'negative'}>
                    {trade.pnl_pct >= 0 ? '+' : ''}{trade.pnl_pct.toFixed(2)}%
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="stats-summary">
        <div className="stat">
          <span className="label">總成交筆數:</span>
          <span className="value">{trades.length}</span>
        </div>
        <div className="stat">
          <span className="label">總盈利:</span>
          <span className="value positive">
            ${trades.filter(t => t.pnl > 0).reduce((sum, t) => sum + t.pnl, 0).toFixed(2)}
          </span>
        </div>
        <div className="stat">
          <span className="label">總虧損:</span>
          <span className="value negative">
            ${Math.abs(trades.filter(t => t.pnl < 0).reduce((sum, t) => sum + t.pnl, 0)).toFixed(2)}
          </span>
        </div>
        <div className="stat">
          <span className="label">淨P&L:</span>
          <span className={`value ${trades.reduce((sum, t) => sum + t.pnl, 0) >= 0 ? 'positive' : 'negative'}`}>
            ${trades.reduce((sum, t) => sum + t.pnl, 0).toFixed(2)}
          </span>
        </div>
      </div>
    </div>
  );
}

export default TradeHistory;
