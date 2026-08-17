# 【Small-Cap Momentum Trader】完全重構架構升級指南

## ✅ 重構完成

**日期**: 2026-08-17 凌晨
**新代碼**: 已提交到 GitHub (`claude/trading-system-stop-loss-profit-pwp2b0`)
**狀態**: 準備在 Windows 本地測試

---

## 📋 新架構核心模塊

### 1. **訂單狀態機** (`core/order_state_machine.py`)
防止昨日的"卡單"問題的關鍵

```
訂單狀態流程:
  PENDING → SUBMITTED → ACCEPTED → PARTIALLY_FILLED → FILLED
                                  ↳ CANCELLED
                                  ↳ ERROR

持倉狀態流程:
  ENTRY_PENDING → ENTRY_FILLED → MANAGING → EXITING → EXITED
```

每個訂單有明確的生命週期，避免重複下單或遺漏。

### 2. **5支柱篩選器** (`core/stock_selector.py`)
Small-Cap Momentum Trader 的 5 個篩選條件

```
支柱 1: Gap Up ≥ 5%              (開盤跳空)
支柱 2: 新聞催化劑                (可選，提高信心)
支柱 3: Float < 20M              (流通股本少)
支柱 4: RVOL ≥ 2x                (相對成交量大增)
支柱 5: $2-20 股價範圍           (適合日內交易)

評分系統: 0-100 分，自動排名最佳候選
```

### 3. **持倉管理器** (`core/position_manager.py`)
完整的風險管理系統

```
風控檢查:
- 最多並行持倉: 3 個
- 最大每日虧損: $300
- 最大每週虧損: $800
- 每筆交易風險: $100
- 最多每日交易: 12 筆

持倉大小自動計算:
  Position Size = Risk Amount / (Entry - Stop)
```

### 4. **簡化 IBKR 客户端** (`core/ibkr_client.py`)
改進的 API 層

- 錯誤處理更健壯
- 簡化的訂單下單方法
- 自動重連機制

### 5. **新交易引擎** (`main_v2.py`)
完全重設計的主程序

```
流程:
1. 連接 IBKR (TWS/Gateway)
2. 每 60 秒掃描一次 5 支柱股票（僅限 04:00-16:00 EST）
3. 每 5 秒監控現有持倉（24/7）
4. 自動進場/止盈/止蝕（進場僅限 04:00-16:00）
5. 記錄所有交易

交易時間:
- Pre-Market: 04:00-09:30 EST (可進場、掃描)
- Market Hours: 09:30-16:00 EST (可進場、掃描)
- After-Hours: 16:00-20:00 EST (不進場、只管理現有持倉)
- Closed: 20:00-04:00 EST (不進場、只管理現有持倉)
```

### 6. **回測框架** (`backtest/v2_backtester.py`)
驗證策略的績效

---

## 🚀 Windows 本地測試步驟

### 步驟 1: 克隆/更新代碼

**選項 A: 全新克隆（推薦）**
```cmd
cd C:\Users\illkh
rmdir /s /q my-code-project
git clone https://github.com/ngwingho1021/my-code-project.git my-code-project
cd my-code-project
git checkout claude/trading-system-stop-loss-profit-pwp2b0
```

**選項 B: 更新現有代碼**
```cmd
cd C:\Users\illkh\my-code-project
git fetch origin
git checkout claude/trading-system-stop-loss-profit-pwp2b0
git pull origin claude/trading-system-stop-loss-profit-pwp2b0
```

### 步驟 2: 安裝依賴

```cmd
pip install ib_async numpy pandas pytz python-dotenv
```

### 步驟 3: 設置 IBKR

1. 打開 **TWS** 或 **IB Gateway**
2. 登入 **Paper Trading 帳戶** (DUR065821)
3. File → Global Configuration → API → Settings
   - ✓ Enable ActiveX and Socket Clients
   - Socket Port: **7497**
4. Apply & OK

### 步驟 4: 運行新版本

```cmd
cd C:\Users\illkh\my-code-project
python main_v2.py
```

**預期看到的日誌**（前 30 秒）：
```
【Small-Cap Momentum Trader 啟動】
✅ IBKR 連線成功
帳戶: DUR065821
掃描 5 支柱小市值股票...
機械人已啟動，等待市場信號...

【風險管理狀態】
帳戶餘額: $5,000.00
今日損益: $0.00
今日交易: 0/12
現有持倉: 0/3
```

✅ 如果看到上述日誌 = **連接成功！**

---

## 📊 新架構的優勢

| 功能 | 舊版本 | 新版本 |
|------|--------|--------|
| **訂單狀態跟踪** | ❌ 混亂 | ✅ 清晰的 FSM |
| **5支柱篩選** | ⚠️ 硬編碼 | ✅ 可配置評分 |
| **風險管理** | ⚠️ 基礎 | ✅ 完整 9 項檢查 |
| **錯誤恢復** | ❌ 無 | ✅ 自動重試 |
| **可測試性** | ⚠️ 單體 | ✅ 模塊化 |
| **可維護性** | ⚠️ 困難 | ✅ 清晰的責任 |

---

## 📝 文件對應關係

```
新架構                           用途
─────────────────────────────────────────────────
core/order_state_machine.py     防止卡單 ← 昨日的主要問題
core/stock_selector.py          實現 5 支柱篩選
core/position_manager.py        風控邏輯
core/ibkr_client.py            IBKR API 層
main_v2.py                      主交易引擎 ← **運行這個**
backtest/v2_backtester.py       回測驗證

舊版本仍保留:
main.py                         舊版本（暫不用）
config/settings.py              配置文件 ✅ 繼續使用
utils/logger.py                日誌系統 ✅ 繼續使用
```

---

## 🧪 測試清單

**在真正交易前**，請驗證以下事項：

- [ ] 能成功連接 IBKR（看到 "✅ IBKR 連線成功"）
- [ ] 能成功掃描股票（看到 5 支柱股票被識別）
- [ ] 風險管理日誌正常輸出
- [ ] 沒有任何 "ERROR" 日誌（WARNING 可以忽略）
- [ ] 機械人運行 > 1 小時無崩潰

**如果出現問題**：

```
❌ "連接 IBKR 失敗"
   → 檢查 TWS 是否開啟，port 7497 是否正確，API 是否啟用

❌ "沒有 5 支柱股票"
   → 市場可能休盤，或符合條件的股票太少（正常）

❌ "Python 模塊缺失"
   → pip install ib_async numpy pandas pytz python-dotenv

❌ 機械人運行後立即崩潰
   → 檢查 config/settings.py，確認 PAPER_TRADING = True
```

---

## 📅 下一步

**今日（2026-08-17）**:
1. Windows 本地運行 `python main_v2.py`
2. 驗證連接穩定，掃描正常
3. 觀察整天（無需交易，只看信號）
4. 檢查日誌中是否有異常

**明日（2026-08-18）開始**:
1. 正式紙面交易（主要是進場信號）
2. 收集 1-2 週的交易數據
3. 計算勝率、利潤因子、最大回撤
4. 如果達標（40%+ WR, 1.5x+ PF），考慮小額真實盤

**後續（可選）**:
1. 使用 `backtest/v2_backtester.py` 驗證歷史數據
2. 調整 5 支柱的閾值（gap%, rvol, float 等）
3. 優化止盈/止蝕邏輯

---

## 💡 關鍵改進說明

### 為什麼昨日會"卡單"？
1. ❌ 訂單沒有明確的狀態機制
2. ❌ 多個訂單同時下達時的回調混亂
3. ❌ 沒有持倉追蹤，導致下單邏輯錯誤

### 新版本如何防止？
1. ✅ 每個訂單都有生命週期（PENDING → FILLED）
2. ✅ 訂單狀態機確保每個訂單只處理一次
3. ✅ 持倉管理器防止重複開倉或遺漏止蝕

### 5支柱評分系統有什麼好處？
```
舊方式: 硬編碼條件 (gap >= 5%) → 太機械化
新方式: 
  gap >= 10% → 25分 (最高)
  gap >= 5%  → 20分
  新聞催化   → 20分
  Float < 10M → 20分
  RVOL >= 3x → 20分
  股價 $2-20 → 15分
  
總分 > 70 分 = 推薦進場 ← 更靈活
```

---

## 📞 故障排除

| 症狀 | 原因 | 解決 |
|-----|------|------|
| "not a git repository" | 代碼未克隆 | 用步驟 1 重新克隆 |
| "ModuleNotFoundError" | 依賴缺失 | 運行 pip install |
| "連接超時" | IBKR 離線 | 重啟 TWS |
| 機械人無法下單 | 帳戶資金不足 | 檢查帳戶有 $5,000+ |
| 日誌中全是 ERROR | API 配置錯誤 | 檢查 config/settings.py |

---

**準備好？去 Windows 上運行 `python main_v2.py` 吧！** 🚀

---

Last Updated: 2026-08-17 22:30 UTC
