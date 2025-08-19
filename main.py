import yfinance as yf
import requests
import time
from datetime import datetime
import pytz
from flask import Flask
import threading
import os

app = Flask(__name__)

# Telegram bot credentials
BOT_TOKEN = "8371520648:AAGCXzleUzrbt4u3yE5h9nNGjK_fEM86eJM"
CHAT_ID = "6280900235"

IST = pytz.timezone('Asia/Kolkata')

# NSE 100 stock list
symbols = [
    "ABB.NS","ADANIENSOL.NS","ADANIENT.NS","ADANIGREEN.NS","ADANIPORTS.NS","ADANIPOWER.NS",
    "AMBUJACEM.NS","APOLLOHOSP.NS","ASIANPAINT.NS","DMART.NS","AXISBANK.NS","BAJAJ-AUTO.NS",
    "BAJFINANCE.NS","BAJAJFINSV.NS","BAJAJHLDNG.NS","BAJAJHFL.NS","BANKBARODA.NS","BEL.NS",
    "BPCL.NS","BHARTIARTL.NS","BOSCHLTD.NS","BRITANNIA.NS","CGPOWER.NS","CANBK.NS",
    "CHOLAFIN.NS","CIPLA.NS","COALINDIA.NS","DLF.NS","DABUR.NS","DIVISLAB.NS","DRREDDY.NS",
    "EICHERMOT.NS","ETERNAL.NS","GAIL.NS","GODREJCP.NS","GRASIM.NS","HCLTECH.NS","HDFCBANK.NS",
    "HDFCLIFE.NS","HAVELLS.NS","HEROMOTOCO.NS","HINDALCO.NS","HAL.NS","HINDUNILVR.NS",
    "HYUNDAI.NS","ICICIBANK.NS","ICICIGI.NS","ICICIPRULI.NS","ITC.NS","INDHOTEL.NS","IOC.NS",
    "IRFC.NS","INDUSINDBK.NS","NAUKRI.NS","INFY.NS","INDIGO.NS","JSWENERGY.NS","JSWSTEEL.NS",
    "JINDALSTEL.NS","JIOFIN.NS","KOTAKBANK.NS","LTIM.NS","LT.NS","LICI.NS","LODHA.NS",
    "M&M.NS","MARUTI.NS","NTPC.NS","NESTLEIND.NS","ONGC.NS","PIDILITIND.NS","PFC.NS",
    "POWERGRID.NS","PNB.NS","RECLTD.NS","RELIANCE.NS","SBILIFE.NS","MOTHERSON.NS","SHREECEM.NS",
    "SHRIRAMFIN.NS","SIEMENS.NS","SBIN.NS","SUNPHARMA.NS","SWIGGY.NS","TVSMOTOR.NS",
    "TCS.NS","TATACONSUM.NS","TATAMOTORS.NS","TATAPOWER.NS","TATASTEEL.NS","TECHM.NS",
    "TITAN.NS","TORNTPHARM.NS","TRENT.NS","ULTRACEMCO.NS","UNITDSPR.NS","VBL.NS","VEDL.NS",
    "WIPRO.NS","ZYDUSLIFE.NS"
]

def send_telegram_message(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": msg}
    try:
        requests.post(url, data=data)
    except Exception as e:
        print(f"Telegram send error: {e}")

def fetch_previous_day(symbol):
    ticker = yf.Ticker(symbol)
    hist = ticker.history(period="2d")
    if len(hist) < 2:
        return None
    return hist.iloc[-2]

def fetch_intraday(symbol, interval="5m"):
    ticker = yf.Ticker(symbol)
    data = ticker.history(period="1d", interval=interval)
    return data

def calculate_targets(price, direction):
    targets = []
    stop_loss_pct = 0.015
    target_pcts = [0.01, 0.02, 0.03]
    if direction == "UP":
        for pct in target_pcts:
            targets.append(price * (1 + pct))
        stop_loss = price * (1 - stop_loss_pct)
    else:
        for pct in target_pcts:
            targets.append(price * (1 - pct))
        stop_loss = price * (1 + stop_loss_pct)
    return targets, stop_loss

def check_alerts(symbol):
    prev_day = fetch_previous_day(symbol)
    if prev_day is None:
        return
    intraday = fetch_intraday(symbol)
    if intraday.empty:
        return
    last_price = intraday['Close'][-1]
    prev_high = prev_day['High']
    prev_low = prev_day['Low']
    if last_price > prev_high:
        targets, stop_loss = calculate_targets(last_price, "UP")
        msg = (f"{symbol} BREAKOUT 🚀\nPrice: {last_price:.2f} > High {prev_high:.2f}\n"
               f"Target1: {targets[0]:.2f}\nTarget2: {targets[1]:.2f}\nTarget3: {targets[2]:.2f}\n"
               f"Stop Loss: {stop_loss:.2f}\nAction: BUY")
        send_telegram_message(msg)
    elif last_price < prev_low:
        targets, stop_loss = calculate_targets(last_price, "DOWN")
        msg = (f"{symbol} BREAKDOWN ⚠️\nPrice: {last_price:.2f} < Low {prev_low:.2f}\n"
               f"Target1: {targets[0]:.2f}\nTarget2: {targets[1]:.2f}\nTarget3: {targets[2]:.2f}\n"
               f"Stop Loss: {stop_loss:.2f}\nAction: SELL")
        send_telegram_message(msg)

def run_bot():
    while True:
        now = datetime.now(IST)
        if now.weekday() < 5 and now.hour >= 9 and (now.hour < 15 or (now.hour == 15 and now.minute <= 30)):
            for sym in symbols:
                check_alerts(sym)
                time.sleep(1)
            time.sleep(300)
        else:
            time.sleep(600)

@app.route('/')
def home():
    now = datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")
    return f"Stock Alert Bot running at {now} IST"

if __name__ == "__main__":
    threading.Thread(target=run_bot, daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
