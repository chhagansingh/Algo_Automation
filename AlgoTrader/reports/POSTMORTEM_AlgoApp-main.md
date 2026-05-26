# Postmortem Report: AlgoApp-main
**Generated:** 2026-05-25
**Classification:** BROKER EXECUTION TOOL (not a trading algorithm)

---

## 1. What This Project Actually Is

**AlgoApp is a GUI-based order placement application**, NOT an algorithmic trading strategy.

```
User clicks GUI → Enters strike/CE/PE/qty → App calls Zerodha/IFL API → Order placed
                       ↑
              NO automated signal generation
              NO strategy logic
              NO backtestable rules
```

---

## 2. Architecture

| Component | Purpose |
|-----------|---------|
| `main.py` | Tkinter GUI (order entry, P&L display) |
| `kite_api.py` | Zerodha Kite API wrapper (paid + free) |
| `ifl_api.py` | IFL Securities API wrapper |
| `Adapter.py` | Unified broker adapter |
| `exchange.py` | Exchange symbol formatting |
| `handlefile.py` | Excel order data persistence |
| `Auto.py` | Autocomplete for instrument search |

**Supported Brokers:**
- Zerodha Kite (paid API)
- Zerodha Kite Free (web scraping login)
- IFL Securities (India Infoline)

---

## 3. Key Constants

```python
BUY = "BUY"
SELL = "SELL"
EXIT_ALL = 0              # Global flag to square off all

CALL_FEQ = 10000          # Market data refresh: 10 seconds (ms)
NEW_CALL_FEQ = 3000       # Alternate refresh: 3 seconds (ms)

TARGETDIFF = 3            # SL/Target display offset
SLDIFF = 3

total_active = 4          # Max 4 legs per strategy
symbol = 'NIFTY'
s = 'OPTIDX'              # Options on index
api_type = 'KiteFree'
```

---

## 4. What the App Does (Manual Flow)

### Step 1: User Selects Strategy via GUI
- Instrument: NIFTY / BANKNIFTY / Stock
- Option: CE / PE
- Strike: Manual entry
- Expiry: Dropdown from API
- Buy/Sell: Radio button
- Quantity: Manual entry
- SL Delta: Display offset
- Target Delta: Display offset

### Step 2: App Fetches Live Prices
```python
m = MarketApi()
m.get_quote(id_, 2, 1502)  # bid/ask from broker
price = m.asks[0]  # for BUY
price = m.bids[0]  # for SELL
```

### Step 3: App Places Order via Broker API
```python
PlaceOrderClass.place_order(
    id_=instrument_id,
    slide=BUY/SELL,
    q=quantity,
    tradingsymbol=symbol,
    size=lot_size,
    product_type=product_value
)
```

### Step 4: P&L Tracking
```python
initsop = initial premium paid/received
csop = current premium value (live from broker)
pl = csop - initsop  # unrealized P&L
```

### Step 5: Manual Exit
- User clicks "Exit Trade" button
- Confirmation dialog
- Square off order placed via API

---

## 5. Why This Cannot Be Backtested

| Requirement | Status |
|-------------|--------|
| Entry signal logic | ❌ None — user manually enters |
| Exit condition (SL auto-trigger) | ❌ None — SL is display only |
| Exit condition (Target auto-trigger) | ❌ None — Target is display only |
| Strategy rules | ❌ None — any instrument/any direction |
| Historical data replay | ❌ No backtest engine |
| P&L calculation per trade | ⚠️ Yes — but only for live trades |

**This is a manual execution platform**, similar to:
- Zerodha Kite web interface
- Upstox Pro web interface
- Any broker's order placement screen

The only "algo" part is the Excel data persistence and real-time P&L calculation.

---

## 6. Multi-Leg Strategy Support

The app supports up to 4 legs simultaneously:
```
Leg 1: NIFTY 24000 CE BUY  Qty=X
Leg 2: NIFTY 24000 PE BUY  Qty=X  → Long Straddle
Leg 3: NIFTY 24200 CE SELL Qty=X
Leg 4: NIFTY 23800 PE SELL Qty=X  → Iron Condor
```

But the user must manually configure each leg. There is NO:
- Automatic ATM strike selection
- Automatic expiry selection (nearest weekly)
- Automatic strategy construction
- Risk/reward calculation

---

## 7. Comparison with AlgoTrader

| Feature | AlgoApp | AlgoTrader |
|---------|---------|------------|
| **Type** | Manual execution GUI | Automated signal engine |
| **Entry** | User clicks | Algorithm generates signal |
| **Exit** | User clicks "Exit" | EOD auto-close / SL logic |
| **Strategy** | None — user decides | 3 deterministic strategies |
| **Backtest** | Impossible | 19 years daily data |
| **Broker** | Direct API integration | Paper trading only |
| **P&L Track** | Real-time via broker API | Simulated via yfinance |
| **Max Legs** | 4 | Unlimited (code-based) |
| **Instruments** | Any option via broker | NIFTY only |

---

## 8. What CAN Be Salvaged

Despite being a manual tool, some components are valuable:

### A. Broker API Wrappers
`kite_api.py` + `ifl_api.py` — Could be adapted for AlgoTrader live trading:
```python
# Future: AlgoTrader live mode
from kite_api import Kite
kite.place_order(
    tradingsymbol="NIFTY26MAY24000CE",
    transaction_type=kite.TRANSACTION_TYPE_SELL,
    quantity=25,
    order_type=kite.ORDER_TYPE_MARKET
)
```

### B. Instrument ID Lookup
`get_instru_id()` function — Maps symbol+strike+expiry to broker instrument token:
```python
lot_size, token = get_instru_id("NIFTY", "CE", "2026-05-26", 24000, "OPTIDX")
```

### C. Real-Time Quote Fetching
```python
m = MarketApi()
m.get_quote(token, exchange=2, segment=1502)
bid = m.bids[0]
ask = m.asks[0]
```

### D. P&L Calculation for Multi-Leg
```python
sop = 0
for leg in legs:
    if leg.type == BUY:
        sop += qty * market_bid
    else:
        sop -= qty * market_ask
pl = sop - initial_sop
```

---

## 9. Verdict

| Metric | Score |
|--------|-------|
| **Backtestability** | 0/10 — No strategy to backtest |
| **Automated Trading** | 0/10 — Fully manual |
| **Broker Integration** | 8/10 — Supports Zerodha + IFL |
| **Code Quality** | 6/10 — Functional but spaghetti GUI code |
| **AlgoTrader Value** | 3/10 — Only API wrappers are useful |

**Overall: NOT a trading algorithm. This is a broker order management GUI.**

---

## 10. Recommendation

**DELETE from project analysis pipeline** — but SAVE broker API wrappers for future live trading integration.

### What to Keep (if anything):
1. `kite_api.py` — Zerodha API wrapper
2. `ifl_api.py` — IFL API wrapper
3. `exchange.py` — Symbol formatting utilities
4. `get_instru_id()` function — Instrument token lookup

### What to Discard:
1. `main.py` — Tkinter GUI (irrelevant)
2. `Auto.py` — Autocomplete widget
3. All Excel data handling (CSV is simpler)

---

## 11. How This Could Have Been a Strategy

To make AlgoApp backtestable, the user would need to add:

```python
# Missing: Entry Signal Logic
def generate_signal(spot, indicators):
    if daily_range < 1.0:
        return "SELL_STRADDLE", atm_strike
    return "NO_TRADE", None

# Missing: Auto Exit Logic
def check_exit(position, current_premium):
    if current_premium <= target:
        return "TARGET_EXIT"
    if current_premium >= stop_loss:
        return "SL_EXIT"
    if time >= "15:25":
        return "EOD_CLOSE"
    return "HOLD"
```

**Without these, it's just a fancy order placement screen.**

---

*Report generated by AlgoTrader import_project module*
*Classification: BROKER EXECUTION TOOL — Not backtestable*
