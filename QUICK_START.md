# 小盤動量交易機械人 - 快速啟動指南

## 前置要求

✅ **Python 3.9+** - [下載 Python](https://www.python.org/downloads/)
✅ **IBKR TWS 或 Gateway** - 需要運行中
✅ **已配置的 config/settings.py** - IBKR 連接參數

## 安裝依賴

在項目根目錄運行：

### Windows (CMD)
```batch
pip install -r requirements.txt
```

### macOS/Linux (Terminal)
```bash
pip3 install -r requirements.txt
```

## 啟動機械人

### 方式 1: 使用啟動脚本（推薦）

**Windows:**
```batch
run.bat
```

**macOS/Linux:**
```bash
chmod +x run.sh
./run.sh
```

### 方式 2: 直接運行 Python

**Windows (CMD):**
```batch
cd /d C:\Users\illkh\Desktop\Trading bots
python run.py
```

**macOS/Linux:**
```bash
cd ~/path/to/project
python3 run.py
```

## 常見錯誤及解決方案

### ❌ `ModuleNotFoundError: No module named 'config'`

**原因**: 不在項目根目錄運行

**解決**:
1. 在文件管理器中進入項目文件夾
2. 在地址欄輸入: `cmd` (Windows) 或 `terminal` (macOS)
3. 或者用命令行:
```batch
cd C:\Users\illkh\Desktop\Trading bots
python run.py
```

### ❌ `ModuleNotFoundError: No module named 'ib_async'`

**原因**: 缺少依賴

**解決**:
```batch
pip install -r requirements.txt
```

### ❌ `ConnectionError: IBKR 連接失敗`

**原因**: IBKR TWS/Gateway 未運行

**解決**:
1. 打開 IBKR TWS 或 Gateway
2. 確保在 `config/settings.py` 中配置的 host/port 正確
3. 默認: `127.0.0.1:7497` (Paper Trading)

## 驗證安裝

運行此命令驗證所有依賴已正確安裝：

```bash
python -c "from config.settings import TRADING_HOURS, ACCOUNT_RISK; print('✅ 配置已加載'); from core.small_cap_momentum_bot_ibkr_client import IBKRClient; print('✅ IBKR 客戶端已加載')"
```

如果看到 `✅` 標記，說明安裝正確。

## 配置檢查清單

啟動前檢查以下項目：

- [ ] IBKR TWS 或 Gateway 正在運行
- [ ] `config/settings.py` 中的連接參數正確
- [ ] `PAPER_TRADING = True` (安全起見)
- [ ] 所有依賴已安裝 (`pip install -r requirements.txt`)
- [ ] 在項目根目錄運行腳本

## 監控運行

啟動後，你應該看到：

```
============================================================
【Small-Cap Momentum Trader 啟動】
============================================================
連接 IBKR 127.0.0.1:7497 clientId=17 ...
✅ IBKR 連線成功
帳戶: DU123456
⏰ 時間狀態: Pre-Market (04:00-09:30)
機械人已啟動，等待市場信號...
```

## 實時監控日誌

打開新的終端窗口監控日誌：

**Windows:**
```batch
type logs\small_cap_momentum_bot_main.log
```

**macOS/Linux:**
```bash
tail -f logs/small_cap_momentum_bot_main.log
```

## 停止機械人

按 `Ctrl + C` 安全關閉機械人。機械人會：
1. 取消所有待處理訂單
2. 保存最終狀態
3. 斷開 IBKR 連線
4. 記錄日誌

## 故障排查

### 日誌位置
- **主日誌**: `logs/small_cap_momentum_bot_main.log`
- **交易日誌**: `logs/trades.log`
- **訂單日誌**: `logs/order_state_machine.log`

### 檢查連接
```bash
python -c "from core.small_cap_momentum_bot_ibkr_client import IBKRClient; c = IBKRClient(); c.connect(); print('✅ IBKR 連接正常')"
```

## 需要幫助?

查看完整文檔:
- 架構設計: `ARCHITECTURE_REBUILD_GUIDE.md`
- 交易邏輯: `STRATEGY_LOGIC.md`
- 風控系統: `POSITION_MANAGEMENT_GUIDE.md`
- 故障排查: `BOT_RESTART_GUIDE.md`

---

**提示**: 第一次運行時，機械人會在日誌中打印詳細的連接和配置信息。檢查日誌確保所有元件正確加載。
