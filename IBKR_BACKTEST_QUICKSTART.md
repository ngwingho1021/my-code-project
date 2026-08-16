# IBKR 回測快速開始 (5分鐘設置)

## 核心變更
✅ **核心/ibkr_client.py** 新增 `get_historical_bars()` 方法
✅ **回測引擎** 支持 IBKR 作為數據源 (--data-source ibkr)
✅ **完整文檔** 和測試工具已提供

---

## 3 個簡單步驟

### 步驟 1: 配置 IBKR (3分鐘)

**前置條件**:
- Windows/Mac/Linux 上安裝 TWS 或 IB Gateway
  - 下載: https://www.interactivebrokers.com/en/trading/platforms
  - 推薦: IB Gateway (更輕量)

**配置 API**:
1. 啟動 TWS/IB Gateway
2. 進入 **配置 (Configuration)**
3. 選擇 **API** > **Settings**
4. ✅ 勾選 **Enable ActiveX and Socket Clients**
5. 確認 **Socket port**: 7497 (紙交易) 或 7496 (實盤)

**驗證 .env**:
```bash
# 項目根目錄的 .env 文件
IB_HOST=127.0.0.1
IB_PORT=7497
IB_CLIENT_ID=1
PAPER_TRADING=True
```

### 步驟 2: 測試連接 (1分鐘)

```bash
# 運行測試套件
python test_ibkr_backtest.py
```

**預期輸出**:
```
✅ IBKR 連接成功!
✅ 成功獲取 XXX 根K線
✅ 合約確認成功
```

### 步驟 3: 運行回測 (1分鐘)

```bash
# 基本用法
python backtest_runner.py \
  --symbol SPY \
  --start 2024-03-01 \
  --end 2024-03-31 \
  --data-source ibkr
```

查看報告: `backtest_reports/backtest_SPY_*.html`

---

## 常見命令

### 快速測試 (數據量小)
```bash
python backtest_runner.py \
  --symbol AAPL \
  --start 2024-06-03 \
  --end 2024-06-07 \
  --timeframe "5 Mins" \
  --data-source ibkr
```

### 詳細回測 (1個月數據)
```bash
python backtest_runner.py \
  --symbol SPY \
  --start 2024-06-01 \
  --end 2024-06-30 \
  --capital 50000 \
  --slippage 1.0 \
  --data-source ibkr
```

### 對比測試 (Alpaca vs IBKR)
```bash
# 使用 Alpaca
python backtest_runner.py --symbol SPY --start 2024-03-01 --end 2024-03-31 --data-source alpaca

# 使用 IBKR
python backtest_runner.py --symbol SPY --start 2024-03-01 --end 2024-03-31 --data-source ibkr
```

---

## 故障排除 (2分鐘)

### ❌ "連線失敗"
```
解決方案:
1. 確認 TWS/IB Gateway 已啟動
2. 檢查 API 是否已在配置中啟用
3. 驗證防火牆允許 127.0.0.1:7497
```

### ❌ "無K線數據"
```
解決方案:
1. 股票代碼檢查 (例: AAPL, 不是 Apple)
2. 日期範圍需在交易日內
3. 確認股票在美股交易所上市
```

### ⚠️ 超時或連接緩慢
```
解決方案:
1. 檢查網絡連接
2. 重啟 TWS/IB Gateway
3. 嘗試減少日期範圍
```

---

## 完整功能清單

### 支持的時間框架
- ✅ 1 Min (1分鐘)
- ✅ 5 Mins (5分鐘)
- ✅ 15 Mins (15分鐘)
- ✅ 1 hour (1小時)
- ✅ 1 day (1日)

### 支持的參數
```bash
--symbol        股票代碼 (AAPL, SPY, TSLA, etc.)
--start         開始日期 (YYYY-MM-DD)
--end           結束日期 (YYYY-MM-DD)
--timeframe     時間框架 (預設: 1Min)
--capital       初始資本 (預設: 25000)
--slippage      滑點% (預設: 0.5)
--data-source   數據源 (alpaca|ibkr) (預設: alpaca)
--output        報告輸出目錄 (預設: backtest_reports)
```

---

## 完整文檔

詳細信息請見:
- **IBKR_BACKTEST_GUIDE.md** - 完整使用指南和故障排除
- **IBKR_IMPLEMENTATION_SUMMARY.md** - 技術架構和設計決策

---

## 核心代碼示例

### Python 直接調用
```python
from core.ibkr_client import IBKRClient
import pandas as pd

# 初始化客戶端
client = IBKRClient()
client.connect()

# 獲取歷史數據
df = client.get_historical_bars(
    symbol="AAPL",
    start_date="2024-01-01",
    end_date="2024-06-30",
    timeframe="1 Min"
)

print(df.head())
client.disconnect()
```

### 回測集成
```python
from backtest.backtester import Backtester

# 使用 IBKR 作為數據源
backtester = Backtester(
    initial_capital=25000,
    slippage_pct=0.5,
    data_source="ibkr"  # 關鍵參數
)

# 運行回測 (需要異步執行)
result = await backtester.run(
    symbol="SPY",
    start_date="2024-01-01",
    end_date="2024-06-30",
    signal_func=my_strategy_signal
)
```

---

## 下一步

### 立即可做
1. ✅ 運行 `test_ibkr_backtest.py` 驗證設置
2. ✅ 回測歷史數據驗證策略
3. ✅ 調整策略參數優化績效

### 後續功能
- 🔜 實時紙交易 (Alpaca 信號 + IBKR 執行)
- 🔜 Web Dashboard 實時監控
- 🔜 多股票批量回測
- 🔜 實盤交易 (需謹慎)

---

## 成功確認清單

- [ ] IBKR/TWS 已啟動
- [ ] API 已在配置中啟用
- [ ] .env 文件已配置
- [ ] `test_ibkr_backtest.py` 全部通過
- [ ] 成功運行至少一個回測
- [ ] 生成了 HTML 報告

✅ 全部完成 → 準備好進行紙交易!

---

**需要幫助?**
- 查看詳細文檔: `IBKR_BACKTEST_GUIDE.md`
- 查看技術細節: `IBKR_IMPLEMENTATION_SUMMARY.md`
- 運行診斷: `python test_ibkr_backtest.py`
