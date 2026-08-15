# ⚡ Backtest POC 使用指南

## 🎯 目的

這個 POC 用來**快速驗證 Ross Cameron 爆升股策略的有效性**，然後決定是否投入時間做完整重構。

---

## 🚀 快速開始

### 1. 安裝依賴

```bash
pip install pandas numpy yfinance
```

### 2. 運行回測

```bash
# 基礎回測（2024年6月-8月）
python scripts/run_backtest_simple.py --start 2024-06-01 --end 2024-08-15

# 調整參數
python scripts/run_backtest_simple.py \
  --start 2024-01-01 --end 2024-08-15 \
  --initial-cash 10000 \
  --risk-per-trade 100 \
  --gap-threshold 20 \
  --float-max 30000000

# 查看所有參數
python scripts/run_backtest_simple.py --help
```

### 3. 查看結果

回測完成後會看到這樣的輸出：

```
============================================================
【回測結果】
============================================================

📊 基本績效:
  總交易筆數: 48
  盈利交易: 29
  虧損交易: 19
  勝率: 60.4%

💰 資金績效:
  總淨利: $2,450.00
  收益率: +24.5%
  最終淨值: $12,450.00

📈 交易統計:
  平均盈利: $156.00
  平均虧損: -$89.00
  最大虧損: -$450.00
  利潤因子: 1.95

⚠️ 風控指標:
  最大回撤: -8.2%
  Sharpe 比率: 2.14

============================================================
```

---

## 📊 重要指標說明

| 指標 | 好的範圍 | 說明 |
|------|---------|------|
| **勝率** | > 50% | 盈利交易的佔比 |
| **收益率** | > 10% | 時間段內的總回報 |
| **利潤因子** | > 1.5 | 盈利總額 / 虧損總額 |
| **最大回撤** | < 20% | 帳戶從峰值跌落的最大幅度 |
| **Sharpe 比率** | > 1.0 | 風險調整後的收益 |

### 🎯 快速判斷

- ✅ **很有潛力**：勝率 > 55% + 利潤因子 > 2.0 + 回撤 < 15%
- 🟡 **還行**：勝率 > 50% + 利潤因子 > 1.5 + 回撤 < 20%
- ❌ **不建議**：勝率 < 50% 或 利潤因子 < 1.2

---

## 🔧 如何調試和改進

### 問題：勝率太低 (< 50%)

**可能原因**：
- Gap 門檻太高 → 候選股太少
- 止盈目標太高 → 難以達到

**解決**：
```bash
# 降低 gap 門檻到 15%
python scripts/run_backtest_simple.py --gap-threshold 15

# 或增加風險倍數（修改代碼中的 tp1/tp2 計算）
```

### 問題：最大虧損太大

**可能原因**：
- 單筆風險 ($100) 太高
- 止蝕設置不夠嚴格

**解決**：
```bash
# 減少單筆風險到 $50
python scripts/run_backtest_simple.py --risk-per-trade 50

# 或改進止蝕邏輯（需修改 simple_backtester.py）
```

### 問題：交易數太少

**可能原因**：
- Float 門檻太低 → 候選股少
- RVol 門檻太高

**解決**：
```bash
# 增加流通股上限到 50M
python scripts/run_backtest_simple.py --float-max 50000000

# 或降低 RVol 門檻到 3x（需修改代碼）
```

---

## 📁 文件結構

```
my-code-project/
├── backtest/
│   ├── __init__.py
│   ├── data_loader.py           # 數據加載
│   ├── simple_backtester.py     # 回測引擎
│   ├── cache/                   # 數據快取（自動生成）
│   └── README.md                # 詳細文檔
├── scripts/
│   └── run_backtest_simple.py   # 運行器
├── backtest_results.json        # 回測結果
└── BACKTEST_POC_GUIDE.md        # 本文檔
```

---

## ⚙️ 進階：參數掃描

如果想找最優參數組合：

```bash
# 簡單的參數掃描（手動）
for gap in 15 20 25 30; do
  echo "=== Testing gap=$gap ==="
  python scripts/run_backtest_simple.py --gap-threshold $gap
done
```

或編寫一個掃描腳本：

```python
# scan_params.py
import subprocess
import json

best_result = None
best_return = -999

for gap in [15, 20, 25, 30]:
    result = subprocess.run([
        'python', 'scripts/run_backtest_simple.py',
        '--gap-threshold', str(gap)
    ], capture_output=True, text=True)
    
    # 解析結果並比較
    # ...
```

---

## 🎯 決定下一步

### 如果回測結果 ✅ 好

```
勝率 > 55% + 利潤因子 > 2.0
         ↓
建議：投入時間做完整重構
├─ 改進 OrderManager（解決盤前掛單問題）
├─ 加入三批止盈邏輯
├─ 加入 Gemini AI 新聞過濾
└─ 紙上交易驗證 → 小額實盤
```

### 如果回測結果 ❌ 差

```
勝率 < 50% 或 利潤因子 < 1.2
         ↓
建議：先優化策略參數
├─ 調整 gap/float/rvol 門檻
├─ 改進進場/止盈邏輯
├─ 加入技術形態確認
└─ 重新回測驗證
```

---

## 🔗 後續計劃

### Phase 1：POC 驗證 ✅ (現在)
- 簡單回測框架
- 基本的績效指標

### Phase 2：改進回測 (下一步)
如果 Phase 1 結果好，實現：
- 分鐘級別 K 線模擬
- 更精細的進場/止盈邏輯
- 成交量/技術形態檢測
- 參數掃描工具

### Phase 3：修復實盤 (再下一步)
- OrderManager（解決盤前掛單）
- PositionTracker（倉位管理）
- StateMachine（訂單狀態追蹤）

### Phase 4：上線交易
- 紙上交易驗證（1-2週）
- 小額實盤（$1000-5000）
- 逐步加倉

---

## ⚠️ 重要提醒

1. **回測 ≠ 實盤**
   - 回測假設完美的成交（實盤有滑價）
   - 回測沒考慮 halt、流動性突變
   - 務必進行紙上交易驗證

2. **參數過擬合風險**
   - 找最優參數容易過擬合
   - 建議在不同時間段驗證

3. **策略本身風險**
   - Penny stocks 易被操縱
   - Halt 風險高
   - 務必嚴格執行止蝕

---

## 💬 常見問題

**Q: 運行回測需要多久？**

A: 取決於數據量
- 1 個月：30-60 秒
- 半年：2-5 分鐘
- 1 年：5-10 分鐘

**Q: 回測結果保存在哪？**

A: 
- 控制台輸出：實時看
- JSON 文件：`backtest_results.json`
- 交易明細：在控制台打印

**Q: 能否調整進場/止盈邏輯？**

A: 能的。需要修改 `simple_backtester.py` 中的 `run()` 方法和交易邏輯。

**Q: 能否加入 AI 審核？**

A: 能的。在 `generate_mock_candidates()` 中加入 `ai_filter_2.py` 的邏輯。

---

## 📞 遇到問題？

常見錯誤：

### `ModuleNotFoundError: No module named 'pandas'`
```bash
pip install pandas numpy yfinance
```

### `ConnectionError` (無法下載數據)
網絡代理問題，可以：
- 檢查網絡連接
- 用快取數據（已有的話）
- 降低下載量

### 回測結果都是 0
檢查 `generate_mock_candidates()` 是否生成了候選股票。

---

## 🚀 下一個行動

1. ✅ **立即做**：運行這個 POC，看一個月的回測結果
2. 📊 **根據結果**：決定是否投入做完整版
3. 💰 **如果好**：做 Phase 2 和 Phase 3 的改進
4. 📈 **最後**：紙上交易驗證，再上實盤

---

**準備好了嗎？** 開始跑回測吧！

```bash
python scripts/run_backtest_simple.py --start 2024-06-01 --end 2024-08-15
```

祝你好運！ 🍀
