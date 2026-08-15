# Backtest POC — 簡單回測框架

## 概述

這是一個簡單的回測框架，用於驗證 Ross Cameron 爆升股交易策略的有效性。

**目的**：在投入時間做完整重構之前，先用歷史數據驗證策略是否真的有效。

---

## 使用方法

### 1. 安裝依賴

```bash
pip install pandas numpy yfinance
```

### 2. 運行回測

```bash
python scripts/run_backtest_simple.py --start 2024-01-01 --end 2024-08-15
```

### 3. 查看結果

回測完成後，會在控制台打印績效報告，並將詳細結果保存到 `backtest_results.json`。

---

## 參數說明

| 參數 | 預設值 | 說明 |
|------|--------|------|
| `--start` | 2024-01-01 | 回測開始日期 |
| `--end` | 2024-08-15 | 回測結束日期 |
| `--initial-cash` | 10000 | 初始資金（$） |
| `--risk-per-trade` | 100 | 每筆交易風險（$） |
| `--gap-threshold` | 20.0 | Gap Up 門檻（%） |
| `--float-max` | 30e6 | 最大流通股（shares） |
| `--rvol-min` | 5.0 | 最小相對成交量（倍） |

### 範例：調整參數

```bash
# 更嚴格的篩選（gap ≥ 30%, float ≤ 20M）
python scripts/run_backtest_simple.py \
  --start 2024-01-01 --end 2024-08-15 \
  --gap-threshold 30.0 \
  --float-max 20000000

# 更激進的風險（每筆 $150）
python scripts/run_backtest_simple.py \
  --risk-per-trade 150
```

---

## 文件結構

```
backtest/
├── __init__.py
├── data_loader.py          # 數據加載（yfinance）
├── simple_backtester.py    # 回測引擎
├── cache/                  # 數據快取目錄
└── README.md               # 本文檔

scripts/
└── run_backtest_simple.py  # 回測運行器

backtest_results.json       # 回測結果（運行後生成）
```

---

## 績效指標

回測會輸出以下指標：

### 基本績效
- **總交易筆數**：回測期間執行的交易總數
- **盈利交易**：賺錢的交易數
- **虧損交易**：賠錢的交易數
- **勝率**：盈利交易占比

### 資金績效
- **總淨利**：絕對收益（$）
- **收益率**：相對收益（%）
- **最終淨值**：回測結束時的帳戶總值

### 交易統計
- **平均盈利**：每筆賺錢交易的平均收益
- **平均虧損**：每筆賠錢交易的平均虧損
- **最大虧損**：單筆最大損失
- **利潤因子**：總利潤 / 總損失（>2.0 視為良好）

### 風控指標
- **最大回撤**：帳戶從峰值跌落的最大百分比
- **Sharpe 比率**：風險調整後的收益率（>1.0 視為良好）

---

## 目前限制

這個 POC 版本有一些簡化假設：

❌ **簡化的進場邏輯**
- 目前假設盤開時進場
- 實際應該使用真實的 K 線突破邏輯

❌ **簡化的止盈邏輯**
- 目前假設當日能觸發止盈
- 實際應該跟蹤多日，支持 Runner 批次

❌ **沒有實時掃描**
- 目前用硬編碼的候選股列表
- 實際應該連接 IBKR 掃描器

❌ **沒有 AI 過濾**
- 目前跳過了 Gemini 新聞審核
- 實際應該加入催化劑過濾

---

## 下一步

### 如果回測結果好 ✅

1. 進行參數掃描，找最優組合
2. 實現完整版回測框架（支持更複雜的邏輯）
3. 改進 OrderManager，修復實盤掛單問題
4. 上線小額實盤驗證

### 如果回測結果差 ❌

1. 分析失敗原因（gap 門檻太高？流動性不足？）
2. 調整策略參數
3. 重新回測
4. 考慮改進進場邏輯

---

## 故障排除

### 問題：缺少模塊

```
ModuleNotFoundError: No module named 'pandas'
```

**解決**：安裝依賴

```bash
pip install pandas numpy yfinance
```

### 問題：無法下載數據

```
NameError: yfinance 無法連接
```

**解決**：檢查網絡連接，或增加重試次數

```python
# 在 data_loader.py 中修改
df = yf.download(
    symbol,
    start=start_date,
    end=end_date,
    progress=False,
    prepost=True,
    retry=5  # 重試次數
)
```

---

## 常見問題

**Q: 回測結果應該看哪個指標？**

A: 重點看：
- 勝率 > 50%
- 利潤因子 > 1.5
- 最大回撤 < 20%

**Q: 回測是否準確反映實盤效果？**

A: 不完全準確，因為：
- 回測用日線，實盤用分鐘線
- 滑價 (slippage) 和佣金未計入
- 沒考慮 halt、liquidity 問題

建議用回測作為初步篩選，最終要紙上交易驗證。

**Q: 如何優化參數？**

A: 手動嘗試不同組合：

```bash
# 嘗試不同的 gap threshold
for gap in 15 20 25 30; do
  echo "Testing gap=$gap"
  python scripts/run_backtest_simple.py --gap-threshold $gap
done
```

---

## 代碼說明

### data_loader.py

- `get_daily_bars()` - 下載並快取歷史日線
- `get_gap_up_stocks()` - 找 gap up 股票
- `get_stock_info()` - 獲取基本信息（float, 等）

### simple_backtester.py

- `SimpleBacktester` - 主回測類
- `Trade` - 交易記錄（entry/exit/pnl）
- `run()` - 主回測循環
- `_calculate_metrics()` - 計算績效指標

### run_backtest_simple.py

- `main()` - 程序入口
- `get_trading_dates()` - 生成交易日期
- `generate_mock_candidates()` - 生成候選股票
- `print_report()` - 打印績效報告

---

## 貢獻與改進

POC 完成後，可擴展為完整版：

1. **更複雜的進場邏輯**
   - 盤前 K 線突破
   - VWAP 確認
   - 技術形態檢測

2. **更複雜的止盈邏輯**
   - 三批止盈（+2R / +3R / Runner）
   - 跟蹤止蝕
   - 隱形賣家偵測

3. **更好的數據源**
   - 連接 IBKR 實時數據
   - 分鐘級別 K 線
   - 深度和成交量

4. **性能優化**
   - 多進程回測
   - 參數掃描並行化
   - 結果存儲到數據庫

---

**生成日期**：2024-08-15  
**作者**：Claude Code
