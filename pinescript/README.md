# ORB Break → Retest → Go (5-min vs 15-min opening range)

`orb_break_retest_go.pine` is a TradingView Pine Script v6 **strategy**.

## Rules
1. Mark the high/low of the first **5** or **15** minutes after the open (default 09:30 New York).
2. **Long:** a candle closes above the OR high → price pulls back to the OR high (retest zone) →
   a candle closes above the retest candle's high → buy at the next candle's open.
3. **Short:** the same thing in reverse below the OR low.
4. The setup is cancelled if price closes back inside the range (by more than the "fail" %).
5. Stop goes beyond the retest swing (or the OR midpoint, or the other side of the range), plus a buffer.
   The target is a multiple of the risk (default 2R). Any trade still open is closed at 15:55. No new entries after 12:00.

## How to compare 5-min vs 15-min
1. In TradingView, open the Pine Editor, paste the file in, then click **Add to chart**.
2. Use a **1-minute or 5-minute** chart (SPY, QQQ, or any stock). A 1-minute chart gives more exact fills, but it has less history.
3. The table in the top-right corner shows **both** opening ranges side by side: trades, win rate, average R, total R and profit factor,
   and which one has the higher win rate.
4. To check either one in the Strategy Tester, change *Opening range to TRADE* to 5 or 15.

The table measures results in R (multiples of the planned risk), with no commission or slippage.
The Strategy Tester uses the commission and slippage you set in the strategy's Properties.
Win rate on its own can be misleading, so also compare avg R and profit factor.
