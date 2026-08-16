# 📊 真實數據驗證指南

## 🔍 當前狀況

### 網絡限制
遠端執行環境的代理阻止了 yfinance 下載：
```
ConnectionError: curl: (7) CONNECT tunnel failed, response 403
```

### 解決方案
提供 **3 種數據驗證方式**：

---

## 📋 方式 1：上傳 CSV 數據（推薦）

### 步驟 1：準備 CSV 文件

CSV 格式示例：
```
Date,Open,High,Low,Close,Volume
2024-06-01,100.0,102.5,99.5,101.0,1000000
2024-06-02,101.5,104.0,101.0,103.0,1200000
2024-06-03,103.0,105.5,100.0,104.5,900000
```

**來源**：
- Yahoo Finance 下載（自己電腦）
- ThinkorSwim 匯出
- 其他交易平台歷史數據
- Polygon.io API（免費層）

### 步驟 2：上傳到項目

```bash
# 在項目中建立 csv_data 目錄
mkdir -p backtest/csv_data

# 將 CSV 文件放入
cp ~/Downloads/NVDA.csv backtest/csv_data/
cp ~/Downloads/AMD.csv backtest/csv_data/
```

### 步驟 3：運行回測

```bash
# 單個股票
python scripts/run_backtest_with_real_or_mock.py \
  --mode csv \
  --csv backtest/csv_data/NVDA.csv \
  --gap 2 \
  --risk-per-trade 100

# 或用改進的 mock 數據對比
python scripts/run_backtest_with_real_or_mock.py \
  --mode mock \
  --days 120 \
  --gap 2 \
  --risk-per-trade 100
```

---

## 📈 數據驗證結果對比

### 改進前 Mock 數據（參數掃描結果）

| Gap | Trades | Win Rate | Profit Factor | PnL |
|-----|--------|----------|---------------|-----|
| 2%  | 29     | 24.1%    | 1.04          | +$11-60 |
| 3%  | 19     | 15.8%    | 0.40          | -$129-788 |
| 5%+ | 0-7    | 0%       | 0.00          | -$0-560 |

### 改進後 Mock 數據（初步測試）

**Gap=1%（100天，風險$100）**：
- 交易筆數：16
- 盈利交易：2
- 虧損交易：14
- **總淨利：-$699 (-7.0%)**
- 勝率：12.5%

**發現**：
- ❌ 結果更差（-7% vs 之前的 -0.5%）
- ❌ 大多數交易在平倉（close）結束
- ❌ TP1/TP2 目標很少達到

---

## 🎯 關鍵洞察

### 問題 1：TP1/TP2 難以達到

在改進的 mock 數據中，大多交易平倉 (close)，而不是達到止盈：

```
❌ [2026-05-04] STOCK_A: $16.02→$15.21 (close) | qty=96 | PnL=$-78
✅ [2026-07-17] STOCK_A: $10.80→$10.88 (close) | qty=935 | PnL=$+71
```

**原因**：
- 止盈目標設置過高（entry + 3x risk）
- 股票沒有足夠的日內波動達到目標
- 當日走勢反向導致虧損平倉

### 問題 2：Gap Up 本身不保證盈利

Mock 數據表明，僅靠 gap up 條件不足以創建盈利策略。需要：
- ✅ 更多進場條件（例如：成交量確認、技術形態）
- ✅ 動態止盈（不是固定的 3x risk）
- ✅ 更嚴格的止蝕邏輯

### 問題 3：交易次數減少

改進的 mock 邏輯使交易減少（但質量可能更高）。

---

## 🔧 策略改進方向

### 改進 1：增加進場條件

```python
# 當前邏輯（太簡單）
if gap >= 2%:
    enter()

# 改進邏輯（多重確認）
if gap >= 2% AND \
   volume > 2M AND \
   close_above_open AND \
   high > open:
    enter()
```

### 改進 2：動態止盈

```python
# 當前邏輯（固定倍數）
tp1 = entry + risk * 2.0
tp2 = entry + risk * 3.0

# 改進邏輯（基於日內波動）
atr = calculate_atr()  # 平均真幅
tp1 = entry + atr * 1.5
tp2 = entry + atr * 2.5
```

### 改進 3：改進止蝕

```python
# 當前邏輯（固定金額）
stop = low - 0.05

# 改進邏輯（百分比 + 支撐位）
stop = max(
    entry * 0.98,          # Entry 下方 2%
    today_low * 0.99       # 當日低點下方 1%
)
```

### 改進 4：風險管理

```python
# 加入最大回撤控制
if current_drawdown > max_allowed_drawdown:
    stop_trading_today = True

# 加入每日止損
if daily_loss > daily_loss_limit:
    stop_trading_today = True
```

---

## 📊 下一步行動計劃

### 階段 1：數據驗證 🔄 當前

- [ ] 準備實際 CSV 數據（6 個月或 1 年的 gap up 股票）
- [ ] 運行 CSV 回測，對比 mock 結果
- [ ] 驗證 mock 數據的準確性

### 階段 2：策略改進 📝

- [ ] 實現改進的進場條件
- [ ] 調整止盈目標（更現實的 R:R 比）
- [ ] 改進止蝕邏輯
- [ ] 重新運行回測

### 階段 3：再次驗證 ✅

- [ ] 用改進的策略重新運行 mock 回測
- [ ] 對比改進前後的結果
- [ ] 評估是否達到目標績效（勝率 > 55%, PF > 1.5）

### 階段 4：實盤驗證 🚀

- [ ] 用實際數據驗證
- [ ] 紙上交易（模擬交易）
- [ ] 小額實盤測試

---

## 💾 數據準備清單

### 自動下載方式（在個人電腦上）

```python
import yfinance as yf

# 下載 NVDA 的 6 個月數據
df = yf.download('NVDA', start='2024-01-01', end='2024-08-31')

# 保存為 CSV
df.to_csv('NVDA.csv')

# 重複其他股票：TSLA, AMD, PLTR, etc.
```

### 手動方式

1. 訪問 https://finance.yahoo.com/
2. 搜索股票代碼
3. 下載 "Historical Data" CSV
4. 上傳到 `backtest/csv_data/`

---

## 🧪 驗證測試

### 測試 1：Single Stock CSV

```bash
python scripts/run_backtest_with_real_or_mock.py \
  --mode csv \
  --csv backtest/csv_data/NVDA.csv \
  --gap 2 \
  --days 120
```

**預期結果**：
- 應該看到實際的 gap up 日期
- 交易結果應該與真實市場相符
- 勝率應該比 mock 更低（因為 mock 太樂觀）

### 測試 2：參數對比

```bash
# Mock 版本
python scripts/parameter_sweep.py

# vs CSV 版本
python scripts/run_backtest_with_real_or_mock.py --mode csv --csv NVDA.csv
```

**對比指標**：
- 勝率差異
- 利潤因子差異
- 平均贏損比差異

---

## 📋 常見問題

**Q: 為什麼改進的 mock 數據結果更差？**

A: 改進的邏輯更接近真實市場：
- 去掉了不切實際的極高波動
- 更現實的止盈達成率
- 這是好事，說明 mock 數據更準確

**Q: 如何確保 CSV 數據格式正確？**

A: 檢查 5 點：
1. 列名正確：Date, Open, High, Low, Close, Volume
2. 日期格式：YYYY-MM-DD
3. 價格為浮點數
4. 成交量為整數
5. High > Low

**Q: 要多少數據才夠？**

A: 建議：
- 最少：3 個月（60 個交易日）
- 理想：6-12 個月（200-250 個交易日）
- 越多越好（避免過擬合）

**Q: 如何生成 CSV 文件？**

A: 在你的個人電腦上：
```bash
pip install yfinance
python -c "
import yfinance as yf
yf.download('NVDA', start='2024-01-01', end='2024-08-31').to_csv('NVDA.csv')
"
```

---

## 🚀 立即開始

### 快速上手（5 分鐘）

1. **下載示例數據**（在個人電腦）
   ```bash
   pip install yfinance pandas
   python -c "
   import yfinance as yf
   for ticker in ['NVDA', 'AMD', 'TSLA']:
       yf.download(ticker, start='2024-06-01', end='2024-08-31').to_csv(f'{ticker}.csv')
   "
   ```

2. **上傳 CSV**
   ```bash
   cp NVDA.csv backtest/csv_data/
   ```

3. **運行回測**
   ```bash
   python scripts/run_backtest_with_real_or_mock.py \
     --mode csv --csv backtest/csv_data/NVDA.csv --gap 2
   ```

4. **檢查結果**
   ```bash
   cat backtest_results_csv.json
   ```

---

## 📞 遇到問題？

| 問題 | 解決方案 |
|------|---------|
| CSV 文件找不到 | 檢查路徑，確保在 `backtest/csv_data/` 目錄 |
| 列名錯誤 | 編輯 CSV，確保首行是 `Date,Open,High,Low,Close,Volume` |
| 沒有交易生成 | 降低 gap 門檻或增加股票數據 |
| 結果不合理 | 檢查數據品質，是否有缺失或錯誤值 |

---

**下一步**：準備 CSV 數據，運行真實驗證！ 🎯
