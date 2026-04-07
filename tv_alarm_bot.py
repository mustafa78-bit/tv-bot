from flask import Flask, request
import requests

app = Flask(__name__)

TOKEN = "8679518067:AAHE-60FofyqLzv1Flo0kG8EYpE69hYS0U4"
CHAT_ID = "1307136561"

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = {
        "chat_id": CHAT_ID,
        "text": message
    }
    requests.post(url, data=data)

@app.route("/")
def home():
    return "TV Alarm Bot OK"

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.get_json(force=True)

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
        print("HATA:", e)
        return "ERROR", 200

if __name__ == "__main__":
    app.run(port=5000)