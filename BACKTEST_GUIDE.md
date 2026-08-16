# 📊 回測系統完全指南

## 系統架構

```
┌─────────────────────────────────────────┐
│      backtest_runner.py (CLI 入口)      │
└──────────────┬──────────────────────────┘
               │
       ┌───────┴────────────────┐
       ▼                        ▼
  ┌─────────────┐    ┌──────────────────┐
  │ Backtester  │    │ GapMomentumStrategy
  │             │    │                  │
  │ - 加載數據  │    │ - MACD信號       │
  │ - 執行信號  │    │ - VWAP確認       │
  │ - 模擬交易  │    │ - 拉回檢測       │
  └──────┬──────┘    │ - 成交量確認     │
         │           └──────────────────┘
         │
    ┌────┴──────────┐
    ▼               ▼
┌─────────────┐ ┌──────────────┐
│ Portfolio   │ │ AlpacaClient │
│             │ │              │
│ - 持倉管理  │ │ - 獲取數據   │
│ - 交易記錄  │ │ - 計算指標   │
│ - 統計計算  │ └──────────────┘
└──────┬──────┘
       │
       ▼
┌──────────────────┐
│ BacktestAnalyzer │
│                  │
│ - 生成HTML報告   │
│ - 生成JSON數據   │
│ - 風險指標計算   │
└──────────────────┘
```

## 快速開始

### 1️⃣ 基本回測

```bash
# 回測單個股票
python backtest_runner.py --symbol AAPL --start 2024-01-01 --end 2024-03-31

# 使用自定義參數
python backtest_runner.py --symbol TSLA --start 2024-01-01 --end 2024-12-31 \
  --timeframe 5Min --capital 50000 --slippage 1.0
```

### 2️⃣ 命令行選項

| 選項 | 說明 | 例子 |
|------|------|------|
| `--symbol` | 股票代碼 (必須) | `AAPL` |
| `--start` | 開始日期 (YYYY-MM-DD) | `2024-01-01` |
| `--end` | 結束日期 (YYYY-MM-DD) | `2024-12-31` |
| `--timeframe` | 時間框架 (預設: 1Min) | `5Min`, `15Min` |
| `--capital` | 初始資本 (預設: 25000) | `50000` |
| `--slippage` | 滑點 % (預設: 0.5) | `1.0` |
| `--output` | 報告目錄 | `my_reports` |

### 3️⃣ 輸出示例

```
================================================================================
🚀 盤前Gap動量交易系統 - 回測模式
================================================================================
股票代碼: AAPL
回測期間: 2024-01-01 至 2024-03-31
時間框架: 1Min
初始資本: $25,000.00
滑點設定: 0.5%
================================================================================

✅ AAPL: 63,345 根K線 (2024-01-02 to 2024-03-29)

📈 買入 100 股 @ 192.35 (2024-01-05 09:35:00)
  ✅ TP1 (50%) 止盈 @ 193.67
  ✅ TP2 (30%) 止盈 @ 195.31
  🛑 止損觸發 @ 189.25

...

📊 生成報告...

📈 總體績效
  初始資本:        $25,000.00
  最終淨值:        $28,450.25
  淨收益:           $3,450.25
  回報率:              13.80%
  最大回撤:             -8.50%

📊 交易統計
  總交易數:                42
  勝利交易:                31
  失敗交易:                11
  勝率:                 73.8%
  平均盈利:        $1,240.50
  平均虧損:         -$320.30
  單筆平均損益:      $82.15
  最大單筆盈利:   $1,850.00
  最大單筆虧損:     -$485.50
  平均持倉時間:         18 分鐘

✅ 回測完成!
================================================================================
📄 HTML報告: backtest_reports/backtest_AAPL_20240815_123045.html
📄 JSON數據: backtest_reports/backtest_AAPL_20240815_123045.json
```

## 核心模塊

### `Backtester` (backtest/backtester.py)

主回測引擎，負責：

```python
from backtest.backtester import Backtester
from strategy.gap_momentum_strategy import GapMomentumStrategy

# 創建回測器
backtester = Backtester(initial_capital=25000, slippage_pct=0.5)

# 運行回測
result = backtester.run(
    symbol='AAPL',
    start_date='2024-01-01',
    end_date='2024-03-31',
    signal_func=signal_function  # 自定義策略函數
)
```

**核心方法**：

| 方法 | 說明 |
|------|------|
| `load_bars()` | 異步加載歷史K線數據 |
| `run()` | 執行完整回測流程 |
| `apply_slippage()` | 模擬成交滑點 |

### `VirtualPortfolio` (backtest/portfolio.py)

虛擬投資組合，跟蹤：

```python
from backtest.portfolio import VirtualPortfolio

portfolio = VirtualPortfolio(initial_capital=25000)

# 進場
portfolio.enter_position(
    symbol='AAPL',
    shares=100,
    price=192.35,
    timestamp=datetime.now(),
    tp1=193.67, tp2=195.31, tp3=197.00,
    sl=189.25
)

# 更新市價
portfolio.update_position_price('AAPL', 195.50, datetime.now())

# 平倉
portfolio.exit_position('AAPL', 195.50, 50, datetime.now(), 'tp1')

# 獲取統計
stats = portfolio.get_trade_stats()
print(f"勝率: {stats['win_rate']:.1f}%")
print(f"單筆平均損益: ${stats['avg_trade_pnl']:.2f}")
```

### `GapMomentumStrategy` (strategy/gap_momentum_strategy.py)

交易策略實現，包括：

```python
from strategy.gap_momentum_strategy import GapMomentumStrategy

strategy = GapMomentumStrategy()

# 生成信號
signal = strategy.generate_signal(df, current_idx)

# 信號結構
# {
#     'action': 'buy',
#     'entry_price': 192.35,
#     'tp1': 193.67,
#     'tp2': 195.31,
#     'tp3': 197.00,
#     'stop_loss': 189.25,
#     'confidence': 85.5,
# }
```

**策略檢查項**：

1. **MACD動能** (confidence: 40)
   - 檢查MACD金叉 (線穿信號線)
   - 檢查MACD柱狀圖增長

2. **VWAP確認** (confidence: 30)
   - 價格在VWAP上方
   - 緩衝百分比: 0%

3. **拉回結構** (confidence: 30)
   - 最近5根K線範圍
   - 拉回幅度 <= 50%

4. **成交量確認** (confidence: 20-50)
   - 成交量與過去20根平均比
   - 要求: >= 2.0x

### `BacktestAnalyzer` (backtest/analyzer.py)

生成可視化報告：

```python
from backtest.analyzer import BacktestAnalyzer

analyzer = BacktestAnalyzer(report_dir='backtest_reports')

# 生成HTML報告（帶圖表）
html_path = analyzer.generate_html_report(result, 'AAPL', '2024-01-01', '2024-03-31')

# 生成JSON數據
json_path = analyzer.generate_json_report(result, 'AAPL')
```

## 自定義策略

### 創建新策略

```python
import pandas as pd
from typing import Dict, Any, Optional

class MyCustomStrategy:
    def generate_signal(self, df: pd.DataFrame, current_idx: int) -> Optional[Dict[str, Any]]:
        """
        自定義信號生成邏輯
        
        Args:
            df: OHLCV DataFrame (columns: o, h, l, c, v)
            current_idx: 當前K線索引
            
        Returns:
            信號字典或 None
        """
        
        if current_idx < 50:  # 需要足夠數據
            return None
        
        current_price = df.iloc[current_idx]['c']
        
        # 你的自定義邏輯...
        
        return {
            'action': 'buy',  # 'buy', 'sell', 'exit', 'hold'
            'entry_price': current_price,
            'tp1': current_price * 1.02,
            'tp2': current_price * 1.03,
            'tp3': current_price * 1.05,
            'stop_loss': current_price * 0.98,
        }


# 使用自定義策略
from backtest.backtester import Backtester

strategy = MyCustomStrategy()
backtester = Backtester()

def signal_func(df, idx):
    return strategy.generate_signal(df, idx)

result = backtester.run('AAPL', '2024-01-01', '2024-03-31', signal_func)
```

## 高級用法

### 多股票批量回測

```python
import asyncio
from backtest.backtester import Backtester
from strategy.gap_momentum_strategy import GapMomentumStrategy, create_backtest_signal_function

async def backtest_multiple():
    symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA']
    results = {}
    
    strategy = GapMomentumStrategy()
    signal_func = create_backtest_signal_function(strategy)
    backtester = Backtester()
    
    for symbol in symbols:
        result = backtester.run(
            symbol=symbol,
            start_date='2024-01-01',
            end_date='2024-12-31',
            signal_func=signal_func
        )
        results[symbol] = result
    
    # 比較結果
    for symbol, result in results.items():
        summary = result.get('summary', {})
        print(f"{symbol}: {summary.get('total_return_pct', 0):.2f}%")

asyncio.run(backtest_multiple())
```

### 參數優化

```python
from backtest.backtester import Backtester
from config.settings import STRATEGY as STRATEGY_PARAMS

# 嘗試不同的MACD參數
best_result = None
best_return = -float('inf')

for fast in [10, 12, 14]:
    for slow in [24, 26, 28]:
        # 修改參數
        STRATEGY_PARAMS.macd_fast = fast
        STRATEGY_PARAMS.macd_slow = slow
        
        # 運行回測
        backtester = Backtester()
        result = backtester.run('AAPL', '2024-01-01', '2024-12-31', signal_func)
        
        total_return = result['summary'].get('total_return_pct', 0)
        if total_return > best_return:
            best_return = total_return
            best_result = (fast, slow, result)

print(f"最佳MACD參數: fast={best_result[0]}, slow={best_result[1]}")
print(f"回報率: {best_return:.2f}%")
```

## 關鍵指標說明

### 收益指標

| 指標 | 說明 | 計算公式 |
|------|------|---------|
| **淨收益** | 最終淨值 - 初始資本 | `final_equity - initial_capital` |
| **回報率** | 收益除以初始資本 | `(final_equity - initial_capital) / initial_capital * 100` |
| **最大回撤** | 最大虧損百分比 | `(peak_equity - trough_equity) / peak_equity * 100` |

### 交易指標

| 指標 | 說明 | 含義 |
|------|------|------|
| **勝率** | 盈利交易 / 總交易 | > 50% 視為正向 |
| **平均損益** | 所有交易平均損益 | 正值表示平均盈利 |
| **風險回報比** | 最大盈利 / 最大虧損 | > 1.0 視為有利 |
| **持倉時間** | 交易平均持有時間 | 短期交易: 分鐘級 |

### 風險指標

| 指標 | 說明 | 理想值 |
|------|------|-------|
| **夏普比率** | 收益 / 波動率 | > 1.0 |
| **最大回撤** | 最大虧損百分比 | < 20% |
| **勝率** | 盈利交易比例 | > 50% |

## 故障排除

### ❌ "無數據加載"

**原因**: Alpaca API未返回數據

```bash
# 檢查API配置
python diagnose_env.py

# 確保日期範圍有效
# 美股交易日: 週一至週五 (節假日除外)
```

### ❌ 信號生成失敗

**原因**: 資料不足或指標計算錯誤

```python
# 檢查數據長度
if current_idx < 50:
    return None  # 需要至少50根K線
```

### ❌ 回測速度慢

**優化建議**:
1. 使用更大的時間框架 (5Min 而非 1Min)
2. 減少回測期間
3. 簡化策略邏輯

## 最佳實踐

### ✅ 回測前檢查清單

- [ ] 確認API密鑰有效
- [ ] 確認股票代碼正確
- [ ] 確認日期範圍有效 (交易日)
- [ ] 確認有足夠初始資本
- [ ] 檢查滑點設定是否合理

### ✅ 策略開發建議

1. **從簡單開始** - 先實現基本邏輯，逐步複雜化
2. **多股票驗證** - 回測結果應在多個股票上驗證
3. **長期驗證** - 至少回測 6 個月 ~ 1 年
4. **實盤前紙交易** - 先用紙交易驗證實時信號

## 相關文件

- `backtest_runner.py` - CLI 工具
- `backtest/backtester.py` - 核心引擎
- `backtest/portfolio.py` - 虛擬組合
- `backtest/analyzer.py` - 結果分析
- `strategy/gap_momentum_strategy.py` - 交易策略

---

**更新時間**: 2024年8月
**版本**: 2.0 (Phase 2 完成)
