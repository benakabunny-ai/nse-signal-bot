# Stock Alert Bot 🚀

This bot scans **Nifty 100 stocks** and sends Telegram alerts when breakout/breakdown happens with 3 targets & stop loss.

### Deployment (Render Free Tier)
1. Push this repo to GitHub.
2. Connect GitHub repo to [Render](https://render.com).
3. Select "Worker" type service.
4. Done! Bot runs 24/7 (use UptimeRobot if needed).

### Files
- main.py → Main bot logic
- nifty100.csv → NSE 100 stock list
- requirements.txt → Dependencies
- Procfile → Process type
- render.yaml → Render deployment config
