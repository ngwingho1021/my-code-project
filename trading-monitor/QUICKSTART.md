# ⚡ 快速開始指南 (5分鐘上手)

## 🎯 目標
在5分鐘內本地運行整個監控系統，體驗完整功能。

---

## 📦 前置要求

```bash
# 檢查Python版本 (需要3.9+)
python --version

# 檢查Node版本 (需要16+)
node --version
```

---

## 🚀 本地運行 (開發模式)

### 1️⃣ 後端API (2分鐘)

```bash
# 進入後端目錄
cd trading-monitor/backend

# 安裝依賴
pip install -r requirements.txt

# 設置環境變數
export DASHBOARD_PASSWORD="monitor123"
export REPORT_EMAIL="your-email@gmail.com"

# 運行服務器
python app.py

# ✅ 服務器運行在 http://localhost:8000
# 測試: curl -u ":monitor123" http://localhost:8000/api/health
```

### 2️⃣ 前端Dashboard (2分鐘)

```bash
# 新開一個終端，進入前端目錄
cd trading-monitor/frontend

# 安裝依賴
npm install

# 運行開發服務器
npm run dev

# ✅ Dashboard運行在 http://localhost:5173
```

### 3️⃣ 訪問系統 (1分鐘)

1. 打開瀏覽器訪問: **http://localhost:5173**
2. 輸入密碼: **monitor123**
3. 🎉 進入Dashboard！

---

## 🎨 界面預覽

### 📊 Dashboard
```
┌────────────────────────────────────────────────┐
│  AI Trading Monitor                      登出   │
├────────────────────────────────────────────────┤
│  [📊Dashboard] [📜成交紀錄] [📈統計分析]        │
├────────────────────────────────────────────────┤
│                                                 │
│  ┌─────────────────────────────────────────┐   │
│  │ 今日P&L          勝率          成交筆數  │   │
│  │  +$250.50        80%             5筆    │   │
│  └─────────────────────────────────────────┘   │
│                                                 │
│  ┌──────────────────┐  ┌──────────────────┐   │
│  │  7天P&L走勢      │  │  成交趨勢圖      │   │
│  │  [圖表]          │  │  [圖表]          │   │
│  └──────────────────┘  └──────────────────┘   │
│                                                 │
└────────────────────────────────────────────────┘
```

### 📜 成交紀錄
```
日期       時間    股票  通道    形態      數量  進場   出場   P&L
2026-08-08 09:30 TSLA 主通道 Micro Pull 200  245.50 248.50 +600
2026-08-08 10:15 NVDA Spike   Bull Flag 150  120.30 123.80 +525
...
```

### 📈 統計分析
```
總成交: 150筆 | 勝率: 75% | 總P&L: +$5,250 | 利潤因子: 2.5
┌─────────────────────┐
│ 通道分析圖表        │
│ 主通道 vs Spike     │
└─────────────────────┘
```

---

## 📝 配置示例

### 使用你的交易日誌

確保這些文件在 `trading-monitor/` 目錄中:

```json
// daily_trade_log.json 示例
[
  {
    "date": "2026-08-08",
    "time": "09:30:00",
    "symbol": "TSLA",
    "channel": "main",
    "pattern": "Micro Pullback",
    "entry": 245.50,
    "exit": 248.50,
    "shares": 200,
    "pnl": 600.00,
    "pnl_pct": 1.22
  }
]

// weekly_risk_tracker.json 示例
{
  "year": 2026,
  "week": 32,
  "weekly_pnl": 2500.00,
  "daily": {
    "2026-08-08": 250.50
  }
}
```

---

## 🔧 常用命令

```bash
# 刷新Dashboard數據
curl -u ":monitor123" http://localhost:8000/api/metrics

# 獲取7天交易紀錄
curl -u ":monitor123" http://localhost:8000/api/trades?days=7

# 獲取詳細統計
curl -u ":monitor123" http://localhost:8000/api/statistics?days=30

# 手動觸發郵件報告
curl -X POST -u ":monitor123" http://localhost:8000/api/send-daily-report
```

---

## 🐛 故障排除

### ❌ 後端連接失敗
```bash
# 1. 檢查後端是否運行
ps aux | grep uvicorn

# 2. 檢查端口
lsof -i :8000

# 3. 重新啟動
# 終止 + 重新運行 python app.py
```

### ❌ 前端無法連接後端
```bash
# 1. 檢查 vite.config.js 的proxy設置
# 應該指向 http://localhost:8000

# 2. 檢查密碼是否正確
# 默認: monitor123

# 3. 檢查CORS設置
# 後端應該允許 http://localhost:5173
```

### ❌ Dashboard顯示無數據
```bash
# 1. 檢查日誌文件是否存在
ls -la daily_trade_log.json
ls -la weekly_risk_tracker.json

# 2. 檢查JSON格式是否正確
python -m json.tool daily_trade_log.json

# 3. 檢查後端日誌中是否有錯誤
# 查看運行 python app.py 的終端輸出
```

---

## 📊 測試數據生成

如果沒有實際交易數據，可以生成測試數據:

```python
# test_data.py
import json
from datetime import date, timedelta
import random

# 生成30天的測試數據
trades = []
for i in range(30):
    trade_date = date.today() - timedelta(days=i)
    num_trades = random.randint(1, 5)
    
    for j in range(num_trades):
        entry = round(random.uniform(100, 300), 2)
        pnl_pct = random.uniform(-2, 5)
        exit = round(entry * (1 + pnl_pct/100), 2)
        
        trades.append({
            "date": trade_date.isoformat(),
            "time": f"{random.randint(9,15)}:{random.randint(0,59):02d}:00",
            "symbol": random.choice(["TSLA", "NVDA", "AAPL", "MSFT"]),
            "channel": random.choice(["main", "spike"]),
            "pattern": random.choice(["Micro Pullback", "Cup and Handle", "Bull Flag"]),
            "entry": entry,
            "exit": exit,
            "shares": random.randint(50, 500),
            "pnl": round((exit - entry) * random.randint(50, 500), 2),
            "pnl_pct": round(pnl_pct, 2)
        })

# 保存測試數據
with open('daily_trade_log.json', 'w') as f:
    json.dump(sorted(trades, key=lambda x: x['date']), f, indent=2)

print("✅ 測試數據已生成")
```

運行:
```bash
python test_data.py
```

---

## 🚀 下一步

### 本地開發完成後

1. **Push到GitHub**
   ```bash
   git add .
   git commit -m "配置本地監控系統"
   git push
   ```

2. **部署到Railway + Vercel**
   - 詳見 [DEPLOYMENT.md](./DEPLOYMENT.md)

3. **自動化日誌同步**
   - 在交易機器人中添加日誌上傳邏輯

4. **配置郵件報告**
   - 設置Gmail應用專用密碼

---

## 💡 常用API快速參考

| 功能 | 命令 |
|------|------|
| 獲取今日指標 | `curl -u ":pass" localhost:8000/api/metrics` |
| 獲取成交紀錄 | `curl -u ":pass" localhost:8000/api/trades?days=7` |
| 獲取統計數據 | `curl -u ":pass" localhost:8000/api/statistics?days=30` |
| 發送郵件 | `curl -X POST -u ":pass" localhost:8000/api/send-daily-report` |

---

## 📱 快速鏈接

- 本地Dashboard: http://localhost:5173
- 本地API: http://localhost:8000/api/health
- API文檔: http://localhost:8000/docs (FastAPI自動生成)

---

**現在就試試吧！🚀**

有問題？查看 [README.md](./README.md) 或 [DEPLOYMENT.md](./DEPLOYMENT.md)
