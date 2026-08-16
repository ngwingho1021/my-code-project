# 🪟 Windows 快速開始指南

## ⚠️ 常見問題

### 問題：多行命令無法運行

**錯誤信息**：
```
'import' is not recognized as an internal or external command
'"python scripts/run_backtest_with_real_or_mock.py \' is not recognized
```

**原因**：Windows CMD 不支持 Unix 風格的多行命令（用 `\` 換行）

**解決方案**：使用提供的 Python 脚本

---

## 🚀 Windows 三步開始

### 第 1 步：下載真實數據

**在 `C:\Users\illkh\my-code-project>` 目錄執行**：

```bash
python download_real_data.py
```

**預期輸出**：
```
【下载真实股票数据】
============================================================
股票代码: NVDA, AMD, TSLA, PLTR, AAPL, MSFT, GOOGL, META
时间范围: 2024-01-01 ~ 2024-08-31
输出目录: backtest/csv_data/

开始下载...

⬇️  NVDA   ✅ 完成 (165 行)
⬇️  AMD    ✅ 完成 (165 行)
⬇️  TSLA   ✅ 完成 (165 行)
...

下载完成: 8/8 成功
保存位置: C:\Users\illkh\my-code-project\backtest\csv_data
```

### 第 2 步：運行回測（單個股票）

**用 CSV 數據測試 NVDA**：

```bash
python scripts/run_backtest_with_real_or_mock.py --mode csv --csv backtest/csv_data/NVDA.csv --gap 2 --risk-per-trade 100
```

**或用 Mock 數據對比**：

```bash
python scripts/run_backtest_with_real_or_mock.py --mode mock --days 120 --gap 2 --risk-per-trade 100
```

### 第 3 步：查看結果

**CSV 結果**：
```bash
type backtest_results_csv.json
```

**Mock 結果**：
```bash
type backtest_results_mock_improved.json
```

---

## 📊 對比 Mock 和真實數據

### 第 1 步：運行 Mock 回測

```bash
python scripts/run_backtest_with_real_or_mock.py --mode mock --days 120 --gap 2
```

記下結果（PnL, Win Rate, Profit Factor）

### 第 2 步：運行 CSV 回測

```bash
python scripts/run_backtest_with_real_or_mock.py --mode csv --csv backtest/csv_data/NVDA.csv --gap 2
```

記下結果

### 第 3 步：對比

```
Mock 結果（理想條件）vs 真實結果（實際交易）
-------------------------------------------------
勝率：        XX% vs YY% （通常下降 5-15%）
利潤因子：    X.XX vs Y.YY
淨利潤：      $XXX vs $YYY
```

---

## 🔧 Windows CMD 常用命令

### 查看文件列表

```bash
dir backtest\csv_data
```

### 查看 JSON 結果

```bash
type backtest_results_real_data.json
```

### 查看日誌

```bash
python download_real_data.py > download.log 2>&1
type download.log
```

### 刪除舊數據（重新下載）

```bash
rmdir /s backtest\csv_data
mkdir backtest\csv_data
python download_real_data.py
```

---

## 📝 完整命令參考

### 下載數據

| 目的 | 命令 |
|------|------|
| 下載 6 個月數據 | `python download_real_data.py` |
| 自訂股票列表 | 編輯 `download_real_data.py` 中的 `symbols` |

### 運行回測

| 目的 | 命令 |
|------|------|
| Mock 模式（默認） | `python scripts/run_backtest_with_real_or_mock.py --mode mock --days 120` |
| CSV 模式（單個） | `python scripts/run_backtest_with_real_or_mock.py --mode csv --csv backtest/csv_data/NVDA.csv` |
| 參數掃描 | `python scripts/parameter_sweep.py` |
| 策略對比 | `python scripts/compare_strategy_versions.py` |

### 調整參數

| 參數 | 示例 |
|------|------|
| Gap 門檻 | `--gap 1.5` (降低 → 更多交易) |
| 風險 | `--risk-per-trade 50` (減少風險) |
| 天數 | `--days 90` (縮短時間) |

---

## 💡 Windows 特定技巧

### 在 CMD 中打開資料夾

```bash
explorer backtest\csv_data
```

### 複製整個結果到記事本

```bash
type backtest_results_csv.json | clip
```
然後在記事本中 `Ctrl+V`

### 在 Python 中直接運行單行代碼

```bash
python -c "import yfinance as yf; df = yf.download('NVDA', start='2024-01-01', end='2024-08-31'); print(f'下載了 {len(df)} 行數據')"
```

### 後台運行（不想看輸出）

```bash
python download_real_data.py > nul
```

---

## 🐛 常見問題排查

### 問題 1：找不到 `download_real_data.py`

**解決**：確保在項目根目錄
```bash
cd C:\Users\illkh\my-code-project
dir download_real_data.py
```

### 問題 2：CSV 文件找不到

**解決**：檢查下載是否成功
```bash
dir backtest\csv_data
```

應該看到 `NVDA.csv`, `AMD.csv` 等

### 問題 3：回測生成 0 筆交易

**原因**：
- Gap 門檻太高（試試 `--gap 1.0`）
- CSV 數據格式不對

**解決**：
```bash
python scripts/run_backtest_with_real_or_mock.py --mode csv --csv backtest/csv_data/NVDA.csv --gap 1.0
```

### 問題 4：網絡超時

**原因**：yfinance 服務器響應慢

**解決**：稍後重試
```bash
python download_real_data.py
```

---

## 📈 最佳實踐

### 第 1 週：數據驗證

1. ✅ 下載 6 個月數據
2. ✅ 用 Mock vs CSV 對比
3. ✅ 評估真實表現

### 第 2 週：參數調整

1. ✅ 根據真實結果調整 gap 和風險
2. ✅ 測試最優參數組合
3. ✅ 記錄最好的設置

### 第 3 週：驗證和優化

1. ✅ 用更長時間段驗證
2. ✅ 評估策略強度
3. ✅ 決定是否進入紙上交易

---

## 🎯 推薦流程

```
下載真實數據
   ↓
  python download_real_data.py
   ↓
對比 Mock vs 真實
   ↓
  python scripts/run_backtest_with_real_or_mock.py --mode mock --days 120
  python scripts/run_backtest_with_real_or_mock.py --mode csv --csv backtest/csv_data/NVDA.csv
   ↓
分析結果
   ↓
  type backtest_results_csv.json (查看 CSV 結果)
  type backtest_results_mock_improved.json (查看 Mock 結果)
   ↓
決定下一步
   ✅ 如果勝率 > 35% → 進行紙上交易驗證
   ❌ 如果勝率 < 25% → 調整參數或考慮其他策略
```

---

## 📞 快速參考

**最常用的命令**：

```bash
# 下載數據（第一次）
python download_real_data.py

# Mock 回測（快速）
python scripts/run_backtest_with_real_or_mock.py --mode mock --days 120

# CSV 回測（真實）
python scripts/run_backtest_with_real_or_mock.py --mode csv --csv backtest/csv_data/NVDA.csv

# 對比所有參數
python scripts/parameter_sweep.py

# 對比策略版本
python scripts/compare_strategy_versions.py
```

---

## ✅ 檢查清單

- [ ] Python 3.9+ 已安裝
- [ ] yfinance 已安裝 (`pip install yfinance pandas`)
- [ ] 在項目根目錄 (`C:\Users\illkh\my-code-project>`)
- [ ] `download_real_data.py` 存在
- [ ] `backtest\csv_data` 目錄存在
- [ ] 成功下載至少 1 個股票 CSV
- [ ] 可以運行回測命令
- [ ] 獲得結果 JSON 文件

**下一步**：`python download_real_data.py` 🚀
