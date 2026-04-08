import requests
import time
import json
import os
from datetime import datetime, timedelta

import os

BOT_TOKEN = os.getenv("8763528906:AAE7rwoVLNfQJaLxkPvmGttBTtcx2Avntjs")
CHAT_ID = os.getenv("1307136561")


CHECK_INTERVAL = 900
START_PAGE = 2
END_PAGE = 4
PER_PAGE = 100

STATE_FILE = "gem_state.json"

session = requests.Session()
session.headers.update({
    "accept": "application/json",
    "user-agent": "Mozilla/5.0"
})

def now_tr():
    return datetime.utcnow() + timedelta(hours=3)

def saat_uygun_mu():
    saat = now_tr().hour
    return 8 <= saat <= 22

def send(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg})
    except:
        pass

def load_state():
    if not os.path.exists(STATE_FILE):
        return {"seen": {}, "pre_seen": {}}
    with open(STATE_FILE, "r") as f:
        return json.load(f)

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)

def veri(page):
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": PER_PAGE,
        "page": page,
        "sparkline": "false",
        "price_change_percentage": "1h,24h"
    }
    try:
        r = session.get(url, params=params, timeout=20)
        if r.status_code == 200:
            return r.json()
        if r.status_code == 429:
            time.sleep(20)
            return []
    except:
        return []
    return []

def uygun(c):
    rank = c.get("market_cap_rank") or 999
    vol = c.get("total_volume") or 0
    p24 = c.get("price_change_percentage_24h_in_currency") or 0

    if not (150 <= rank <= 400): return False
    if vol < 2_000_000: return False
    if p24 < -10 or p24 > 15: return False
    return True

def skor(c):
    score = 0
    vol = c.get("total_volume") or 0
    mc = c.get("market_cap") or 1
    p1 = c.get("price_change_percentage_1h_in_currency") or 0
    p24 = c.get("price_change_percentage_24h_in_currency") or 0

    oran = vol / mc if mc > 0 else 0

    if 0.02 < oran < 0.25: score += 30
    if 1 < p24 < 10: score += 30
    if 0 < p1 < 2: score += 20
    if p1 > 0: score += 10

    return score

def run():
    if not saat_uygun_mu():
        print("Saat dışı, bekleniyor...")
        return

    state = load_state()
    seen = state["seen"]
    pre_seen = state["pre_seen"]

    coins = []
    for p in range(START_PAGE, END_PAGE+1):
        coins += veri(p)
        time.sleep(5)

    msg_pre = "🧠 PRE-ELITE RADAR\n\n"
    msg_elite = "💎 ELITE RADAR\n\n"

    for c in coins:
        if not uygun(c): continue

        s = skor(c)
        sym = c["symbol"].upper()

        if 60 <= s < 85:
            if sym not in pre_seen:
                pre_seen[sym] = 1
                msg_pre += f"{sym} | Skor:{s}\n"

        if s >= 85:
            if sym not in seen:
                seen[sym] = 1
                msg_elite += f"{sym} | Skor:{s}\n"

    if msg_pre.strip() != "🧠 PRE-ELITE RADAR":
        send(msg_pre)

    if msg_elite.strip() != "💎 ELITE RADAR":
        send(msg_elite)

    save_state({"seen": seen, "pre_seen": pre_seen})

while True:
    run()
    time.sleep(CHECK_INTERVAL)
    from flask import Flask
import threading

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot çalışıyor"

def run_web():
    app.run(host='0.0.0.0', port=10000)

threading.Thread(target=run_web).start()
