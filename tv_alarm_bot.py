from flask import Flask, request
import requests
import os

app = Flask(__name__)

TOKEN = os.environ.get("TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

def send_telegram(message):
    if not TOKEN or not CHAT_ID:
        print("❌ TOKEN veya CHAT_ID eksik!")
        return

    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = {
        "chat_id": CHAT_ID,
        "text": message
    }

    try:
        response = requests.post(url, data=data)
        print("📩 Telegram cevap:", response.text)
    except Exception as e:
        print("❌ Telegram gönderim hatası:", str(e))


@app.route("/")
def home():
    return "TV Alarm Bot OK"


@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.get_json(force=True)
        print("📥 Gelen veri:", data)

        signal = data.get("signal", "YOK")
        ticker = data.get("ticker", "YOK")
        tf = data.get("tf", "YOK")
        price = data.get("price", "YOK")

        message = f"""
🔥 ICARUS {signal}

Coin: {ticker}
TF: {tf}
Price: {price}
"""

        send_telegram(message)

        return "OK", 200

    except Exception as e:
        print("❌ HATA:", str(e))
        return "ERROR", 500
