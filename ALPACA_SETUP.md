# Alpaca + IBKR 混合交易系統設置指南

## 架構概述

```
┌─────────────────────────────────────────────────────────────┐
│                 盤前動量交易系統                             │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  Alpaca API                           IBKR API              │
│  ├─ 免費盤前數據 ──────────┐         ├─ 實際交易執行       │
│  ├─ 實時成交量           │    獲得  │─ 期權交易           │
│  ├─ K線數據獲取           │   信號   │─ 融資槓桿          │
│  └─ WebSocket推送        │ ──────→ └─ 高級訂單類型       │
│                           │                                  │
│  DataFetcher (統一層)   │                                  │
│  ├─ Gap檢測 (>= 5%)   ──┤                                  │
│  ├─ 成交量分析          │   觸發   OrderManager (IBKR執行) │
│  ├─ 技術面分析          │ ──────→ ├─ 下單執行             │
│  └─ 支撐位/阻力位        │         ├─ 止損管理             │
│                           │         └─ 分批止盈             │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

## 快速開始

### 第1步: 安裝依賴

```bash
# 複製requirements.txt中的新依賴
pip install -r requirements.txt

# 或只安裝Alpaca相關的
pip install aiohttp>=3.9.0 alpaca-trade-api>=2.0.0
```

### 第2步: 獲取API密鑰

#### Alpaca API
1. 註冊 https://alpaca.markets （免費）
2. 登入Dashboard
3. 進入 Account → API Keys
4. 複製 API Key 和 Secret Key
5. 切換到 Paper Trading 賬戶（測試用）

#### IBKR（已有）
- 確保 TWS / IB Gateway 正在運行
- 確認端口設置: 7497 (Paper) 或 7496 (Live)

### 第3步: 配置環境變數

```bash
# 複製模板
cp .env.example .env

# 編輯 .env，填入你的密鑰
nano .env
```

你的 `.env` 應該看起來這樣：
```
ALPACA_API_KEY=PK1234567890abcdefgh
ALPACA_SECRET_KEY=secret1234567890abcdefgh
ALPACA_BASE_URL=https://paper-api.alpaca.markets

IB_HOST=127.0.0.1
IB_PORT=7497
IB_CLIENT_ID=17
```

### 第4步: 測試連接

```bash
# 運行Alpaca整合測試
python test_alpaca_integration.py
```

預期輸出：
```
✅ 連接測試 - 通過
✅ 數據獲取 - 通過
✅ Gap檢測 - 通過
✅ 支撐位/阻力位 - 通過

🎉 所有測試通過! Alpaca整合就緒
```

## 核心模塊說明

### 1. `core/alpaca_client.py`
Alpaca API客戶端，提供：
- **非同步API調用**（高效且不阻塞）
- **K線數據獲取**（1分鐘、5分鐘、15分鐘、日線等）
- **實時報價**（bid/ask）
- **賬戶信息**

使用示例：
```python
async with AlpacaClient() as client:
    # 獲取最新K線
    bars = await client.get_latest_bars(["AAPL", "TSLA"])
    
    # 獲取歷史數據
    bars = await client.get_bars(
        "AAPL",
        timeframe="1Min",
        limit=100
    )
    
    # 獲取賬戶信息
    account = await client.get_account()
```

### 2. `core/data_fetcher.py`
統一數據層，提供：
- **Gap檢測** - 識別 >= 5% gap的股票
- **成交量分析** - 計算相對成交量（相對20日平均）
- **支撐位/阻力位** - 技術面分析
- **市場狀態檢查** - 判斷盤前/盤中/盤後

使用示例：
```python
async with DataFetcher() as fetcher:
    # 掃描gap-up
    gapups = await fetcher.scan_gapups(["AAPL", "TSLA", ...])
    for gap in gapups:
        print(f"{gap.symbol}: {gap.gap_pct:+.2f}% gap, {gap.rel_volume:.2f}x volume")
    
    # 識別技術位
    support, resistance = await fetcher.identify_support_resistance("AAPL")
```

### 3. 與現有系統的集成

現有模塊保持不變：
- `strategy/ross_cameron.py` - 進場/離場邏輯（不變）
- `core/indicators.py` - 技術指標（不變）
- `core/order_manager.py` - 訂單執行（使用IBKR，不變）

新增模塊供其使用：
- `core/alpaca_client.py` ← 替代IBKR的數據層
- `core/data_fetcher.py` ← 統一數據接口

## 使用流程

### 盤前交易流程

1. **4:00 AM EST** - 系統啟動，開始掃描
   ```bash
   python main.py --mode premarket
   ```

2. **掃描器** 使用 `DataFetcher.scan_gapups()`
   - 從Alpaca獲取盤前數據
   - 檢測 gap >= 5%
   - 驗證成交量
   - 過濾價格範圍

3. **信號生成** 使用 `RossCameronStrategy`
   - MACD確認
   - VWAP確認
   - Pullback確認
   - Level 2 (IBKR) 買盤確認

4. **訂單執行** 使用 `OrderManager` (IBKR)
   - 提交限價買單
   - 設置止損單 (IBKR)
   - 設置分層止盈單 (IBKR)

5. **監控** 持續關注
   - 實時成交量 (Alpaca)
   - 技術面變化 (Alpaca)
   - 訂單狀態 (IBKR)
   - 風險指標 (RiskManager)

### 回測流程（下一個Phase）

```bash
# 未來實現
python -m backtest.backtester \
  --symbol AAPL \
  --start 2024-01-01 \
  --end 2024-12-31 \
  --strategy ross_cameron
```

### 紙交易流程（驗證Phase）

```bash
# 使用紙交易賬戶（已設置）
python main.py --mode paper --duration 7  # 運行7天紙交易
```

## 常見問題

### Q: 為什麼混合使用Alpaca和IBKR？

**A:** 最優成本效益：
- **Alpaca**: 免費盤前數據 + 無限API調用 → 數據層
- **IBKR**: 期權交易 + 融資槓桿 + 複雜訂單 → 執行層
- **結果**: 零成本實時數據 + 專業交易功能

### Q: Alpaca紙交易和IBKR紙交易如何同步？

**A:** 目前分開運行：
- 數據層用Alpaca數據（免費）
- 訂單執行在IBKR紙交易（完整測試）
- 未來可實現Alpaca訂單執行以完全同步

### Q: 如果Alpaca API掉線會怎樣？

**A:** 安全機制：
- 自動重試（最多3次，指數退避）
- 優雅降級到IBKR數據
- 如果無數據，停止交易信號
- 不會執行沒有確認的訂單

### Q: 可以使用實盤嗎？

**A:** 可以，但需謹慎：
1. 在紙交易上驗證至少2-4週
2. 監控勝率和回報率
3. 從1手股票開始
4. 修改 `PAPER_TRADING = False` 和 `IB_PORT = 7496`
5. 確保風控設置合理

### Q: 如何進行回測？

**A:** Phase 2實現（當前開發中）
- 加載Alpaca歷史數據
- 模擬交易執行
- 生成績效報告
- 支持參數優化

## 故障排查

### 問題: "API Key not found"

```
❌ 未設定Alpaca API密鑰
```

**解決**:
```bash
cp .env.example .env
# 編輯 .env 填入真實密鑰
nano .env
```

### 問題: "Unable to connect to Alpaca"

**檢查清單**:
1. 網絡連接是否正常？
2. API密鑰是否正確？
3. 賬戶是否激活？
4. IP是否被限制？

### 問題: "IBKR Connection Failed"

**檢查清單**:
1. TWS/IB Gateway是否運行？
2. 端口是否正確 (7497/7496)?
3. 防火牆是否允許127.0.0.1?

## 下一步

### Phase 2: 回測引擎
- [ ] 創建 `backtest/` 模塊
- [ ] 實現歷史數據回測
- [ ] 生成績效報告
- [ ] 支持參數優化

### Phase 3: Web Dashboard
- [ ] FastAPI後端
- [ ] Vue前端儀表板
- [ ] WebSocket實時推送
- [ ] 交易歷史查詢

### Phase 4: 高級功能
- [ ] 期權策略支持
- [ ] 融資槓桿管理
- [ ] 多符號並行交易
- [ ] ML信號增強

## 支持

遇到問題？
1. 查看日志: `logs/` 目錄
2. 檢查 `.env` 配置
3. 運行 `test_alpaca_integration.py`
4. 檢查GitHub Issues

---

**最後提醒**: 始終在紙交易模式下充分驗證策略，不要匆忙進入實盤。
