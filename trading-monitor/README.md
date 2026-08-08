# 🤖 AI Trading Monitor - 實時交易監控系統

一個美觀現代的實時交易監控Dashboard + 每日報告系統，為你的Python AI交易機器人提供全方位監控。

## ✨ 功能特色

### 📊 實時Dashboard
- **即時指標**: P&L、勝率、成交數、最大回撤
- **美觀圖表**: 7天走勢圖、成交趨勢、通道分佈
- **風控監控**: 即時風控狀態、熔斷警告
- **持倉監控**: 實時持倉詳情

### 📜 成交紀錄
- **完整歷史**: 查看所有成交紀錄
- **靈活篩選**: 按日期、通道、形態篩選
- **詳細分析**: 每筆成交的進出場價格、P&L、收益率

### 📈 統計分析
- **績效指標**: 勝率、利潤因子、Sharpe Ratio
- **通道分析**: 主通道 vs Spike通道對比
- **形態統計**: 各類技術形態的成功率
- **深度洞察**: 最好/最壞的交易模式

### 📧 每日郵件報告
- **自動發送**: 每日收市後自動發送
- **完整摘要**: 績效、統計、風控狀態
- **成交詳情**: 當日所有成交紀錄
- **美觀格式**: HTML郵件，方便查閱

### 🔒 安全訪問
- **密碼保護**: Basic Auth認證，只有你能訪問
- **遠程訪問**: 雲端部署，隨時隨地查看
- **HTTPS**: 自動HTTPS加密傳輸

---

## 🚀 快速開始

### 前置條件
- Python 3.9+
- Node.js 16+
- 日誌文件: `daily_trade_log.json` 和 `weekly_risk_tracker.json`

### 本地開發

#### 1. 後端API (FastAPI)
```bash
cd trading-monitor/backend

# 安裝依賴
pip install -r requirements.txt

# 設置環境變數
export DASHBOARD_PASSWORD="your-secure-password"
export REPORT_EMAIL="your-email@gmail.com"
export SMTP_PASSWORD="your-smtp-password"

# 運行開發服務器
python app.py
# 訪問: http://localhost:8000
```

#### 2. 前端Dashboard (React + Vite)
```bash
cd trading-monitor/frontend

# 安裝依賴
npm install

# 設置環境變數
echo "VITE_API_URL=http://localhost:8000" > .env.local

# 運行開發服務器
npm run dev
# 訪問: http://localhost:5173
```

### 環境變數配置

**後端 (.env)**:
```env
# 訪問密碼
DASHBOARD_PASSWORD=monitor123

# 每日報告
REPORT_EMAIL=your-email@gmail.com

# Gmail SMTP (建議使用應用專用密碼)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM=your-email@gmail.com

# 前端URL (如果部署到Vercel)
FRONTEND_URL=https://your-dashboard.vercel.app
```

---

## ☁️ 雲端部署

### 選項1: Vercel (前端) + Railway (後端) ⭐ 推薦

#### Step 1: 部署後端到Railway

1. 推送代碼到GitHub
2. 連接Railway: https://railway.app
3. 新建Project → GitHub Repository
4. 選擇 `trading-monitor` 目錄
5. 設置環境變數:
   ```
   DASHBOARD_PASSWORD=your-secure-password
   REPORT_EMAIL=your-email@gmail.com
   SMTP_HOST=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USER=your-gmail@gmail.com
   SMTP_PASSWORD=your-app-password (1)
   SMTP_FROM=your-gmail@gmail.com
   ```
6. 部署後獲取Railway URL: `https://your-app.railway.app`

#### Step 2: 部署前端到Vercel

1. Fork本Repository到你的GitHub
2. 訪問 https://vercel.com
3. Import Project → 選擇repository
4. 配置Build Settings:
   - Framework: Vite
   - Build Command: `cd frontend && npm install && npm run build`
   - Output Directory: `frontend/dist`
5. 環境變數:
   ```
   VITE_API_URL=https://your-app.railway.app
   ```
6. Deploy並獲取Vercel URL

#### Step 3: 連接日誌文件

在你的交易機器人環境中:
```bash
# 複製日誌文件到Railway應用
# 配置webhook或定時同步 daily_trade_log.json 和 weekly_risk_tracker.json
```

### 選項2: Heroku (已棄用 ❌ 不推薦)

### 選項3: Docker + 自建服務器

```bash
# 構建Docker Image
docker build -f trading-monitor/backend/Dockerfile -t trading-monitor-api .

# 運行容器
docker run -p 8000:8000 \
  -e DASHBOARD_PASSWORD=your-password \
  -e REPORT_EMAIL=your-email@gmail.com \
  -e SMTP_PASSWORD=your-smtp-password \
  trading-monitor-api
```

---

## 📋 API 端點

### 認證
所有端點使用 HTTP Basic Auth:
```
Authorization: Basic base64(":password")
```

### 端點列表

| 方法 | 端點 | 說明 |
|------|------|------|
| GET | `/api/health` | 健康檢查 |
| GET | `/api/metrics` | Dashboard指標 |
| GET | `/api/trades?days=7` | 成交紀錄 |
| GET | `/api/trades/summary?days=7` | 成交統計 |
| GET | `/api/statistics?days=30` | 詳細統計 |
| POST | `/api/send-daily-report` | 手動發送報告 |

### 範例請求

```bash
# 獲取指標
curl -u ":monitor123" http://localhost:8000/api/metrics

# 獲取7天成交
curl -u ":monitor123" http://localhost:8000/api/trades?days=7

# 手動發送報告
curl -X POST -u ":monitor123" http://localhost:8000/api/send-daily-report
```

---

## 🔧 配置郵件報告

### Gmail設置 (推薦)

1. 啟用 2FA: https://myaccount.google.com/security
2. 生成應用專用密碼:
   - 訪問 https://myaccount.google.com/apppasswords
   - 選擇 Mail + Windows Computer
   - 複製生成的密碼
3. 在環境變數中使用該密碼

### 其他郵件服務商

修改 `backend/app.py` 中的 SMTP 設置:
```python
# Outlook
SMTP_HOST = "smtp-mail.outlook.com"
SMTP_PORT = 587

# SendGrid
SMTP_HOST = "smtp.sendgrid.net"
SMTP_PORT = 587
```

---

## 📊 數據流

```
交易機器人
    ↓
daily_trade_log.json
weekly_risk_tracker.json
    ↓
FastAPI Backend (Railway)
    ↓
┌─────────────────────────┐
├─ Dashboard (Vercel)
├─ 每日郵件報告
└─ REST API
```

---

## 🛠️ 自定義

### 修改Dashboard指標

編輯 `backend/app.py` 中的 `get_metrics()`:
```python
async def get_metrics(credentials: HTTPBasicCredentials = Depends(verify_password)):
    # 添加自定義指標
    your_metric = calculated_value
    return DashboardMetrics(
        ...
        your_metric=your_metric,
    )
```

### 修改UI主題

編輯 `frontend/src/App.css`:
```css
:root {
  --primary: #667eea;      /* 改成你喜歡的顏色 */
  --primary-dark: #764ba2;
  --success: #10b981;
  --danger: #ef4444;
  /* ... */
}
```

### 添加新圖表

在 `frontend/src/components/Dashboard.jsx`:
```jsx
import { LineChart, Line, ... } from 'recharts';

// 添加新圖表容器
<div className="chart-box">
  <h3>你的圖表標題</h3>
  <ResponsiveContainer width="100%" height={300}>
    {/* 你的Recharts圖表 */}
  </ResponsiveContainer>
</div>
```

---

## 🐛 故障排除

### Dashboard連接失敗
- ✅ 確保後端正在運行
- ✅ 檢查環境變數 `VITE_API_URL` 是否正確
- ✅ 檢查CORS設置

### 郵件未發送
- ✅ 確保SMTP密碼正確
- ✅ 檢查郵箱是否已啟用2FA和應用專用密碼
- ✅ 查看後端日誌

### 數據未更新
- ✅ 檢查日誌文件是否在正確的路徑
- ✅ 確保日誌格式正確 (JSON)
- ✅ 檢查文件權限

---

## 📞 支持

- 📧 Email: rnleo1021@gmail.com
- 🐛 Issues: 在GitHub提交Issue

---

## 📄 License

MIT License - 自由使用和修改

---

## 🎯 路線圖

- [ ] WebSocket即時更新（無需刷新）
- [ ] 推送通知（進場/止盈時通知）
- [ ] 高級篩選（按日期/通道/收益率）
- [ ] 數據匯出（CSV/Excel）
- [ ] 多語言支持
- [ ] 移動端App

---

**開始監控你的AI交易機器人吧！🚀**
