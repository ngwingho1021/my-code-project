import React, { useState, useEffect } from 'react';
import { AlertCircle, TrendingUp, TrendingDown, Activity, BarChart3, Settings } from 'lucide-react';
import Dashboard from './components/Dashboard';
import TradeHistory from './components/TradeHistory';
import Statistics from './components/Statistics';
import Login from './components/Login';
import './App.css';

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [activeTab, setActiveTab] = useState('dashboard');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem('auth_token');
    if (token) {
      setIsAuthenticated(true);
    }
  }, []);

  const handleLogout = () => {
    localStorage.removeItem('auth_token');
    setIsAuthenticated(false);
  };

  const handleLoginSuccess = () => {
    setIsAuthenticated(true);
    setActiveTab('dashboard');
  };

  if (!isAuthenticated) {
    return <Login onLoginSuccess={handleLoginSuccess} />;
  }

  return (
    <div className="app-container">
      {/* 頂部導航欄 */}
      <nav className="navbar">
        <div className="navbar-brand">
          <Activity className="logo-icon" />
          <h1>AI Trading Monitor</h1>
        </div>
        <div className="navbar-tabs">
          <button
            className={`nav-tab ${activeTab === 'dashboard' ? 'active' : ''}`}
            onClick={() => setActiveTab('dashboard')}
          >
            📊 Dashboard
          </button>
          <button
            className={`nav-tab ${activeTab === 'trades' ? 'active' : ''}`}
            onClick={() => setActiveTab('trades')}
          >
            📜 成交紀錄
          </button>
          <button
            className={`nav-tab ${activeTab === 'stats' ? 'active' : ''}`}
            onClick={() => setActiveTab('stats')}
          >
            📈 統計分析
          </button>
        </div>
        <button className="logout-btn" onClick={handleLogout}>
          登出
        </button>
      </nav>

      {/* 主容器 */}
      <div className="main-container">
        {activeTab === 'dashboard' && <Dashboard />}
        {activeTab === 'trades' && <TradeHistory />}
        {activeTab === 'stats' && <Statistics />}
      </div>

      {/* 底部狀態欄 */}
      <footer className="footer">
        <p>🤖 AI Trading Bot Monitor | Real-time Dashboard</p>
        <p style={{ fontSize: '12px', color: '#999' }}>
          Last Update: {new Date().toLocaleTimeString('zh-HK')}
        </p>
      </footer>
    </div>
  );
}

export default App;
