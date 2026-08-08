# 🚀 完整部署指南

本指南將一步步教你如何將AI Trading Monitor部署到雲端，實現遠程訪問。

---

## 📋 前置準備

### 所需帳戶
1. **GitHub** - 用於代碼版本控制
2. **Railway** - 用於部署後端API
3. **Vercel** - 用於部署前端Dashboard
4. **Gmail** - 用於發送每日報告 (可選)

---

## Step 1️⃣: 準備GitHub

### 1.1 創建GitHub Repository

```bash
# 初始化Git
git init

# 添加遠程倉庫
git remote add origin https://github.com/your-username/trading-monitor.git

# 推送代碼
git add .
git commit -m "初始化 Trading Monitor"
git branch -M main
git push -u origin main
```

### 1.2 確保代碼結構正確

```
trading-monitor/
├── backend/
│   ├── app.py
│   ├── requirements.txt
│   ├── Dockerfile
│   └── Procfile
├── frontend/
│   ├── src/
│   ├── package.json
│   ├── vite.config.js
│   └── index.html
├── railway.json
├── vercel.json
└── README.md
```

---

## Step 2️⃣: 部署後端到Railway

### 2.1 訪問Railway

1. 打開 https://railway.app
2. 用GitHub帳戶登錄
3. 點擊 **New Project**

### 2.2 連接GitHub Repository

1. 選擇 **Deploy from GitHub**
2. 授權Railway訪問GitHub
3. 選擇你的 `trading-monitor` repository
4. 點擊 **Deploy Now**

### 2.3 配置環境變數

1. 在Railway Dashboard中找到你的Project
2. 進入 **Variables** 標籤
3. 添加以下環境變數:

```
DASHBOARD_PASSWORD = your-secure-password (例: MyMonitor123!)
REPORT_EMAIL = your-email@gmail.com
SMTP_HOST = smtp.gmail.com
SMTP_PORT = 587
SMTP_USER = your-email@gmail.com
SMTP_PASSWORD = your-app-password (Gmail應用專用密碼)
SMTP_FROM = your-email@gmail.com
FRONTEND_URL = https://trading-monitor-dashboard.vercel.app (稍後設置)
```

### 2.4 獲取Railway API URL

1. 在Railway Dashboard中，找到 **Deployments**
2. 查找 **Deployment URL**，例如: `https://your-app-12345.railway.app`
3. **複製該URL** - 後面會用到

### 2.5 配置Web服務端口

1. 進入 **Settings** 標籤
2. 確保 **PORT** 設置為 `8000`
3. 確保啟動命令為: `cd backend && uvicorn app:app --host 0.0.0.0 --port 8000`

✅ **後端部署完成！**

---

## Step 3️⃣: 配置日誌文件同步

因為日誌文件在你的本地機器上，需要定期同步到Railway:

### 方案A: 使用webhook (推薦)

在你的交易機器人中添加:

```python
import requests
import json
from datetime import date

async def upload_logs_to_railway():
    """每日收市後上傳日誌到Railway"""
    railway_url = "https://your-railway-app.railway.app/api/upload-logs"
    
    # 讀取本地日誌
    with open('daily_trade_log.json', 'r') as f:
        trades = json.load(f)
    
    with open('weekly_risk_tracker.json', 'r') as f:
        risk = json.load(f)
    
    # 發送到Railway
    payload = {
        'trades': trades,
        'risk_data': risk,
    }
    
    response = requests.post(
        railway_url,
        json=payload,
        auth=('', 'your-dashboard-password')
    )
    
    if response.ok:
        print("✅ 日誌已同步到Railway")
    else:
        print(f"❌ 同步失敗: {response.status_code}")
```

### 方案B: 手動上傳 (臨時方案)

```bash
# 使用curl上傳日誌
curl -X POST https://your-railway-app.railway.app/api/upload-logs \
  -H "Content-Type: application/json" \
  -u ":your-password" \
  -d @daily_trade_log.json
```

---

## Step 4️⃣: 部署前端到Vercel

### 4.1 連接Vercel

1. 打開 https://vercel.com
2. 用GitHub帳戶登錄
3. 點擊 **Add New...** → **Project**
4. 搜索並選擇你的 `trading-monitor` repository

### 4.2 配置Build設置

在 **Configure Project** 頁面:

- **Framework Preset**: Vite
- **Root Directory**: ./trading-monitor (或留空)
- **Build Command**: `cd frontend && npm install && npm run build`
- **Output Directory**: `frontend/dist`
- **Install Command**: `npm install`

### 4.3 設置環境變數

在 **Environment Variables** 部分添加:

```
Name: VITE_API_URL
Value: https://your-railway-app.railway.app
```

點擊 **Save** 並部署。

### 4.4 獲取Vercel URL

部署完成後，Vercel會生成一個URL:
```
https://trading-monitor-dashboard.vercel.app
```

### 4.5 更新Railway FRONTEND_URL

回到Railway Dashboard，更新環境變數:
```
FRONTEND_URL = https://trading-monitor-dashboard.vercel.app
```

---

## Step 5️⃣: 配置Gmail郵件報告 (可選)

### 5.1 啟用Gmail 2FA

1. 訪問 https://myaccount.google.com/security
2. 向下滾動找到 **2-Step Verification**
3. 點擊 **Enable 2-Step Verification**
4. 按照指示完成設置

### 5.2 生成應用專用密碼

1. 訪問 https://myaccount.google.com/apppasswords
2. 選擇 **Mail** 和 **Windows Computer**
3. Google會生成一個16位密碼
4. 複製該密碼並保存

### 5.3 更新Railway環境變數

在Railway Dashboard中:

```
SMTP_USER = your-email@gmail.com
SMTP_PASSWORD = 粘貼16位密碼 (不含空格)
```

### 5.4 測試郵件發送

```bash
curl -X POST https://your-railway-app.railway.app/api/send-daily-report \
  -u ":your-password"
```

檢查你的郵箱是否收到報告。

---

## Step 6️⃣: 測試完整系統

### 6.1 測試後端

```bash
# 測試API連接
curl https://your-railway-app.railway.app/api/health \
  -u ":your-password"

# 應該返回
# {"status":"ok","timestamp":"..."}
```

### 6.2 訪問Dashboard

1. 打開 https://trading-monitor-dashboard.vercel.app
2. 輸入密碼: `your-secure-password`
3. 應該看到Dashboard頁面

### 6.3 查看實時數據

1. 確保日誌文件已上傳到Railway
2. 在Dashboard中點擊 🔄 **重新整理**
3. 檢查數據是否正常顯示

---

## 🔄 定時同步日誌

為了讓Dashboard實時顯示數據，你需要定期將日誌文件同步到Railway。

### 方案1: 在主交易機器人中添加同步

編輯 `main_bot.py`:

```python
import aiohttp

async def sync_logs_to_cloud():
    """每小時同步一次日誌"""
    railway_url = "https://your-railway-app.railway.app/api/upload-logs"
    
    while True:
        try:
            # 讀取日誌
            with open('daily_trade_log.json', 'rb') as f:
                logs = f.read()
            
            with open('weekly_risk_tracker.json', 'rb') as f:
                risk = f.read()
            
            # 上傳到Railway
            async with aiohttp.ClientSession() as session:
                headers = {
                    'Authorization': 'Basic ' + base64.b64encode(b':your-password').decode()
                }
                # ... 上傳邏輯 ...
            
            await asyncio.sleep(3600)  # 每小時同步一次
        except Exception as e:
            print(f"日誌同步失敗: {e}")
            await asyncio.sleep(60)

# 在main_bot.py中啟動任務
asyncio.create_task(sync_logs_to_cloud())
```

### 方案2: 使用Cron Job (Linux/Mac)

```bash
# 編輯crontab
crontab -e

# 添加每小時同步一次
0 * * * * curl -X POST https://your-railway-app.railway.app/api/upload-logs \
  -H "Content-Type: application/json" \
  -u ":password" \
  -d @~/path/to/daily_trade_log.json
```

### 方案3: GitHub Actions

在 `.github/workflows/sync-logs.yml`:

```yaml
name: Sync Logs to Railway

on:
  schedule:
    - cron: '0 * * * *'  # 每小時執行

jobs:
  sync:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Sync logs
        run: |
          curl -X POST https://your-railway-app.railway.app/api/upload-logs \
            -u ":${{ secrets.DASHBOARD_PASSWORD }}"
```

---

## 🔐 安全注意事項

1. **密碼安全**
   - 使用強密碼 (至少12個字符，包含大小寫和數字)
   - 不要在代碼中硬編碼密碼
   - 使用環境變數存儲敏感信息

2. **HTTPS**
   - Railway和Vercel都自動提供HTTPS
   - 所有傳輸都會加密

3. **認證**
   - 使用HTTP Basic Auth
   - 考慮在Railway中添加IP白名單

4. **日誌文件**
   - 不要將日誌文件提交到GitHub
   - 定期備份重要數據

---

## 🆘 常見問題

### Q1: Railway部署失敗？
```
A: 檢查:
1. Dockerfile 是否正確
2. requirements.txt 是否包含所有依賴
3. Python版本是否為3.9+
4. 環境變數是否正確設置
```

### Q2: Vercel前端無法連接後端？
```
A: 檢查:
1. VITE_API_URL 環境變數是否正確
2. Railway API URL 是否可訪問
3. CORS設置是否正確
4. 密碼是否正確
```

### Q3: 郵件無法發送？
```
A: 檢查:
1. Gmail 2FA 是否已啟用
2. 應用專用密碼是否正確複製
3. SMTP 設置是否正確
4. REPORT_EMAIL 是否有效
```

### Q4: 日誌數據不更新？
```
A: 檢查:
1. 日誌文件是否存在且有效
2. 同步任務是否正在運行
3. 日誌路徑是否正確
4. Railway 容器日誌中是否有錯誤
```

---

## 📊 監控部署狀態

### Railway Dashboard
- https://railway.app → 查看部署狀態、日誌、重啟應用

### Vercel Dashboard
- https://vercel.com → 查看構建狀態、環境變數

### 檢查應用健康狀態
```bash
# 後端健康檢查
curl -I https://your-railway-app.railway.app/api/health

# 應該返回 200 OK
```

---

## 🎯 完成清單

- [ ] GitHub Repository已創建並推送代碼
- [ ] Railway後端已部署並運行
- [ ] 環境變數已在Railway中設置
- [ ] Vercel前端已部署並構建成功
- [ ] VITE_API_URL 指向正確的Railway URL
- [ ] 可以訪問Dashboard (輸入密碼)
- [ ] 日誌文件已上傳到Railway
- [ ] Dashboard顯示正確的數據
- [ ] Gmail郵件配置已完成 (可選)
- [ ] 測試發送郵件報告
- [ ] 設置日誌定時同步

---

## 🚀 下一步

1. **每日運維**
   - 監控Dashboard中的風控狀態
   - 查看每日成交紀錄
   - 檢查郵件報告

2. **定期備份**
   - 備份 `daily_trade_log.json`
   - 備份 `weekly_risk_tracker.json`
   - 導出重要的交易數據

3. **性能優化**
   - 監控Railway和Vercel的成本
   - 優化API查詢性能
   - 清理過舊數據

4. **功能擴展**
   - 添加WebSocket實時推送
   - 集成Telegram通知
   - 添加數據導出功能

---

**祝賀！你已成功部署AI Trading Monitor！🎉**

有問題？查看 [README.md](./README.md) 或提交Issue。
