import React, { useState } from 'react';
import { Lock, AlertCircle } from 'lucide-react';
import '../styles/Login.css';

function Login({ onLoginSuccess }) {
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleLogin = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const backendUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';

      const response = await fetch(`${backendUrl}/api/health`, {
        method: 'GET',
        headers: {
          'Authorization': 'Basic ' + btoa(':' + password),
        },
      });

      if (response.status === 401) {
        setError('❌ 密碼錯誤，請重試');
      } else if (response.ok) {
        // 存儲認證信息
        const auth = btoa(':' + password);
        localStorage.setItem('auth_token', auth);
        localStorage.setItem('api_url', backendUrl);
        onLoginSuccess();
      } else {
        setError('連線失敗，請檢查後端狀態');
      }
    } catch (err) {
      setError('無法連接到伺服器，請檢查網絡或後端地址');
      console.error('Login error:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-container">
      <div className="login-box">
        <div className="login-header">
          <div className="logo">🤖</div>
          <h1>AI Trading Monitor</h1>
          <p>實時交易監控系統</p>
        </div>

        <form onSubmit={handleLogin} className="login-form">
          <div className="form-group">
            <label htmlFor="password">
              <Lock size={16} />
              訪問密碼
            </label>
            <input
              id="password"
              type="password"
              placeholder="輸入訪問密碼"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              disabled={loading}
              autoFocus
            />
          </div>

          {error && (
            <div className="error-box">
              <AlertCircle size={16} />
              <span>{error}</span>
            </div>
          )}

          <button
            type="submit"
            disabled={loading || !password}
            className={loading ? 'loading' : ''}
          >
            {loading ? '驗證中...' : '進入 Dashboard'}
          </button>
        </form>

        <div className="login-footer">
          <p>🔒 您的數據已加密傳輸</p>
          <p style={{ fontSize: '12px', color: '#999' }}>
            僅用於個人訪問 • 禁止分享密碼
          </p>
        </div>
      </div>

      <div className="login-background"></div>
    </div>
  );
}

export default Login;
