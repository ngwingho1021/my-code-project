# 🚀 今日快速啟動指南 (2026-08-17)

## 前置準備（9:15 AM EST）

### 1️⃣ TWS / IB Gateway 設定 (5 分鐘)
```
✅ 打開 TWS
✅ 登入 Paper Trading 帳戶（DUR065821）
✅ File → Global Configuration → API → Settings
   ✓ 勾選 "Enable ActiveX and Socket Clients"
   ✓ Socket Port: 7497
✅ Apply & OK
```

### 2️⃣ 清理舊進程（如適用）
```cmd
taskkill /F /IM python.exe
```

### 3️⃣ 更新代碼
```cmd
cd C:\Users\illkh\my-code-project
git pull origin claude/trading-system-stop-loss-profit-pwp2b0
```

### 4️⃣ 檢查依賴（可選 - 如果之前冇安裝）
```cmd
pip install ib_async numpy pandas pytz python-dotenv
```

---

## 啟動機械人 (9:25 AM EST)

```cmd
python main.py
```

**預期看到的日誌（首 30 秒）**：

```
2026-08-17 09:25:00 - INFO - 連接 IBKR 127.0.0.1:7497...
2026-08-17 09:25:01 - INFO - IBKR 連線成功。
2026-08-17 09:25:02 - INFO - 交易機械人啟動（Paper Trading）
2026-08-17 09:25:05 - INFO - 向 IBKR 發送 scanner 請求...
2026-08-17 09:25:08 - INFO - Scanner 初篩結果 (5 隻): UPST, COIN, XPEV, MRVL, ...
2026-08-17 09:25:10 - INFO - 二次過濾後符合 5 核心條件: UPST, COIN
2026-08-17 09:25:12 - INFO - 加入監控名單: UPST gap=6.2% relVol=3.1x
2026-08-17 09:25:15 - INFO - 加入監控名單: COIN gap=5.8% relVol=2.2x
Bot started. Waiting for signals...
```

✅ **如果看到上述日誌 = 正常！**

---

## 監控中 (9:30 AM - 4:00 PM EST)

### 正常行為

- 每 **60 秒** 會掃描一次新的 gap-up 機會
- 每 **5 秒** 會檢查持倉是否應該離場
- 最多同時監控 **3 個股票**（新增的保護措施）
- 如果達到 3 個就會停止掃描，直到有離場

### ⚠️ 警告訊號 & 應對

| 警告 | 原因 | 應對 |
|------|------|------|
| `ERROR - Couldn't connect to TWS` | API 未啟用 | 檢查 TWS 設定，重啟機械人 |
| `HMDS connection inactive` | 網絡問題 | 等待 (IBKR 會自動恢復) |
| `Order: PreSubmitted` | 訂單待審 | 正常 - 等待成交或自動冷卻 |
| `⚠️ 機械人可能卡住（>30秒冇心跳）` | **機械人僵死** | **按 Ctrl+C 立即重啟** |
| `連續 5 次出錯，機械人停止運行` | **API 故障** | 等 30 秒，重啟 TWS，重啟機械人 |

---

## 交易紀錄檢查

### 即時監控
```
日誌檔案位置：logs/2026-08-17.log
交易紀錄位置：logs/trades.log
```

### 市場收盤後檢查
```cmd
type logs\trades.log
```

Expected format:
```
ENTER UPST shares=50 limit=15.50 stop=14.50
EXIT UPST reason='target1' shares=25 @ 16.50
EXIT UPST reason='target2' shares=25 @ 17.50
EXIT COIN reason='stop' shares=30 @ 25.10
```

---

## 安全停止（市場收盤後）

**正確做法**：
```cmd
按 Ctrl+C 一次
```

等待日誌顯示：
```
收到手動中止指令，準備安全結束...
```

✅ 機械人會自動：
1. 取消所有未成交的訂單
2. 記錄所有交易到 CSV
3. 生成每日報告

---

## 今日目標

- [ ] 連接到 IBKR 成功
- [ ] 掃描並加入第一個候選股票
- [ ] 執行至少 1 筆交易（或觀察整天）
- [ ] 沒有看到凍結警告 (`>30秒冇心跳`)
- [ ] 安全關閉機械人

---

## 如果發生問題

### 機械人卡住超過 30 秒

```cmd
按 Ctrl+C
taskkill /F /IM python.exe
REM 等 10 秒
python main.py
```

### 訂單卡在 PreSubmitted

1. 打開 TWS → Account → Orders → Presubmitted
2. 看是否有舊訂單 → **右鍵 → Cancel**
3. 等 30 秒後重新啟動機械人

### 網絡連線問題

- 檢查 TWS 是否顯示 "Disconnected" 
- 如果是 → 等 30 秒，IBKR 會自動重連
- 如果不會自動重連 → 重啟 TWS → 重啟機械人

---

## 成功標誌 ✅

- 機械人運行 > 2 小時無問題
- 至少執行 1 筆交易
- 沒有凍結警告
- 有完整的交易紀錄在 logs/trades.log

---

**祝好運！今天是正式驗證策略的日子。如果一切順利，下一步就是 1-2 週的持續監控，然後評估是否進入真實盤。**

---
Last Updated: 2026-08-17 08:00 UTC
