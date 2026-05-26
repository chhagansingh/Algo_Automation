"""
AlgoTrader — Global Configuration
All paths, constants, and algo metadata in one place.
"""
import os

# ── Base paths ────────────────────────────────────────────────────────────────
BASE_DIR        = os.path.dirname(os.path.abspath(__file__))
DATA_DIR        = os.path.join(BASE_DIR, "data")
TRADES_DIR      = os.path.join(DATA_DIR, "trades")
PAPER_DIR       = os.path.join(DATA_DIR, "paper")
LOGS_DIR        = os.path.join(BASE_DIR, "logs")
FRONTEND_DIR    = os.path.join(BASE_DIR, "frontend")

# ── CSV file paths ─────────────────────────────────────────────────────────────
CSV_TRADES = {
    "algo1": os.path.join(TRADES_DIR, "algo1_trades.csv"),
    "algo2": os.path.join(TRADES_DIR, "algo2_trades.csv"),
    "algo3": os.path.join(TRADES_DIR, "algo3_trades.csv"),
    "algo4": os.path.join(TRADES_DIR, "algo4_trades.csv"),
    "algo5": os.path.join(TRADES_DIR, "algo5_trades.csv"),
    "algo6": os.path.join(TRADES_DIR, "algo6_trades.csv"),
    "algo7": os.path.join(TRADES_DIR, "algo7_trades.csv"),
    "algo8": os.path.join(TRADES_DIR, "algo8_trades.csv"),
    "algo9": os.path.join(TRADES_DIR, "algo9_trades.csv"),
    "algo10": os.path.join(TRADES_DIR, "algo10_trades.csv"),
    "algo11": os.path.join(TRADES_DIR, "algo11_trades.csv"),
    "algo12": os.path.join(TRADES_DIR, "algo12_trades.csv"),
    "algo13": os.path.join(TRADES_DIR, "algo13_trades.csv"),
    "algo14": os.path.join(TRADES_DIR, "algo14_trades.csv"),
    "algo15": os.path.join(TRADES_DIR, "algo15_trades.csv"),
    "algo16": os.path.join(TRADES_DIR, "algo16_trades.csv"),
    "algo17": os.path.join(TRADES_DIR, "algo17_trades.csv"),
}
CSV_PAPER_OPEN = {
    "algo1": os.path.join(PAPER_DIR, "algo1_paper_open.csv"),
    "algo2": os.path.join(PAPER_DIR, "algo2_paper_open.csv"),
    "algo3": os.path.join(PAPER_DIR, "algo3_paper_open.csv"),
    "algo4": os.path.join(PAPER_DIR, "algo4_paper_open.csv"),
    "algo5": os.path.join(PAPER_DIR, "algo5_paper_open.csv"),
    "algo6": os.path.join(PAPER_DIR, "algo6_paper_open.csv"),
    "algo7": os.path.join(PAPER_DIR, "algo7_paper_open.csv"),
    "algo8": os.path.join(PAPER_DIR, "algo8_paper_open.csv"),
    "algo9": os.path.join(PAPER_DIR, "algo9_paper_open.csv"),
    "algo10": os.path.join(PAPER_DIR, "algo10_paper_open.csv"),
    "algo11": os.path.join(PAPER_DIR, "algo11_paper_open.csv"),
    "algo12": os.path.join(PAPER_DIR, "algo12_paper_open.csv"),
    "algo13": os.path.join(PAPER_DIR, "algo13_paper_open.csv"),
    "algo14": os.path.join(PAPER_DIR, "algo14_paper_open.csv"),
    "algo15": os.path.join(PAPER_DIR, "algo15_paper_open.csv"),
    "algo16": os.path.join(PAPER_DIR, "algo16_paper_open.csv"),
    "algo17": os.path.join(PAPER_DIR, "algo17_paper_open.csv"),
}
CSV_DAILY_SUMMARY = os.path.join(DATA_DIR, "daily_summary.csv")

# ── Algo metadata ─────────────────────────────────────────────────────────────
ALGOS = {
    "algo1": {
        "id": "algo1",
        "name": "RD-Straddle [58%WR · Stable]",
        "short_name": "RD-Straddle",
        "tag": "58%WR · Stable",
        "subtitle": "Binary Short Straddle — Daily Range Filter",
        "symbol": "NIFTY",
        "lot_size": 25,
        "initial_capital": 200_000,
        "signal_names": ["STRADDLE_SELL"],
        "exit_reasons": ["TARGET_EXIT", "SL_EXIT", "NO_TRADE"],
        "signal_cards": ["Daily_Range_%", "Close_Move_%", "Trade_Signal"],
    },
    "algo2": {
        "id": "algo2",
        "name": "NTB-ScenB [97%WR · Best]",
        "short_name": "NTB-ScenB",
        "tag": "97%WR · Best",
        "subtitle": "Short Straddle — Close-Move Filtered (Scenario B)",
        "symbol": "NIFTY",
        "lot_size": 25,
        "initial_capital": 200_000,
        "signal_names": ["SHORT_STRADDLE"],
        "exit_reasons": ["THRESHOLD_EXIT", "CLOSE_MOVE_EXIT", "NO_TRADE"],
        "signal_cards": ["Daily_Range_%", "Close_Move_%", "Win_PnL", "Loss_PnL"],
    },
    "algo3": {
        "id": "algo3",
        "name": "EMA Crossover [39%WR · Developing]",
        "short_name": "EMA-Cross",
        "tag": "39%WR · Developing",
        "subtitle": "EMA 5/20 + RSI Filter — Lagged Directional CE/PE",
        "symbol": "NIFTY",
        "lot_size": 25,
        "initial_capital": 200_000,
        "signal_names": ["EMA_BUY_CE", "EMA_BUY_PE"],
        "exit_reasons": ["TARGET_EXIT", "SL_EXIT"],
        "signal_cards": ["Spot", "EMA5", "EMA20", "RSI"],
    },
    "algo4": {
        "id": "algo4",
        "name": "Flow-NIFTY [39%WR · Study]",
        "short_name": "Flow-NIFTY",
        "tag": "39%WR · Study",
        "subtitle": "Options-Flow Proxy (EMA-13 Trend) — Buy NIFTY",
        "symbol": "NIFTY",
        "lot_size": 25,
        "initial_capital": 200_000,
        "signal_names": ["FLOW_BUY_NIFTY"],
        "exit_reasons": ["TARGET_EXIT", "SL_EXIT", "NO_TRADE"],
        "signal_cards": ["Spot", "EMA_13", "Above_EMA", "Flow_Signal_Tomorrow"],
    },
    "algo5": {
        "id": "algo5",
        "name": "VIX Reversion [Study]",
        "short_name": "VIX-Reversion",
        "tag": "Study",
        "subtitle": "India VIX Mean-Reversion — Buy NIFTY when Fear Spikes",
        "symbol": "NIFTY",
        "lot_size": 25,
        "initial_capital": 200_000,
        "signal_names": ["VIX_BUY_NIFTY"],
        "exit_reasons": ["TARGET_EXIT", "SL_EXIT", "EOD_EXIT", "NO_TRADE"],
        "signal_cards": ["Spot", "VIX", "VIX_Thresh", "VIX_Signal_Tomorrow"],
    },
    "algo6": {
        "id": "algo6",
        "name": "SuperTrend Spread [Study]",
        "short_name": "SuperTrend-Spread",
        "tag": "Study",
        "subtitle": "SuperTrend + ADX — Trend-Following Credit Spread",
        "symbol": "NIFTY",
        "lot_size": 25,
        "initial_capital": 200_000,
        "signal_names": ["ST_BUY", "ST_SELL"],
        "exit_reasons": ["TREND_FLIP", "EOD_CLOSE", "NO_TRADE"],
        "signal_cards": ["Spot", "SuperTrend", "ST_Period", "ST_Multiplier"],
    },
    "algo7": {
        "id": "algo7",
        "name": "Dual Thrust [57%WR · Viable]",
        "short_name": "Dual-Thrust",
        "tag": "57%WR · Viable",
        "subtitle": "Opening Range Breakout — N-day Range Thresholds",
        "symbol": "NIFTY",
        "lot_size": 25,
        "initial_capital": 200_000,
        "signal_names": ["DT_BUY", "DT_SELL"],
        "exit_reasons": ["EOD_EXIT", "EOD_CLOSE", "NO_TRADE"],
        "signal_cards": ["Spot", "Upper", "Lower", "DT_Period", "DT_K"],
    },
    "algo8": {
        "id": "algo8",
        "name": "CPMA Scalper [38%WR · Developing]",
        "short_name": "CPMA-Scalper",
        "tag": "38%WR · Developing",
        "subtitle": "EMA(20) vs CPMA(21) Crossover — 0.5% SL / 1% Target / 5-bar Max Hold",
        "symbol": "NIFTY",
        "lot_size": 25,
        "initial_capital": 200_000,
        "signal_names": ["CPMA_BUY", "CPMA_SELL"],
        "exit_reasons": ["TARGET_EXIT", "SL_EXIT", "SIGNAL_FLIP", "MAX_HOLD", "EOD_CLOSE"],
        "signal_cards": ["Spot", "EMA", "CPMA", "EMA_Period", "CPMA_Period"],
    },
    "algo9": {
        "id": "algo9",
        "name": "Bullish Scanner [Developing]",
        "short_name": "Bullish-Scanner",
        "tag": "Developing",
        "subtitle": "Composite Score (SMA+RSI+MACD+ADX+Momentum) — Buy CE on Score >= Threshold",
        "symbol": "NIFTY",
        "lot_size": 25,
        "initial_capital": 200_000,
        "signal_names": ["SCANNER_BUY_CE"],
        "exit_reasons": ["SCORE_EXIT", "EOD_CLOSE", "NO_TRADE"],
        "signal_cards": ["Spot", "Bullish_Score", "Entry_Thresh", "Exit_Thresh"],
    },
    "algo10": {
        "id": "algo10",
        "name": "Awesome Oscillator [50%WR · Developing]",
        "short_name": "Awesome-Oscillator",
        "tag": "50%WR · Developing",
        "subtitle": "AO(3,21) + ADX>25 — Directional ATM CE/PE with 0.75% Target / 0.75% SL",
        "symbol": "NIFTY",
        "lot_size": 25,
        "initial_capital": 200_000,
        "signal_names": ["AO_BUY_CE", "AO_BUY_PE"],
        "exit_reasons": ["TARGET_HIT", "SL_HIT", "EOD_CLOSE", "NO_TRADE"],
        "signal_cards": ["Spot", "AO", "ADX", "AO_Short", "AO_Long"],
    },
    "algo11": {
        "id": "algo11",
        "name": "Gamma Scalping Proxy [Study]",
        "short_name": "Gamma-Scalping",
        "tag": "Study",
        "subtitle": "Long ATM Straddle + Delta Hedge — Daily proxy for gamma scalping (NOT true gamma scalping)",
        "symbol": "NIFTY",
        "lot_size": 25,
        "initial_capital": 200_000,
        "signal_names": ["LONG_STRADDLE"],
        "exit_reasons": ["EOD_CLOSE", "NO_TRADE"],
        "signal_cards": ["Spot", "Strike", "DTE", "IV", "Pos_Size_%"],
    },
    "algo12": {
        "id": "algo12",
        "name": "NIFTY Dip Recovery [Study]",
        "short_name": "Dip-Recovery",
        "tag": "Study",
        "subtitle": "Buy ATM CE on 2% dip from 20-day high — 4% recovery target / 50% SL / 5-day max hold",
        "symbol": "NIFTY",
        "lot_size": 25,
        "initial_capital": 200_000,
        "signal_names": ["DIP_BUY_CE"],
        "exit_reasons": ["RECOVERY_EXIT", "SL_EXIT", "MAX_HOLD_EXIT", "NO_TRADE"],
        "signal_cards": ["Spot", "Roll_High", "Drawdown_%", "Trigger_%", "Entry_Px", "DTE"],
    },
    "algo13": {
        "id": "algo13",
        "name": "Signal Rolling [49%WR · Viable]",
        "short_name": "Signal-Rolling",
        "tag": "49%WR · Viable",
        "subtitle": "Consecutive 3-day close momentum — Buy ATM CE/PE on streak breakout",
        "symbol": "NIFTY",
        "lot_size": 25,
        "initial_capital": 200_000,
        "signal_names": ["ROLL_BUY_CE", "ROLL_BUY_PE"],
        "exit_reasons": ["TARGET_EXIT", "SL_EXIT", "MAX_HOLD_EXIT", "NO_TRADE"],
        "signal_cards": ["Spot", "Close", "Streak", "Direction", "Entry_Px", "DTE"],
    },
    "algo14": {
        "id": "algo14",
        "name": "ML-RF Classifier [49%WR · Viable]",
        "short_name": "ML-RF",
        "tag": "49%WR · Viable",
        "subtitle": "RandomForest on RSI/MACD/BB/vol — Predict next-day direction → ATM CE/PE",
        "symbol": "NIFTY",
        "lot_size": 25,
        "initial_capital": 200_000,
        "signal_names": ["ML_BUY_CE", "ML_BUY_PE"],
        "exit_reasons": ["TARGET_EXIT", "SL_EXIT", "MAX_HOLD_EXIT", "NO_TRADE"],
        "signal_cards": ["Spot", "RSI", "MACD", "BB_Pos", "Pred_Up", "Entry_Px", "DTE"],
    },
    "algo15": {
        "id": "algo15",
        "name": "Aggregate Score [45%WR · Viable]",
        "short_name": "Agg-Score",
        "tag": "45%WR · Viable",
        "subtitle": "9 normalized indicators → dynamic weighted aggregate score → vol-adjusted signal. From FreqAI-LSTM crypto project.",
        "symbol": "NIFTY",
        "lot_size": 25,
        "initial_capital": 200_000,
        "signal_names": ["AGG_BUY_CE", "AGG_BUY_PE"],
        "exit_reasons": ["TARGET_EXIT", "SL_EXIT", "MAX_HOLD_EXIT", "NO_TRADE"],
        "signal_cards": ["Spot", "S_Score", "Vol_Adj", "Target", "Buy_Thresh", "Sell_Thresh", "Entry_Px", "DTE"],
    },
    "algo16": {
        "id": "algo16",
        "name": "NIFTY Scalper (4/5) [94%WR · Intraday]",
        "short_name": "Scalper-4/5",
        "tag": "94%WR · Intraday",
        "subtitle": "5-checklist confluence (VWAP+EMA+Supertrend+RSI+VIX) — 4/5 align → ATM CE/PE. +2%Tgt/-5%SL. Max 5/day.",
        "symbol": "NIFTY",
        "lot_size": 25,
        "initial_capital": 200_000,
        "signal_names": ["SCALP_BUY_CE", "SCALP_BUY_PE"],
        "exit_reasons": ["TARGET_EXIT", "SL_EXIT", "EOD_EXIT", "NO_TRADE"],
        "signal_cards": ["Spot", "Bull_Count", "Bear_Count", "VWAP", "EMA", "ST", "RSI", "VIX", "Strike", "Entry_Px", "TTE"],
    },
    "algo17": {
        "id": "algo17",
        "name": "NIFTY Scalper (3/5) [95%WR · Intraday]",
        "short_name": "Scalper-3/5",
        "tag": "95%WR · Intraday",
        "subtitle": "5-checklist confluence (VWAP+EMA+Supertrend+RSI+VIX) — 3/5 align → ATM CE/PE. +2%Tgt/-5%SL. Max 5/day. Aggressive.",
        "symbol": "NIFTY",
        "lot_size": 25,
        "initial_capital": 200_000,
        "signal_names": ["SCALP_BUY_CE", "SCALP_BUY_PE"],
        "exit_reasons": ["TARGET_EXIT", "SL_EXIT", "EOD_EXIT", "NO_TRADE"],
        "signal_cards": ["Spot", "Bull_Count", "Bear_Count", "VWAP", "EMA", "ST", "RSI", "VIX", "Strike", "Entry_Px", "TTE"],
    },
}

ALGO_IDS = list(ALGOS.keys())

# ── Market constants ──────────────────────────────────────────────────────────
NIFTY_TICKER    = "^NSEI"
STRIKE_STEP     = 50
RISK_FREE_RATE  = 0.07
BASE_IV         = 0.13
EXPIRY_DAYS     = 3          # weekly expiry assumption for BS pricing

# ── Paper trading ─────────────────────────────────────────────────────────────
PAPER_INTERVAL_SECONDS = 60   # check for signals every 60s during market hours
OPTION_CHAIN_REFRESH_SECONDS = 60  # NSE option chain poll interval (same as NSE-OCA default)
MARKET_OPEN_IST  = "09:15"
MARKET_CLOSE_IST = "15:30"

# ── NSE Option Chain ──────────────────────────────────────────────────────────
NSE_SYMBOL = "NIFTY"
