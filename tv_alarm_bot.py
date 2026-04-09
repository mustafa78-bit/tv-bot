from flask import Flask, request
import requests
import os

app = Flask(__name__)

TOKEN = os.environ.get("AAHE-60FofyqLzv1Flo0kG8EYpE69hYS0U4")
CHAT_ID = os.environ.get("1307136561")

def send_telegram(message):
    if not TOKEN or not CHAT_ID:
        print("HATA: TOKEN veya CHAT_ID eksik")
        return

    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = {
        "chat_id": CHAT_ID,
        "text": message
    }

    try:
        r = requests.post(url, data=data, timeout=15)
        print("Telegram cevap:", r.status_code, r.text)
    except Exception as e:
        print("Telegram gönderim hatası:", str(e))

@app.route("/")
def home():
    return "BOT AKTIF", 200

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.get_json(force=True) or {}
        print("Gelen veri:", data)

        signal = data.get("signal", "YOK")
        ticker = data.get("ticker", "YOK")
        tf = data.get("tf", "YOK")
        price = data.get("price", "YOK")

        message = f"""🔥 ICARUS {signal}

Coin: {ticker}
TF: {tf}
Price: {price}
"""

        send_telegram(message)
        return "OK", 200

    except Exception as e:
        print("WEBHOOK HATA:", str(e))
        return "ERROR", 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    print(f"Sunucu başlıyor, port: {port}")
    app.run(host="0.0.0.0", port=port)
