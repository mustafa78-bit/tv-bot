import requests
import time
import threading
import os
from datetime import datetime, timedelta
from flask import Flask

# =========================
# TELEGRAM
# =========================
BOT_TOKEN = "8763528906:AAE7rwoVLNfQJaLxkPvmGttBTtcx2Avntjs"
CHAT_ID = "1307136561"

# =========================
# AYARLAR
# =========================
START_HOUR = 8
END_HOUR = 22
ACTIVE_SLEEP = 7200
SLEEP_MODE = 300

START_PAGE = 2
END_PAGE = 6
PER_PAGE = 100

app = Flask(__name__)

@app.route("/")
def home():
    return "GEM RADAR AKTIF"

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
# TELEGRAM GÖNDER
# =========================
def send_telegram(text):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        data = {
            "chat_id": CHAT_ID,
            "text": text
        }
        r = requests.post(url, data=data, timeout=20)
        print("Telegram:", r.status_code, r.text[:200])
    except Exception as e:
        print("Telegram hata:", e)

# =========================
# COINGECKO
# =========================
def get_page(page):
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
        print("CoinGecko hata:", r.status_code)
        return []
    except Exception as e:
        print("CoinGecko exception:", e)
        return []

def get_all_data():
    coins = []
    for page in range(START_PAGE, END_PAGE + 1):
        coins += get_page(page)
        time.sleep(2)
    return coins

# =========================
# FİLTRE
# =========================
def filter_coin(c):
    rank = c.get("market_cap_rank") or 9999
    vol = c.get("total_volume") or 0
    mc = c.get("market_cap") or 1
    p1h = c.get("price_change_percentage_1h_in_currency") or 0
    p24 = c.get("price_change_percentage_24h_in_currency") or 0

    if rank < 200 or rank > 600:
        return False
    if vol < 4_000_000:
        return False
    if (vol / mc) < 0.02:
        return False
    if p24 < -8 or p24 > 14:
        return False
    if p1h < -2:
        return False

    return True

# =========================
# SKOR
# =========================
def score(c):
    s = 0
    p1h = c.get("price_change_percentage_1h_in_currency") or 0
    p24 = c.get("price_change_percentage_24h_in_currency") or 0
    vol = c.get("total_volume", 0)
    rank = c.get("market_cap_rank") or 9999

    if 0.3 <= p1h <= 2.5:
        s += 40
    if 2 <= p24 <= 10:
        s += 30
    if vol > 10_000_000:
        s += 20
    if 220 <= rank <= 450:
        s += 10

    return s

# =========================
# ANALİZ
# =========================
def analyze():
    print("Tarama başladı...")
    coins = get_all_data()
    selected = []

    for c in coins:
        if not filter_coin(c):
            continue
        sc = score(c)
        if sc >= 70:
            selected.append((c, sc))

    selected.sort(key=lambda x: x[1], reverse=True)

    if not selected:
        print("Uygun coin yok")
        return

    msg = f"💎 GEM RADAR\n🕒 {tr_str()}\n\n"

    for c, sc in selected[:5]:
        symbol = (c.get("symbol") or "").upper()
        price = c.get("current_price") or 0
        rank = c.get("market_cap_rank") or 0
        p1h = c.get("price_change_percentage_1h_in_currency") or 0
        p24 = c.get("price_change_percentage_24h_in_currency") or 0

        msg += (
            f"{symbol}\n"
            f"Rank: {rank}\n"
            f"Fiyat: ${price:.6f}\n"
            f"1s: {p1h:.2f}%\n"
            f"24s: {p24:.2f}%\n"
            f"Skor: {sc}\n\n"
        )

    print(msg)
    send_telegram(msg)

# =========================
# LOOP
# =========================
def radar_loop():
    send_telegram("🚀 GEM RADAR AKTIF - sistem çalışıyor")

    while True:
        try:
            hour = tr_now().hour
            print("Saat:", hour)

            if START_HOUR <= hour < END_HOUR:
                analyze()
                print(f"{ACTIVE_SLEEP} saniye bekleniyor...")
                time.sleep(ACTIVE_SLEEP)
            else:
                print("Uyku modu...")
                time.sleep(SLEEP_MODE)

        except Exception as e:
            print("Genel hata:", e)
            send_telegram(f"⚠️ GEM RADAR HATA: {e}")
            time.sleep(60)

# =========================
# MAIN
# =========================
if __name__ == "__main__":
    threading.Thread(target=radar_loop, daemon=True).start()
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
