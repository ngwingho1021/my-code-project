# One Box Scalper (5-min vs 15-min box)

`orb_break_retest_go.pine` is a TradingView Pine Script v6 **strategy**. It follows the "One Box Scalper"
from Scarface Trades' video *My Simple 5 Minute "First Candle" Scalping Strategy*.

## Rules
1. **Box:** the high and low of the first 5-minute candle after the open (09:30–09:35 New York time).
   No trades while price is inside the box.
2. **Breakout:** on the **1-minute chart**, a candle closes above the box (long) or below it (short).
3. **Retest + confirmation:** price comes back to the edge of the box and prints a reversal candle,
   which must close back outside the box:
   - Long: a hammer (long lower wick) or a bullish engulfing candle
   - Short: a shooting star / inverted hammer (long upper wick) or a bearish engulfing candle

   The trade is entered at the next candle's open.
4. **Exit (default, SPX options):** stop -15% / take profit +30% of the option premium, converted to SPX points with delta
   (SPX points = premium × % ÷ delta; with $20 premium and 0.50 delta: stop 6 pts, target 12 pts).
   **Exit (chart mode):** stop just beyond the signal candle (you can also choose the retest swing, the middle of the box, or the other side of the box).
   **Target:** 2R.
5. **Cancelled:** if price closes through to the other side of the box before a confirmation candle appears.
6. Only trades the first 90 minutes (no new entries after 11:00). Max 1 trade per day by default.

## Comparing the 5-min and 15-min box
Add the strategy to a **1-minute** chart. The table in the top-right corner shows both boxes side by side
(trades, win rate, avg R, total R, profit factor) and which one has the higher win rate.
For the full Strategy Tester report on each one, change *Box to TRADE* between 5 and 15.

The table measures results in R (multiples of the planned risk), with no commission or slippage.
TradingView only keeps a limited amount of 1-minute history, depending on your plan.
