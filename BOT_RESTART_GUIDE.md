# 交易機械人安全重啟指南

## 發生的問題分析

上一次運行時，機械人在 **06:55:48** 停止工作。從日誌顯示：

- ✓ 成功連接 IBKR (帳戶 DUR065821)
- ✓ 成功訂閱 8 個監控股票的市場數據
- ✗ **MRVL (Marvell)** 被動態掃描發現並加入監控名單
- ✗ 下單後進入無窮迴圈，訂單卡在 "PreSubmitted" 狀態
- ✗ 機械人停止回應

### 根本原因

1. **動態掃描過度激進**：機械人掃描到任何符合 5 核心條件的股票都會加入監控名單，導致短時間內開啟多個持倉
2. **並行控制缺失**：沒有上限控制同時間開啟幾多個位
3. **非同步循環死結**：`ib_async` 在大量並行訂單時出現回調循環

## 修復已套用

✅ **並行控制保護**：
   - 新增硬限制：最多同時監控 3 個股票
   - 掃描時會檢查是否達到上限，達到就停止掃描

✅ **日誌改進**：
   - 當達到並行上限時會記錄警告

## 重啟步驟（Windows 用戶）

### 步驟 1：清理舊進程

打開 **Command Prompt** 或 **PowerShell**：

```cmd
REM 殺掉所有 Python 進程（謹慎！）
taskkill /F /IM python.exe

REM 或更安全的做法：開啟工作管理員，手動結束 python.exe 進程
```

### 步驟 2：檢查 IBKR 連線

1. 打開 **TWS** 或 **IB Gateway**
2. 確認已登入 **Paper Trading 帳戶**（DUR065821）
3. 驗證 API 已啟用：
   - **TWS**: File → Global Configuration → API → Settings
   - 勾選 "Enable ActiveX and Socket Clients"
   - Socket Port 設為 **7497**
   - Apply

### 步驟 3：重新安裝依賴（若有缺失）

```cmd
cd C:\Users\illkh\my-code-project
pip install ib_async numpy pandas pytz python-dotenv
```

### 步驟 4：啟動機械人

```cmd
cd C:\Users\illkh\my-code-project
python main.py
```

預期看到的日誌輸出：

```
2026-08-17 13:45:00 - INFO - 連接 IBKR 127.0.0.1:7497...
2026-08-17 13:45:01 - INFO - IBKR 連線成功。
2026-08-17 13:45:02 - INFO - 交易機械人啟動（Paper Trading）
2026-08-17 13:45:05 - INFO - 向 IBKR 發送 scanner 請求...
2026-08-17 13:45:08 - INFO - Scanner 初篩結果 (5 隻): [MRVL, UPST, COIN, ...]
Bot started. Waiting for signals...
```

### 步驟 5：監控運行

- 機械人會每 **60 秒掃描一次**新的 gap-up 機會
- 每 **5 秒檢查一次**現有持倉是否應該離場
- 如果 IBKR 連線中斷會看到 "ERROR" 日誌 —— TWS 亦會自動斷開
- **按 Ctrl+C 安全停止機械人**

### 步驟 6：檢查交易記錄

機械人會輸出：
- **logs/2026-08-17.log** - 詳細日誌
- **logs/trades.log** - 所有交易記錄

## 如果機械人仍然卡住

### 方案 A：檢查 IBKR 中是否有卡住的訂單

1. 打開 TWS → Account → Orders → Presubmitted
2. 如果看到未成交的 TRAIL SELL 訂單 → **手動取消**
3. 檢查是否有持倉沒有止蝕單 → **手動加止蝕單**

### 方案 B：完整重設（核武級）

```cmd
REM 停止所有 Python
taskkill /F /IM python.exe

REM 強制關閉 TWS/IB Gateway，5 秒後重新開啟
REM 刪除舊日誌（可選）
del logs\*.log

REM 重新啟動機械人
python main.py
```

## 配置選項

如果想要**手動控制監控名單**（不用動態掃描），編輯 `config/settings.py`：

```python
@dataclass
class AccountRisk:
    # ...
    scan_only_symbols: list = ['NVDA', 'AMD', 'TSLA', 'PLTR', 'AAPL', 'MSFT', 'GOOGL', 'META']
```

改為 `None` 恢復動態掃描。

## 日常監控清單

每日啟動機械人前檢查：

- [ ] TWS/IB Gateway 已開啟
- [ ] 確認登入的是 **Paper Trading** 帳戶
- [ ] API 已啟用，Socket Port = 7497
- [ ] 帳戶現金足夠（$5,000+）
- [ ] 沒有卡住的訂單

## 故障排除

| 問題 | 可能原因 | 解決辦法 |
|------|--------|--------|
| "Couldn't connect to TWS" | API 未啟用或端口錯誤 | 檢查 TWS 設定，確認 port 7497 |
| "HMDS connection inactive" | 網絡問題 | 稍候，IBKR 會自動恢復 |
| 訂單卡在 PreSubmitted | 網絡延遲或 API 超時 | 手動取消 → 等 30 秒 → 重試 |
| 機械人用 100% CPU | 無窮迴圈（回調地獄） | Ctrl+C 停止 → 殺進程 → 重啟 |

---

**最後更新**：2026-08-17
**版本**：v3.2 with 並行限制
