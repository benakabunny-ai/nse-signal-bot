# NSE Stock Alert Bot 🚀

This bot monitors 100 NSE stocks and sends Telegram alerts for breakout/breakdown with 3 targets and stop loss.

## Deployment on Render
1. Upload repo to GitHub.
2. Create a new **Web Service** on Render → Python environment.
3. Connect GitHub repo, build from `requirements.txt`.
4. Procfile is included: `web: gunicorn main:app`.

## Keep Alive with UptimeRobot
1. Create a free account at [UptimeRobot](https://uptimerobot.com).
2. Add new monitor → HTTP(s) → enter your Render URL.
3. Interval: 5 minutes → Save.
4. Now your bot stays awake.

## Local Run
```bash
pip install -r requirements.txt
python main.py
```

## Telegram Setup
- Create bot via [BotFather](https://t.me/BotFather)
- Replace BOT_TOKEN and CHAT_ID in main.py
