# ⚡ 快速開始指南

## 🚀 3分鐘設置

### Step 1: 克隆項目
```bash
git clone https://github.com/ngwingho1021/my-code-project.git
cd my-code-project
git checkout claude/premarket-gap-momentum-trading-9osw06
```

### Step 2: 安裝依賴
```bash
pip install -r requirements.txt
```

### Step 3: 配置API密鑰

複製 `.env.example` 為 `.env`：
```bash
copy .env.example .env  # Windows
# 或
cp .env.example .env    # Mac/Linux
```

編輯 `.env` 文件並填入你的API密鑰：

```
# Alpaca API（去 https://alpaca.markets 獲取）
ALPACA_API_KEY=PK_xxxxxxxxxxxxx
ALPACA_SECRET_KEY=xxxxxxxxxxxxxxxxxxxxx
ALPACA_BASE_URL=https://paper-api.alpaca.markets

# IBKR（保持預設值，除非你有特殊需求）
IB_HOST=127.0.0.1
IB_PORT=7497
IB_CLIENT_ID=17
```

### Step 4: 測試連接

```bash
python test_alpaca_integration.py
```

應該看到：
```
✅ 通過 - 連接測試
✅ 通過 - 數據獲取
✅ 通過 - Gap檢測
✅ 通過 - 支撐位/阻力位

🎉 所有測試通過! Alpaca整合就緒
```

### Step 5: 運行盤前掃描

```bash
python demo_premarket_scan.py
```

### Step 6: 啟動交易系統

```bash
python main.py
```

---

## 📋 .env 文件重要提醒

- **不要提交到git** - 永遠不要上傳你的 API 密鑰！
- **密鑰安全** - 定期輪換你的 API 密鑰
- **紙交易模式** - 初期使用 `ALPACA_BASE_URL=https://paper-api.alpaca.markets`

---

## 🔧 常見問題

### 問題1: "API密鑰未設定"

**檢查清單:**
1. `.env` 文件是否存在？
2. API 密鑰是否正確複製（無多餘空格）？
3. 運行診斷工具：
   ```bash
   python diagnose_env.py
   ```

### 問題2: "401 認證失敗"

**解決:**
- 確認 API 密鑰在 Alpaca Dashboard 中仍然有效
- 嘗試重新生成新的 API 密鑰
- 確認 `ALPACA_BASE_URL=https://paper-api.alpaca.markets` (紙交易URL)

### 問題3: "無法連接到 Alpaca"

**檢查:**
- 網絡連接是否正常？
- 是否有防火牆阻止？
- Alpaca 服務是否在線？

---

## 📚 更多資源

- `ALPACA_SETUP.md` - 詳細的集成指南
- `IMPLEMENTATION_PROGRESS.md` - 項目進度
- `README.md` - 完整的項目說明

---

## ✅ 準備好了嗎？

按照上面的步驟：

1. ✓ 克隆項目
2. ✓ 安裝依賴
3. ✓ 配置 .env
4. ✓ 測試連接
5. ✓ 運行掃描
6. ✓ 啟動系統

**祝交易順利！** 🚀
