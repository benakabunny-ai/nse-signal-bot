
import yfinance as yf
import pandas as pd
import ta
import requests
from datetime import datetime, time
import pytz
import time as t

TELEGRAM_TOKEN = "8371520648:AAGCXzleUzrbt4u3yE5h9nNGjK_fEM86eJM"
TELEGRAM_CHAT_ID = "6280900235"

def send_telegram_alert(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": message})

IST = pytz.timezone("Asia/Kolkata")
START_TIME = time(8, 0)
END_TIME = time(16, 0)

TICKERS = [
    "RELIANCE.NS","TCS.NS","INFY.NS","HDFC.NS","HDFCBANK.NS","ICICIBANK.NS",
    "KOTAKBANK.NS","SBIN.NS","ITC.NS","BAJFINANCE.NS","BAJAJFINSV.NS","BHARTIARTL.NS",
    "ASIANPAINT.NS","MARUTI.NS","HCLTECH.NS","LT.NS","AXISBANK.NS","SUNPHARMA.NS",
    "TITAN.NS","ULTRACEMCO.NS","NESTLEIND.NS","M&M.NS","TECHM.NS","WIPRO.NS",
    "POWERGRID.NS","JSWSTEEL.NS","INDUSINDBK.NS","ONGC.NS","DIVISLAB.NS","HINDUNILVR.NS",
    "BPCL.NS","COALINDIA.NS","TATASTEEL.NS","GRASIM.NS","ADANIPORTS.NS","SBILIFE.NS",
    "NTPC.NS","DRREDDY.NS","HDFCLIFE.NS","BAJAJ-AUTO.NS","BRITANNIA.NS","CIPLA.NS",
    "EICHERMOT.NS","IOC.NS","HEROMOTOCO.NS","UPL.NS","SHREECEM.NS","TATAMOTORS.NS",
    "VEDL.NS","HINDALCO.NS","ICICIPRULI.NS","INDIGO.NS","PIDILITIND.NS","COLPAL.NS",
    "GAIL.NS","TATACONSUM.NS","SBIN.NS","L&T.NS","MUTHOOTFIN.NS","BANKBARODA.NS",
    "MARICO.NS","AMBUJACEM.NS","BANDHANBNK.NS","CHOLAFIN.NS","ADANIENT.NS","ADANIGREEN.NS",
    "BAJAJFINSV.NS","BAJFINANCE.NS","HAVELLS.NS","ICICIBANK.NS","HCLTECH.NS","INFY.NS",
    "TATAELXSI.NS","APOLLOHOSP.NS","DRREDDY.NS","SBILIFE.NS","AXISBANK.NS","ITC.NS",
    "M&M.NS","SUNPHARMA.NS","TECHM.NS","ULTRACEMCO.NS","WIPRO.NS","ADANIPORTS.NS",
    "INDUSINDBK.NS","ONGC.NS","DIVISLAB.NS","HINDUNILVR.NS","BPCL.NS","COALINDIA.NS",
    "TATASTEEL.NS","GRASIM.NS","ADANIGREEN.NS","ADANIPOWER.NS","ICICIPRULI.NS","PIDILITIND.NS",
    "BRITANNIA.NS","HDFCLIFE.NS","HDFCBANK.NS","RELIANCE.NS","TCS.NS","INFY.NS","HDFC.NS"
]

last_alert_times = {ticker: None for ticker in TICKERS}

def fetch_data(ticker, period="5d", interval="5m"):
    df = yf.download(ticker, period=period, interval=interval)
    return df

def generate_signal(df):
    df["EMA20"] = ta.trend.EMAIndicator(df["Close"], window=20).ema_indicator()
    df["EMA50"] = ta.trend.EMAIndicator(df["Close"], window=50).ema_indicator()
    
    signal = "HOLD"
    last_close = df["Close"].iloc[-1]
    stop_loss = target = None
    
    if df["EMA20"].iloc[-1] > df["EMA50"].iloc[-1]:
        signal = "BUY"
        stop_loss = round(last_close * 0.995, 2)
        target = round(last_close * 1.01, 2)
    elif df["EMA20"].iloc[-1] < df["EMA50"].iloc[-1]:
        signal = "SELL"
        stop_loss = round(last_close * 1.005, 2)
        target = round(last_close * 0.99, 2)
    
    recent_high = df["High"].iloc[-5:].max()
    recent_low = df["Low"].iloc[-5:].min()
    breakout = last_close > recent_high
    breakdown = last_close < recent_low
    
    return signal, last_close, stop_loss, target, breakout, breakdown

while True:
    now = datetime.now(pytz.timezone("Asia/Kolkata"))
    current_time = now.time()
    weekday = now.weekday()

    if 0 <= weekday <= 4 and time(8,0) <= current_time <= time(16,0):
        send_telegram_alert("💓 Bot heartbeat: running and monitoring tickers...")
        for ticker in TICKERS:
            df = fetch_data(ticker)
            signal, price, sl, target, breakout, breakdown = generate_signal(df)

            if breakout:
                send_telegram_alert(f"🚀 BREAKOUT ALERT! {ticker}: Price={price} | SL={sl} | Target={target}")
            if breakdown:
                send_telegram_alert(f"⚡ BREAKDOWN ALERT! {ticker}: Price={price} | SL={sl} | Target={target}")

            if last_alert_times[ticker] is None or (datetime.now() - last_alert_times[ticker]).seconds >= 300:
                send_telegram_alert(f"{ticker}: {signal} | Price={price} | SL={sl} | Target={target}")
                last_alert_times[ticker] = datetime.now()
    t.sleep(30)
