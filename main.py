import time
import yfinance as yf
import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta
import pytz
from flask import Flask

# ================== TELEGRAM BOT CONFIG ==================
BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
CHAT_ID = "YOUR_TELEGRAM_CHAT_ID"
TELEGRAM_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

# ================== STOCK LIST (TOP 100 NSE) ==================
STOCKS = [
    "RELIANCE.NS", "HDFCBANK.NS", "ICICIBANK.NS", "INFY.NS", "TCS.NS", "LT.NS",
    "AXISBANK.NS", "SBIN.NS", "BHARTIARTL.NS", "ITC.NS", "KOTAKBANK.NS",
    "WIPRO.NS", "BAJFINANCE.NS", "HCLTECH.NS", "SUNPHARMA.NS", "ADANIGREEN.NS",
    "ADANIPORTS.NS", "ADANIENT.NS", "ONGC.NS", "TITAN.NS", "POWERGRID.NS",
    "NTPC.NS", "NESTLEIND.NS", "ULTRACEMCO.NS", "HINDUNILVR.NS", "JSWSTEEL.NS",
    "BAJAJFINSV.NS", "COALINDIA.NS", "VEDL.NS", "MARUTI.NS", "CIPLA.NS",
    "HEROMOTOCO.NS", "TECHM.NS", "DRREDDY.NS", "GRASIM.NS", "HDFCLIFE.NS",
    "SBILIFE.NS", "BRITANNIA.NS", "BPCL.NS", "EICHERMOT.NS", "HAVELLS.NS",
    "ICICIPRULI.NS", "DIVISLAB.NS", "SHREECEM.NS", "INDUSINDBK.NS",
    "UPL.NS", "M&M.NS", "ASIANPAINT.NS", "TATAMOTORS.NS", "TATASTEEL.NS",
    "DLF.NS", "GAIL.NS", "PIDILITIND.NS", "LTIM.NS", "AMBUJACEM.NS",
    "ACC.NS", "PEL.NS", "BANKBARODA.NS", "PNB.NS", "CANBK.NS", "IDFCFIRSTB.NS",
    "AUROPHARMA.NS", "TORNTPHARM.NS", "LUPIN.NS", "BANDHANBNK.NS", "MUTHOOTFIN.NS",
    "BIOCON.NS", "GLENMARK.NS", "APOLLOHOSP.NS", "NAUKRI.NS", "IRCTC.NS",
    "ZOMATO.NS", "PAYTM.NS", "NYKAA.NS", "POLYCAB.NS", "INDIGO.NS",
    "MCDOWELL-N.NS", "JUBLFOOD.NS", "COLPAL.NS", "OBEROIRLTY.NS", "BOSCHLTD.NS",
    "ABB.NS", "SIEMENS.NS", "CONCOR.NS", "HAL.NS", "BEL.NS", "IOC.NS",
    "INDHOTEL.NS", "TRENT.NS", "DMART.NS", "ASHOKLEY.NS", "MOTHERSON.NS",
    "TVSMOTOR.NS", "SUPREMEIND.NS", "ALKEM.NS", "CROMPTON.NS", "ESCORTS.NS"
]

# ================== FUNCTIONS ==================

def supertrend(df, period=7, multiplier=3):
    hl2 = (df["High"] + df["Low"]) / 2
    df["ATR"] = df["High"].rolling(period).max() - df["Low"].rolling(period).min()
    df["UpperBand"] = hl2 + (multiplier * df["ATR"])
    df["LowerBand"] = hl2 - (multiplier * df["ATR"])
    df["ST"] = np.where(df["Close"] > df["UpperBand"], df["LowerBand"], df["UpperBand"])
    return df

def send_telegram(message):
    try:
        requests.post(TELEGRAM_URL, data={"chat_id": CHAT_ID, "text": message})
    except Exception as e:
        print("Telegram Error:", e)

def check_signals():
    ist = pytz.timezone("Asia/Kolkata")
    now = datetime.now(ist)

    for symbol in STOCKS:
        try:
            df = yf.download(symbol, interval="15m", period="5d")
            if df.empty:
                continue

            df["EMA20"] = df["Close"].ewm(span=20).mean()
            df["EMA50"] = df["Close"].ewm(span=50).mean()
            df["Middle"] = df["Close"].rolling(20).mean()
            df["STD"] = df["Close"].rolling(20).std()
            df["Upper"] = df["Middle"] + (2 * df["STD"])
            df["Lower"] = df["Middle"] - (2 * df["STD"])
            df = supertrend(df)

            price = df["Close"].iloc[-1]
            ema20 = df["EMA20"].iloc[-1]
            ema50 = df["EMA50"].iloc[-1]
            upper = df["Upper"].iloc[-1]
            lower = df["Lower"].iloc[-1]

            signal = None
            if ema20 > ema50 and price > upper:
                signal = f"🚀 BUY {symbol}\nPrice: {price:.2f}\nTarget: {price*1.02:.2f}\nSL: {price*0.98:.2f}"
            elif ema20 < ema50 and price < lower:
                signal = f"⚠️ SELL {symbol}\nPrice: {price:.2f}\nTarget: {price*0.98:.2f}\nSL: {price*1.02:.2f}"

            if signal:
                send_telegram(signal)

        except Exception as e:
            print(f"Error for {symbol}: {e}")

# ================== FLASK KEEP-ALIVE ==================
app = Flask(__name__)

@app.route('/')
def home():
    return "Stock Alert Bot Running!"

if __name__ == "__main__":
    while True:
        ist = pytz.timezone("Asia/Kolkata")
        now = datetime.now(ist)
        if 9 <= now.hour < 16 and now.weekday() < 5:
            check_signals()
        time.sleep(900)  # every 15 minutes
                
