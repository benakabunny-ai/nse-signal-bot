
import os
import time
import logging
import traceback
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import requests
import pandas as pd
import yfinance as yf
from flask import Flask, jsonify

# ============ Config ============
IST = ZoneInfo("Asia/Kolkata")
INTERVAL = "5m"
PERIOD = "7d"
ROLL_WINDOW = 20        # breakout/breakdown lookback
ATR_LEN = 14
TARGET_R_MULT = 1.5     # Target = 1.5 * ATR
LOOP_SLEEP = 60         # seconds
HEARTBEAT_MIN = 5
SIGNALS_MIN = 5

# Telegram (fallback to provided values if env not set)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "8371520648:AAGCXzleUzrbt4u3yE5h9nNGjK_fEM86eJM")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "6280900235")

# Top 100 NSE tickers (Yahoo suffix .NS)
TICKERS = [
    "RELIANCE.NS","HDFCBANK.NS","ICICIBANK.NS","INFY.NS","TCS.NS","LT.NS","SBIN.NS","BHARTIARTL.NS","ITC.NS","HINDUNILVR.NS",
    "KOTAKBANK.NS","BAJFINANCE.NS","AXISBANK.NS","ASIANPAINT.NS","SUNPHARMA.NS","MARUTI.NS","ULTRACEMCO.NS","ONGC.NS","TITAN.NS","NTPC.NS",
    "WIPRO.NS","POWERGRID.NS","ADANIENT.NS","ADANIGREEN.NS","ADANIPORTS.NS","ADANIPOWER.NS","LTIM.NS","M&M.NS","NESTLEIND.NS","HCLTECH.NS",
    "JSWSTEEL.NS","COALINDIA.NS","BAJAJFINSV.NS","TATAMOTORS.NS","TATASTEEL.NS","BPCL.NS","IOC.NS","HEROMOTOCO.NS","BRITANNIA.NS","DIVISLAB.NS",
    "DRREDDY.NS","GRASIM.NS","HINDALCO.NS","TECHM.NS","EICHERMOT.NS","CIPLA.NS","UPL.NS","BAJAJ-AUTO.NS","DMART.NS","DLF.NS",
    "HDFCLIFE.NS","ICICIPRULI.NS","SBILIFE.NS","PIDILITIND.NS","SHREECEM.NS","TATACONSUM.NS","MUTHOOTFIN.NS","INDUSINDBK.NS","PEL.NS","AMBUJACEM.NS",
    "ACC.NS","BERGEPAINT.NS","COLPAL.NS","DABUR.NS","GAIL.NS","HAVELLS.NS","IGL.NS","INDIGO.NS","LICHSGFIN.NS","LODHA.NS",
    "LTI.NS","HDFCAMC.NS","NAUKRI.NS","SRF.NS","TORNTPHARM.NS","TRENT.NS","VOLTAS.NS","ZYDUSLIFE.NS","AUROPHARMA.NS","APOLLOHOSP.NS",
    "ICICIGI.NS","BANKBARODA.NS","CANBK.NS","PNB.NS","BANDHANBNK.NS","FEDERALBNK.NS","IDFCFIRSTB.NS","YESBANK.NS","INDHOTEL.NS","BOSCHLTD.NS",
    "TATAPOWER.NS","OBEROIRLTY.NS","TVSMOTOR.NS","PAGEIND.NS","HINDPETRO.NS","ABB.NS","SIEMENS.NS","MCX.NS","CONCOR.NS","GODREJCP.NS"
]

# ============ App & State ============
app = Flask(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")

_last_hb_bucket = None
_last_sig_bucket = None
state = {
    "breakout_sent": {},
    "breakdown_sent": {},
    "last_signal": {},  # ticker -> {"type": "Buy"/"Sell", "time": iso}
}

# ============ Helpers ============
def now_ist():
    return datetime.now(IST)

def within_market_hours_ist(ts: datetime) -> bool:
    return (ts.weekday() < 5) and (8 <= ts.hour < 16)

def bucket_minute(ts: datetime, every: int) -> str:
    m = (ts.minute // every) * every
    return ts.replace(second=0, microsecond=0, minute=m).isoformat()

def send_tg(text: str):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        r = requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": text}, timeout=15)
        if not r.ok:
            logging.warning("Telegram send failed %s %s", r.status_code, r.text)
    except Exception as e:
        logging.exception("Telegram error: %s", e)

def fetch_df(ticker: str) -> pd.DataFrame:
    for attempt in range(3):
        try:
            df = yf.download(ticker, period=PERIOD, interval=INTERVAL, auto_adjust=True, progress=False)
            if isinstance(df, pd.DataFrame) and not df.empty:
                return df.dropna().copy()
        except Exception as e:
            logging.warning("%s fetch error (%d): %s", ticker, attempt+1, e)
        time.sleep(1 + attempt)
    return pd.DataFrame()

def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    # SMA crossover
    df["SMA20"] = df["Close"].rolling(20).mean()
    df["SMA50"] = df["Close"].rolling(50).mean()

    # ATR (manual)
    prev_close = df["Close"].shift(1)
    tr = pd.concat([
        (df["High"] - df["Low"]).abs(),
        (df["High"] - prev_close).abs(),
        (df["Low"] - prev_close).abs(),
    ], axis=1).max(axis=1)
    df["ATR"] = tr.rolling(ATR_LEN).mean()

    # Breakout/Down levels
    df["HH"] = df["High"].rolling(ROLL_WINDOW).max()
    df["LL"] = df["Low"].rolling(ROLL_WINDOW).min()

    return df

def crossover_signal(df: pd.DataFrame):
    if len(df) < 55:
        return None
    sma20_now, sma50_now = df["SMA20"].iloc[-1], df["SMA50"].iloc[-1]
    sma20_prev, sma50_prev = df["SMA20"].iloc[-2], df["SMA50"].iloc[-2]
    if pd.isna(sma20_now) or pd.isna(sma50_now) or pd.isna(sma20_prev) or pd.isna(sma50_prev):
        return None
    if sma20_now > sma50_now and sma20_prev <= sma50_prev:
        return "Buy"
    if sma20_now < sma50_now and sma20_prev >= sma50_prev:
        return "Sell"
    return None

def breakout_flags(df: pd.DataFrame):
    if len(df) < ROLL_WINDOW + 2:
        return (False, False)
    c_now, c_prev = df["Close"].iloc[-1], df["Close"].iloc[-2]
    hh_now, ll_now = df["HH"].iloc[-1], df["LL"].iloc[-1]
    hh_prev, ll_prev = df["HH"].iloc[-2], df["LL"].iloc[-2]
    is_breakout = pd.notna(hh_now) and (c_now >= hh_now) and (c_prev < hh_prev)
    is_breakdown = pd.notna(ll_now) and (c_now <= ll_now) and (c_prev > ll_prev)
    return bool(is_breakout), bool(is_breakdown)

def sl_target(side: str, price: float, atr: float):
    if pd.isna(atr) or atr <= 0:
        # fallback to ±1%
        if side == "Buy":
            return round(price*0.99,2), round(price*1.01,2)
        else:
            return round(price*1.01,2), round(price*0.99,2)
    if side == "Buy":
        return round(price - atr, 2), round(price + TARGET_R_MULT*atr, 2)
    else:
        return round(price + atr, 2), round(price - TARGET_R_MULT*atr, 2)

def fmt_signal(t, side, price, sl, tgt):
    icon = "🟢 BUY" if side == "Buy" else "🔴 SELL"
    return f"{icon} {t}\n₹{price:.2f} | SL: ₹{sl:.2f} | 🎯: ₹{tgt:.2f}\nSMA20/50 crossover\n{now_ist().strftime('%d-%b %H:%M IST')}"

def fmt_break(t, kind, price):
    return (("📈 BREAKOUT " if kind=='up' else "📉 BREAKDOWN ") +
            f"{t}\n₹{price:.2f}\n{now_ist().strftime('%d-%b %H:%M IST')}")

# ============ Core ============
def process_ticker(ticker: str):
    df = fetch_df(ticker)
    if df.empty:
        return
    df = compute_indicators(df)
    last_close = float(df["Close"].iloc[-1])

    # Immediate breakout/breakdown
    brk_up, brk_dn = breakout_flags(df)
    if brk_up:
        k = now_ist().strftime("%Y-%m-%d %H:%M")
        if state["breakout_sent"].get(ticker) != k:
            send_tg(fmt_break(ticker, "up", last_close))
            state["breakout_sent"][ticker] = k
    if brk_dn:
        k = now_ist().strftime("%Y-%m-%d %H:%M")
        if state["breakdown_sent"].get(ticker) != k:
            send_tg(fmt_break(ticker, "down", last_close))
            state["breakdown_sent"][ticker] = k

    # Regular SMA signals (only once per change)
    sig = crossover_signal(df)
    if sig:
        prev = state["last_signal"].get(ticker, {}).get("type")
        if prev != sig:
            atr = float(df["ATR"].iloc[-1]) if pd.notna(df["ATR"].iloc[-1]) else float("nan")
            sl, tgt = sl_target(sig, last_close, atr)
            send_tg(fmt_signal(ticker, sig, last_close, sl, tgt))
            state["last_signal"][ticker] = {"type": sig, "time": now_ist().isoformat()}

def bot_loop():
    global _last_hb_bucket, _last_sig_bucket
    logging.info("Bot loop started.")
    while True:
        try:
            ts = now_ist()
            if within_market_hours_ist(ts):
                hb_bucket = bucket_minute(ts, HEARTBEAT_MIN)
                sig_bucket = bucket_minute(ts, SIGNALS_MIN)

                # Process all tickers (trim if needed for free plan stability)
                for t in TICKERS:
                    try:
                        process_ticker(t)
                    except Exception as te:
                        logging.warning("[%s] processing error: %s", t, te)
                        traceback.print_exc()

                # Heartbeat
                if hb_bucket != _last_hb_bucket:
                    send_tg(f"💓 Heartbeat {ts.strftime('%d-%b %H:%M IST')} | {len(TICKERS)} tickers")
                    _last_hb_bucket = hb_bucket

                # mark signals bucket
                if sig_bucket != _last_sig_bucket:
                    _last_sig_bucket = sig_bucket

            time.sleep(LOOP_SLEEP)

        except Exception as e:
            logging.error("Main loop error: %s", e)
            traceback.print_exc()
            time.sleep(5)

# Start background thread
import threading
threading.Thread(target=bot_loop, daemon=True).start()

# ============ Flask ============
app = Flask(__name__)

@app.get("/")
def index():
    return "✅ India Stock Bot (SMA20/50 • ATR SL/Target • Breakout/Down)."

@app.get("/healthz")
def health():
    return jsonify(ok=True, tickers=len(TICKERS), time=now_ist().strftime("%Y-%m-%d %H:%M:%S IST"))

if __name__ == "__main__":
    port = int(os.getenv("PORT", "10000"))
    app.run(host="0.0.0.0", port=port)
