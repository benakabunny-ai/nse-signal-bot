import yfinance as yf
import requests
import time
from datetime import datetime
import pytz
import pandas as pd

BOT_TOKEN = "YOUR_BOT_TOKEN"
CHAT_ID = "YOUR_CHAT_ID"
IST = pytz.timezone('Asia/Kolkata')

symbols = pd.read_csv("nifty100.csv")["Symbol"].tolist()

def send_telegram_message(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": msg}
    requests.post(url, data=data)

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
    target_pct = [0.01, 0.02, 0.03]
    stop_loss_pct = 0.015
    targets = []
    if direction == "UP":
        for pct in target_pct:
            targets.append(price * (1 + pct))
        stop_loss = price * (1 - stop_loss_pct)
    else:
        for pct in target_pct:
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
        msg = f"{symbol} BREAKOUT 🚀\nPrice: {last_price:.2f}\nTargets: {', '.join([str(round(t,2)) for t in targets])}\nStop Loss: {stop_loss:.2f}\nAction: BUY"
        send_telegram_message(msg)
    elif last_price < prev_low:
        targets, stop_loss = calculate_targets(last_price, "DOWN")
        msg = f"{symbol} BREAKDOWN ⚠️\nPrice: {last_price:.2f}\nTargets: {', '.join([str(round(t,2)) for t in targets])}\nStop Loss: {stop_loss:.2f}\nAction: SELL"
        send_telegram_message(msg)

def is_market_open():
    now = datetime.now(IST)
    if now.weekday() >= 5:
        return False
    start = now.replace(hour=9, minute=15, second=0, microsecond=0)
    end = now.replace(hour=15, minute=30, second=0, microsecond=0)
    return start <= now <= end

def main():
    while True:
        if is_market_open():
            for sym in symbols:
                check_alerts(sym)
                time.sleep(1)
            time.sleep(300)
        else:
            time.sleep(600)

if __name__ == "__main__":
    main()
