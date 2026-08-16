# IBKR 回測指南

## 概述
系統現在支持使用 IBKR (Interactive Brokers) 作為回測數據源，無需依賴 Alpaca API。這特別適合已經有 IBKR 账户的用户。

## 前置條件

### 1. IBKR TWS 或 IB Gateway 運行
必須在本地運行以下之一：
- **TWS (Trader Workstation)** - 完整的交易平台
- **IB Gateway** - 輕量級應用 (推薦)

#### 下載和安裝
- 訪問 https://www.interactivebrokers.com/en/trading/platforms
- 選擇 TWS 或 IB Gateway
- 安裝並啟動應用

### 2. 啟用 API 連接
在 TWS/IB Gateway 中：
1. 進入 **配置 (Configuration)**
2. 選擇 **API** > **Settings**
3. 啟用 API
4. 設定以下參數：
   - **Socket port**: 7497 (紙交易) 或 7496 (實盤)
   - **Enable ActiveX and Socket Clients**: 勾選
   - **Read-Only API**: 可選（安全建議勾選）

### 3. 配置 .env 文件
確保 `.env` 文件包含 IBKR 連接參數：

```env
# IBKR 配置（回測用）
IB_HOST=127.0.0.1
IB_PORT=7497                    # 紙交易端口 (7496=實盤)
IB_CLIENT_ID=1
PAPER_TRADING=True              # 必須為 True

# Alpaca 配置（如果使用 --data-source alpaca）
ALPACA_API_KEY=your_api_key
ALPACA_SECRET_KEY=your_secret_key
ALPACA_BASE_URL=https://paper-api.alpaca.markets
```

## 使用方法

### 基本用法 - 使用 IBKR 數據

```bash
python backtest_runner.py \
  --symbol AAPL \
  --start 2024-01-01 \
  --end 2024-12-31 \
  --data-source ibkr
```

### 高級選項

#### 1. 自定義時間框架
IBKR 支持的時間框架：
- `1 Min` - 1分鐘
- `5 Mins` - 5分鐘
- `15 Mins` - 15分鐘
- `1 hour` - 1小時
- `1 day` - 1日

```bash
python backtest_runner.py \
  --symbol SPY \
  --start 2024-06-01 \
  --end 2024-06-30 \
  --timeframe "5 Mins" \
  --data-source ibkr
```

#### 2. 自定義初始資本和滑點
```bash
python backtest_runner.py \
  --symbol TSLA \
  --start 2024-01-01 \
  --end 2024-06-30 \
  --capital 50000 \
  --slippage 1.0 \
  --data-source ibkr
```

#### 3. 自定義報告輸出目錄
```bash
python backtest_runner.py \
  --symbol NVDA \
  --start 2024-01-01 \
  --end 2024-03-31 \
  --output my_backtest_reports \
  --data-source ibkr
```

### 完整示例
```bash
python backtest_runner.py \
  --symbol AAPL \
  --start 2024-03-01 \
  --end 2024-03-31 \
  --timeframe "1 Min" \
  --capital 25000 \
  --slippage 0.5 \
  --output backtest_reports \
  --data-source ibkr
```

## Alpaca vs IBKR 數據源對比

| 特性 | Alpaca | IBKR |
|------|--------|------|
| 盤前數據 | ✅ 包含 | ✅ 可用 |
| API 密鑰 | 需要 | ❌ 不需要 |
| 本地連接 | ❌ 遠程 | ✅ 本地 |
| 初始設置 | 複雜 | 中等 |
| 可靠性 | 高 | 高 |
| 成本 | 免費 | 免費 (已有账户) |

## 故障排除

### 連接錯誤：Connection refused
**問題**: `IBKR 連線失敗...`

**解決方案**:
1. 確認 TWS/IB Gateway 已啟動
2. 檢查端口設置 (7497 for 紙交易)
3. 確認 API 已在 TWS 中啟用

```bash
# 診斷連接
python -c "from core.ibkr_client import IBKRClient; c = IBKRClient(); c.connect()"
```

### 無數據錯誤
**問題**: `無法確認合約: Stock(...)`

**解決方案**:
1. 確認股票代碼正確 (例: AAPL, 而不是 Apple)
2. 股票必須在美股交易所交易
3. 檢查日期範圍是否包含交易日

### 超時錯誤
**問題**: `連接超時`

**解決方案**:
1. 增加 IBKRClient 中的 timeout 參數 (目前: 15秒)
2. 檢查網絡連接
3. 嘗試重啟 TWS/IB Gateway

## 回測報告

回測完成後，會生成以下文件：

```
backtest_reports/
├── backtest_AAPL_2024-01-01_2024-12-31.html  # 可視化報告
└── backtest_AAPL_2024-01-01_2024-12-31.json  # 詳細數據
```

### HTML 報告包含:
- 📈 淨值曲線 (Equity Curve)
- 📊 回撤曲線 (Drawdown)
- 📋 交易統計 (Win Rate, 最大虧損, 等)
- 📝 交易列表 (每筆交易詳情)

### 在瀏覽器中查看
```bash
# Windows
start backtest_reports/backtest_AAPL_*.html

# macOS
open backtest_reports/backtest_AAPL_*.html

# Linux
xdg-open backtest_reports/backtest_AAPL_*.html
```

## 性能建議

### 1. 時間框架選擇
- **1分鐘**: 快速迭代，適合日內交易測試
- **5分鐘**: 平衡精度與速度
- **1小時+**: 更長期的趨勢分析

### 2. 數據範圍
- 建議測試期間: **1-3個月**
- 對於策略優化: 從短期開始，逐步擴展
- 避免超過 1 年，除非有足夠計算資源

### 3. 快速測試
```bash
# 快速測試一周數據
python backtest_runner.py \
  --symbol SPY \
  --start 2024-06-03 \
  --end 2024-06-07 \
  --timeframe "5 Mins" \
  --data-source ibkr
```

## 自定義策略

如果要修改交易策略邏輯，編輯:
- `strategy/gap_momentum_strategy.py` - 主策略文件
- `core/indicators.py` - 技術指標計算

然後重新運行回測即可自動應用新邏輯。

## 下一步

1. ✅ 完成 IBKR 回測
2. 📊 分析回測結果
3. 🚀 切換到紙交易模式 (實時盤前信號)
4. 💰 (可選) 遷移到實盤交易

## 聯繫與支持

如遇到問題：
1. 檢查本文檔的故障排除部分
2. 查看日志輸出 (通常包含詳細錯誤信息)
3. 驗證 .env 配置正確
4. 確認 IBKR 連接正常
