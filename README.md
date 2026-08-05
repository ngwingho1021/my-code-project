# AI Auto Trade — IBKR / Ross Cameron 動能策略（Paper Trading）

用 Python + IBKR API（`ib_async`）自動執行 Ross Cameron 風格嘅小型股動能突破策略。
**目前只設計喺 Paper Trading 運作，唔好改做真實盤，除非你已經完全理解同測試過成個系統。**

## 策略邏輯概覽

1. **5 核心篩選**（`core/scanner.py`）
   - 股價 $2–20
   - 流通股本 (float) < 20,000,000 股
   - Gap up ≥ 5%
   - 相對成交量 (RVOL) ≥ 2 倍
   - 有新聞催化劑（`core/news.py`，用 IBKR 新聞 feed 關鍵字判斷；預設冇催化劑都容許進場，但信心較低 — 可喺 `config/settings.py` 嘅 `SCANNER.require_catalyst` 改做必要條件）

2. **進場確認**（`strategy/ross_cameron.py` + `core/indicators.py`）
   - 1 分鐘圖 MACD 向上（macd 遞增、企穩喺 signal 線之上、histogram 遞增）
   - 股價企穩喺 VWAP 之上
   - 出現健康嘅 micro pullback（縮量窄幅拉回，冇跌穿升浪 50%）
   - 10 秒圖確認短線動能未衰減
   - Level 2 order book imbalance + Time & Sales 買賣速度確認買盤主導（`core/level2.py`）
   - 盈虧比要 ≥ 1:2（理想 1:3）先落單

3. **離場邏輯**
   - 分批止盈：第 1R 食 50%、第 2R 再食 30%，尾段 20% 用 trailing stop
   - Topping tail（上影線佔比過大）+ 動能衰減 = 優先離場
   - Level 2/Tape 轉弱（買盤流動性衰減 + 賣壓轉強 + tape 沽盤主導）= 離場
   - 止蝕用 **STP LMT**（stop-limit）而唔係純市價止蝕，防止急跌時滑價成交（`core/order_manager.py`）

4. **熔斷 (Halt) / 復牌 (Resume) 處理**（`core/order_manager.monitor_and_manage_halts`）
   - 偵測到熔斷即刻取消現有掛單，暫停對該股嘅任何操作
   - 復牌後唔會即刻掛單，先確認連續幾個 tick 報價穩定、波幅喺安全範圍內
   - 波幅過大 = 直接市價止蝕離場；波幅正常 = 用新價位重新計止蝕並重新掛單
   - 等待復牌超過 `EXEC_SAFETY.resume_max_wait_sec`（預設 10 分鐘）就自動放棄，唔會盲等

5. **風控**（`core/risk_manager.py`）— 全部可以喺 `config/settings.py` 調整
   - 帳戶規模 $5,000
   - 每日最多 12 次交易
   - 最多同時持有 3 隻股票
   - 單注最大虧損 $100
   - 每日最大虧損 $300（觸及後自動停止當日交易）
   - 每週最大虧損 $800（觸及後自動停止當週交易）

## 安裝

```bash
pip install -r requirements.txt
```

## 使用步驟

1. 開啟 **TWS** 或 **IB Gateway**，登入 **Paper Trading** 帳戶
2. TWS: `File -> Global Configuration -> API -> Settings`
   - 打勾 `Enable ActiveX and Socket Clients`
   - Socket port: `7497`（TWS Paper）或 `4002`（IB Gateway Paper）
   - 建議打勾 `Read-Only API` 先測試，確認邏輯正確後先解除
3. 確認你嘅帳戶有訂閱：
   - Level 2 / Market Depth 數據（例如 NASDAQ TotalView 或 NYSE ArcaBook）
   - IBKR 新聞（TWS -> Global Configuration -> News，一般 Broad Tape 免費）
4. 檢查 `config/settings.py` 入面嘅所有參數（風控數值、策略參數）
5. 執行：

```bash
python main.py
```

## 檔案結構

```
config/settings.py       全部可調參數（風控、策略、掃描條件、執行安全）
core/ibkr_client.py      IBKR 連線管理
core/scanner.py          5 核心條件掃描器
core/news.py             新聞催化劑判斷
core/indicators.py       VWAP / MACD / pullback / topping tail 指標
core/level2.py           Level 2 order book + Time & Sales 分析
core/risk_manager.py     交易次數/持倉數/虧損上限風控
core/order_manager.py    落單、分批止盈、防滑價止蝕、熔斷復牌處理
strategy/ross_cameron.py 進場/離場訊號整合邏輯
main.py                  主程式 loop
```

## 重要提醒

- **呢個系統未經過任何實盤驗證**，Paper Trading 階段請密切監察日誌（`logs/` 目錄），
  對比每一單嘅進出場理由同你自己嘅判斷是否一致。
- IBKR 嘅新聞/float 數據透過 API 攞未必完整或即時，`core/scanner.py` 入面嘅
  `_get_float_shares` 用 fundamental data 解析，唔係所有股票都有呢個資料，
  遇到攞唔到會當「未知」處理但唔會因此被過濾（可自行調整為更嚴謹）。
- 止蝕用 stop-limit 有機會喺極端流動性蒸發情況下不成交，`monitor_and_manage_halts`
  同 Level2 轉弱訊號係額外多一重保護，但唔可以完全消除滑價風險。
- 正式轉真實盤之前，建議至少連續數星期 paper trading 結果穩定，並人手覆核策略邏輯。
