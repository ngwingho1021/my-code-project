# TradingView Integration Guide

## Overview

The Small-Cap Momentum Trader bot now integrates with TradingView for real-time gap-up detection via webhook. This guide walks you through the complete setup process.

---

## Prerequisites

✅ **TradingView Premium Subscription** - Required for webhook alerts
✅ **Small-Cap Momentum Bot Running** - With webhook receiver active
✅ **Internet Connection** - For TradingView → Bot communication

---

## Step 1: Copy the Pine Script Strategy

### Option A: Copy-Paste Method

1. Go to TradingView Chart (any stock, e.g., SPY for testing)
2. Click **Pine Editor** (bottom left)
3. Click **New Script** → Select **Strategy**
4. Copy the entire content from `/tradingview/small_cap_momentum_bot_strategy.pine`
5. Paste into the Pine Editor
6. Click **Save** and give it a name: `Small-Cap Momentum Bot - 5 Pillars`
7. Click **Add to Chart**

### Option B: Direct Link (if available)
If the script is published to TradingView Community, you can search for it directly in the Strategy Library.

---

## Step 2: Configure Strategy Parameters

After adding the strategy to your chart, configure these parameters:

| Parameter | Default | Range | Purpose |
|-----------|---------|-------|---------|
| **Min Gap %** | 5.0 | 0-50 | Minimum gap-up percentage (Pillar 1) |
| **Min RVOL** | 2.0 | 1-10 | Minimum relative volume (Pillar 2) |
| **RVOL Lookback Days** | 20 | 5-100 | Period for RVOL calculation |
| **Float < 20M** | ✓ | Checkbox | Low float requirement (Pillar 3) |
| **Min Price** | 2.0 | 0.1-100 | Minimum stock price (Pillar 4) |
| **Max Price** | 20.0 | 1-1000 | Maximum stock price (Pillar 4) |
| **Min Volume** | 100,000 | 10K-∞ | Minimum daily volume (Pillar 5) |

### Recommended Settings for Small-Cap Momentum
```
Min Gap %:           5.0 (or 3.0 for more signals, 7.0 for stricter)
Min RVOL:            2.0 (or 3.0 for high conviction)
RVOL Lookback Days:  20
Float < 20M:         CHECKED
Min Price:           2.0
Max Price:           20.0
Min Volume:          100,000
```

---

## Step 3: Create the Webhook Alert

### Step 3a: Set Alert Conditions

1. **On your chart** where the strategy is running, right-click the strategy name
2. Select **Create Alert** (or go to Alerts → Create Alert)
3. Choose:
   - **Alert Condition**: `Small-Cap Momentum Bot - 5 Pillars` → **Entry Signal**
   - **Frequency**: `Once per bar close` (to avoid duplicate signals)

### Step 3b: Configure Webhook URL

1. In the alert dialog, look for **Notifications** or **Webhook** section
2. **Enable Webhook URL**
3. Enter the webhook endpoint:

#### For Local Testing (Your Computer)
```
http://127.0.0.1:5000/webhook/tradingview
```

#### For Remote Server (Cloud, VPS, or Always-On Machine)
If your trading bot runs on a remote machine or you want alerts while your computer is off:

1. **Option A - Use ngrok** (Quick tunnel for testing)
   ```bash
   ngrok http 5000
   # Output: Forwarding https://abc123.ngrok.io → http://127.0.0.1:5000
   ```
   Use: `https://abc123.ngrok.io/webhook/tradingview`

2. **Option B - Set up port forwarding** (Production)
   - Configure your router/firewall to forward port 5000
   - Use your external IP or domain: `http://YOUR_IP:5000/webhook/tradingview`

3. **Option C - Use cloud deployment** (Docker, AWS Lambda, Heroku)
   - Deploy the bot to a cloud service
   - Use the cloud service's webhook URL

### Step 3c: Webhook URL Examples

| Setup | URL |
|-------|-----|
| Local Computer (Same Network) | `http://127.0.0.1:5000/webhook/tradingview` |
| Local Computer (from same router) | `http://192.168.1.100:5000/webhook/tradingview` |
| ngrok Tunnel | `https://abc123.ngrok.io/webhook/tradingview` |
| Cloud Server | `http://your-domain.com:5000/webhook/tradingview` |

---

## Step 4: Test the Webhook Connection

### Test 1: Health Check Endpoint

Before sending real alerts, verify the bot is reachable:

```bash
curl http://127.0.0.1:5000/webhook/health
```

Expected response:
```json
{
  "status": "ok",
  "timestamp": "2026-08-18T12:00:00.123456",
  "service": "Small-Cap Momentum Bot Webhook Receiver"
}
```

### Test 2: Status Endpoint

Check if the bot is online and trading:

```bash
curl http://127.0.0.1:5000/webhook/status
```

Expected response:
```json
{
  "status": "online",
  "time_status": "Pre-Market (04:00-09:30)",
  "positions": 0,
  "timestamp": "2026-08-18T12:00:00.123456"
}
```

### Test 3: Manual Webhook Test

Send a test signal to verify the webhook parsing works:

```bash
curl -X POST http://127.0.0.1:5000/webhook/tradingview \
  -H "Content-Type: application/json" \
  -d '{"message": "UPST|ENTRY|15.50|GAP=6.23%|RVOL=3.45x|VOL=2500000"}'
```

Expected response:
```json
{"status": "success", "message": "Signal processed"}
```

Bot log should show:
```
📩 收到 TradingView 信號: {'message': 'UPST|ENTRY|15.50|GAP=6.23%|RVOL=3.45x|VOL=2500000'}
✅ 解析成功: {'symbol': 'UPST', 'signal_type': 'ENTRY', 'entry_price': 15.5, 'gap_pct': 6.23, 'rvol': 3.45, 'volume': 2500000, 'timestamp': '2026-08-18T12:00:00.123456'}
🎯 執行進場: UPST @ $15.50
```

---

## Step 5: Real Trading Setup

### Before Going Live

✅ **Verify bot is running**
```bash
ps aux | grep small_cap_momentum_bot_main.py
```

✅ **Check logs in real-time**
```bash
tail -f logs/small_cap_momentum_bot_main.log
```

✅ **Confirm TradingView strategy is running on your charts**
- Strategy should show green "Entry Signal" labels when all 5 pillars are met
- Check the strategy's information panel for Gap, RVOL, Volume values

✅ **Test with one low-float stock**
- Load a chart for a known gap-up candidate (e.g., UPST)
- Manually adjust parameters until you see the entry signal
- Create a test alert to verify webhook fires

✅ **Monitor your account in IBKR**
- Paper trading account should be used initially
- Watch for new positions appearing when alerts trigger

### Production Checklist

- [ ] TradingView strategy added to chart
- [ ] All 5 parameters configured
- [ ] Webhook alert created with correct URL
- [ ] Health check endpoint responds 200
- [ ] Status endpoint shows "online"
- [ ] Manual test alert was processed successfully
- [ ] Bot logs show "Webhook 服務器已啟動"
- [ ] Paper trading is active (PAPER_TRADING=True in config)
- [ ] First test alert received and processed
- [ ] Position opened successfully from webhook signal

---

## Troubleshooting

### Webhook Alert Not Firing

**Problem**: Strategy shows entry signals but TradingView alert doesn't fire
- [ ] Verify alert is created with `Once per bar close` frequency
- [ ] Check alert is enabled (green toggle)
- [ ] Confirm strategy added to correct timeframe (recommended: 5-min or Daily)

### Webhook Not Reaching Bot

**Problem**: Alert fires but bot doesn't receive signal

Check connectivity:
```bash
# From bot machine
curl -v http://127.0.0.1:5000/webhook/health

# From another machine (if bot is remote)
curl -v http://BOT_IP:5000/webhook/health
```

Common issues:
- ❌ Bot not running (`python small_cap_momentum_bot_main.py`)
- ❌ Flask server didn't start (check logs for errors)
- ❌ Firewall blocking port 5000 (whitelist 5000)
- ❌ Wrong IP/URL in alert (test with health endpoint first)
- ❌ TradingView webhook is sending to old/wrong URL (update alert)

### Signal Parsed But No Entry

**Problem**: Webhook received but position not opened

Check conditions:
- ⏰ **Trading hours**: Is it between 04:00-16:00 EST? (Check bot's time_status)
- 💰 **Risk limits**: Max concurrent positions (3), daily loss (-$300), weekly loss (-$800)?
- 🔗 **IBKR connection**: Is bot connected to IBKR? (Check logs for connection status)
- 📋 **Insufficient data**: Float shares unknown? No market data available?

Example log message if blocked:
```
⚠️ 進場失敗: 無法開倉 UPST (超過持倉限制)
```

### Entry Price Slippage

**Problem**: Webhook sent entry_price=15.50 but order filled at 15.70

This is normal in real trading. The bot uses the TradingView alert price as a reference, but actual execution depends on:
- Current market price when order is placed
- Order type (LIMIT uses entry_price, MARKET gets current market price)
- Bid-ask spread in small-cap stocks

To minimize:
- Use Limit orders (default behavior)
- Trigger alerts during most liquid times (09:30-15:00 EST)

---

## Advanced: Customizing Strategy Parameters per Stock

### Scenario 1: Stricter Filter (Fewer False Signals)
```
Min Gap %: 7.0
Min RVOL: 3.0
Min Price: 3.0
Max Price: 15.0
```

### Scenario 2: More Aggressive (More Signals)
```
Min Gap %: 3.0
Min RVOL: 1.5
Min Volume: 50,000
```

### Scenario 3: Low Float Focus (Most Conservative)
```
Min Gap %: 5.0
Min RVOL: 2.0
Min Price: 2.0
Max Price: 20.0
Float < 20M: ✓ CHECKED (strict)
```

Adjust these parameters on your chart and observe the strategy's entry signals. When satisfied with the filter performance, update the webhook alert.

---

## Performance Monitoring

After the bot is trading via webhook signals, monitor these metrics:

### Daily Checklist
- [ ] Check bot logs for webhook receives: `📩 收到 TradingView 信號`
- [ ] Verify position entries: `✅ 已下買單`
- [ ] Monitor P&L in IBKR account
- [ ] Confirm exit signals triggering: `止盈` / `止蝕`

### Weekly Review
- [ ] Total trades executed
- [ ] Win rate % (should be > 50%)
- [ ] Profit factor (should be > 1.5)
- [ ] Max drawdown (should be < 30%)

These stats are printed in the bot's log at end of day.

---

## FAQ

**Q: Do I need to keep my computer on all the time?**
A: Only if you're running the bot locally. For 24/7 trading, deploy the bot to a cloud server (AWS, Heroku, DigitalOcean, etc.)

**Q: Can I use the same webhook URL for multiple charts?**
A: Yes! Create one webhook server (running once), then point multiple TradingView alerts to it.

**Q: What if I want to trade other timeframes (1min, 4hr)?**
A: The Pine Script works on any timeframe. Create separate strategies for each timeframe and point each to the same webhook URL.

**Q: How do I disable the bot without stopping it?**
A: The webhook receiver will process all signals, but the bot won't enter if it's outside trading hours (04:00-16:00 EST) or risk limits are breached.

**Q: Can I test with paper trading first?**
A: Yes! PAPER_TRADING=True is set in config/settings.py by default. All signals will execute on paper account, not real.

---

## Support & Debugging

### Enable Verbose Logging
Edit `config/settings.py` and set `LOG_LEVEL = "DEBUG"` to see detailed webhook processing.

### View Bot Logs
```bash
# Watch logs in real-time
tail -f logs/small_cap_momentum_bot_main.log

# Search for webhook events
grep "webhook" logs/small_cap_momentum_bot_main.log
```

### Common Log Patterns
```
✅ = Success (entry executed, position opened)
⚠️ = Warning (signal skipped due to conditions)
❌ = Error (webhook error, connection failed)
📩 = Info (webhook received)
🎯 = Info (entry in progress)
```

---

## Next Steps

1. ✅ Add strategy to TradingView chart
2. ✅ Configure parameters
3. ✅ Create webhook alert
4. ✅ Test health/status endpoints
5. ✅ Send manual test signal
6. ✅ Monitor first real webhook signal
7. ✅ Review trade execution in bot logs
8. ✅ Track P&L and performance metrics

---

**Last Updated**: 2026-08-18  
**Bot Version**: Small-Cap Momentum Trader v2.0  
**Webhook Protocol**: JSON POST with TradingView alert message format
