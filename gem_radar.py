import requests
import time
import os
import json
import threading
from datetime import datetime, timedelta
from flask import Flask, request

# =========================
# TELEGRAM (DİREKT YAZ)
# =========================
BOT_TOKEN = "8763528906:AAE7rwoVLNfQJaLxkPvmGttBTtcx2Avntjs"
CHAT_ID = "1307136561"

# =========================
# SAAT AYARLARI
# =========================
START_HOUR = 8
END_HOUR = 22
ACTIVE_SLEEP = 7200   # 2 saat
SLEEP_MODE = 300      # 5 dk

# =========================
# COINGECKO
# =========================
START_PAGE = 2
END_PAGE = 6
PER_PAGE = 100

STATE_FILE = "state.json"

app = Flask(__name__)

@app.route("/")
def home():
    return "ELITE BOT AKTIF"

# 🔥 TRADINGVIEW WEBHOOK
@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json or {}
    message = data.get("message", "🚨 SIGNAL")
    send_telegram(message)
    return "OK"

# =========================
# SESSION
# =========================
session = requests.Session()
session.headers.update({
    "accept": "application/json",
    "user-agent": "Mozilla/5.0"
})

# =========================
# ZAMAN
# =========================
def tr_now():
    return datetime.utcnow() + timedelta(hours=3)

def tr_str():
    return tr_now().strftime("%d.%m.%Y %H:%M")

# =========================
# TELEGRAM
# =========================
def send_telegram(text):
    if not BOT_TOKEN or not CHAT_ID:
        print("Telegram eksik")
        return

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": CHAT_ID,
        "text": text
    }

    try:
        requests.post(url, data=data, timeout=15)
    except Exception as e:
        print("Telegram hata:", e)

# =========================
# STATE
# =========================
def load_state():
    if not os.path.exists(STATE_FILE):
        return {"seen": {}, "pre_seen": {}}
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"seen": {}, "pre_seen": {}}

def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f)

# =========================
# API
# =========================
def get_page(page):
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": PER_PAGE,
        "page": page,
        "sparkline": "false",
        "price_change_percentage": "1h,24h,7d"
    }
    try:
        r = session.get(url, params=params, timeout=20)
        if r.status_code == 200:
            return r.json()
        return []
    except:
        return []

def get_all_data():
    coins = []
    for page in range(START_PAGE, END_PAGE + 1):
        coins += get_page(page)
        time.sleep(2)
    return coins

# =========================
# FİLTRE + SKOR
# =========================
def base_filter(c):
    rank = c.get("market_cap_rank") or 9999
    vol = c.get("total_volume") or 0
    mc = c.get("market_cap") or 1
    p1h = c.get("price_change_percentage_1h_in_currency") or 0
    p24 = c.get("price_change_percentage_24h_in_currency") or 0

    if rank < 200 or rank > 600: return False
    if vol < 4_000_000: return False
    if (vol / mc) < 0.02: return False
    if p24 < -8 or p24 > 14: return False
    if p1h < -2.5: return False

    return True

def score_coin(c):
    score = 0
    p1h = c.get("price_change_percentage_1h_in_currency") or 0
    p24 = c.get("price_change_percentage_24h_in_currency") or 0

    if 0.3 <= p1h <= 2.5: score += 30
    if 2 <= p24 <= 10: score += 30
    if c.get("total_volume",0) > 10_000_000: score += 20
    if 220 <= (c.get("market_cap_rank") or 9999) <= 450: score += 20

    return score

# =========================
# ANALİZ
# =========================
def analyze():
    coins = get_all_data()
    selected = []

    for c in coins:
        if not base_filter(c):
            continue
        sc = score_coin(c)
        if sc >= 80:
            selected.append((c, sc))

    selected.sort(key=lambda x: x[1], reverse=True)

    if not selected:
        return

    msg = f"💎 ELITE RADAR\n🕒 {tr_str()}\n\n"

    for c, sc in selected[:5]:
        symbol = (c.get("symbol") or "").upper()
        price = c.get("current_price") or 0
        msg += f"{symbol}\nFiyat: ${price:.4f}\nSkor: {sc}\n\n"

    send_telegram(msg)

# =========================
# LOOP
# =========================
def radar_loop():
    while True:
        try:
            hour = tr_now().hour
            if START_HOUR <= hour < END_HOUR:
                analyze()
                time.sleep(ACTIVE_SLEEP)
            else:
                time.sleep(SLEEP_MODE)
        except:
            time.sleep(60)

# =========================
# MAIN
# =========================
if __name__ == "__main__":
    threading.Thread(target=radar_loop, daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
