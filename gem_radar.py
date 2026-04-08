import requests
import time
import os
import json
import threading
from datetime import datetime, timedelta
from flask import Flask

# =========================
# TELEGRAM
# =========================
import os

BOT_TOKEN = os.getenv("8763528906:AAE7rwoVLNfQJaLxkPvmGttBTtcx2Avntjs")
CHAT_ID = os.getenv("1307136561")

# =========================
# SAAT AYARLARI
# =========================
START_HOUR = 8
END_HOUR = 22

# Çalışma saatinde tarama aralığı (saniye)
ACTIVE_SLEEP = 7200   # 2 saat

# Çalışma saati dışı kontrol aralığı
SLEEP_MODE = 300      # 5 dakika

# =========================
# COINGECKO SAYFA AYARLARI
# =========================
START_PAGE = 2
END_PAGE = 6
PER_PAGE = 100

# =========================
# DOSYA
# =========================
STATE_FILE = "state.json"

# =========================
# FLASK
# =========================
app = Flask(__name__)

@app.route("/")
def home():
    return "Gem radar aktif"

# =========================
# REQUEST SESSION
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
    if not BOT_TOKEN or not CHAT_ID or "BURAYA_" in BOT_TOKEN or "BURAYA_" in CHAT_ID:
        print("Telegram ayarları eksik")
        return

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": CHAT_ID,
        "text": text
    }

    try:
        r = requests.post(url, data=data, timeout=20)
        print("Telegram status:", r.status_code, r.text[:200])
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
    except Exception as e:
        print("State okuma hatası:", e)
        return {"seen": {}, "pre_seen": {}}

def save_state(state):
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("State yazma hatası:", e)

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
        "price_change_percentage": "1h,24h,7d"
    }

    try:
        r = session.get(url, params=params, timeout=25)

        if r.status_code == 200:
            return r.json()

        if r.status_code == 429:
            print("Rate limit, bekleniyor...")
            time.sleep(20)
            return []

        print("HTTP hata:", r.status_code, r.text[:200])
        return []

    except Exception as e:
        print("İstek hatası:", e)
        return []

def get_all_data():
    coins = []
    for page in range(START_PAGE, END_PAGE + 1):
        data = get_page(page)
        if data:
            coins.extend(data)
        time.sleep(4)
    return coins

# =========================
# FİLTRELER
# =========================
def base_filter(c):
    rank = c.get("market_cap_rank") or 9999
    vol = c.get("total_volume") or 0
    mc = c.get("market_cap") or 1
    p1h = c.get("price_change_percentage_1h_in_currency") or 0
    p24 = c.get("price_change_percentage_24h_in_currency") or 0
    p7d = c.get("price_change_percentage_7d_in_currency") or 0
    vol_ratio = vol / mc if mc > 0 else 0

    if rank < 200 or rank > 600:
        return False
    if vol < 4_000_000:
        return False
    if vol_ratio < 0.02:
        return False
    if p24 < -8 or p24 > 14:
        return False
    if p7d < -25 or p7d > 40:
        return False
    if p1h < -2.5:
        return False

    return True

def elite_filter(c):
    p1h = c.get("price_change_percentage_1h_in_currency") or 0
    p24 = c.get("price_change_percentage_24h_in_currency") or 0

    if p1h < 0.2 or p1h > 3.5:
        return False
    if p24 > 12:
        return False

    return True

def pre_elite_filter(c):
    p1h = c.get("price_change_percentage_1h_in_currency") or 0
    p24 = c.get("price_change_percentage_24h_in_currency") or 0
    vol = c.get("total_volume") or 0

    if vol < 5_000_000:
        return False
    if not (0.05 <= p1h <= 0.8):
        return False
    if not (0.5 <= p24 <= 5.0):
        return False

    return True

# =========================
# SKOR
# =========================
def score_coin(c):
    score = 0

    rank = c.get("market_cap_rank") or 9999
    vol = c.get("total_volume") or 0
    mc = c.get("market_cap") or 1
    p1h = c.get("price_change_percentage_1h_in_currency") or 0
    p24 = c.get("price_change_percentage_24h_in_currency") or 0
    p7d = c.get("price_change_percentage_7d_in_currency") or 0
    vol_ratio = vol / mc if mc > 0 else 0

    if 220 <= rank <= 450:
        score += 20
    elif 200 <= rank <= 520:
        score += 12

    if 0.04 <= vol_ratio <= 0.18:
        score += 25
    elif 0.02 <= vol_ratio < 0.04:
        score += 12

    if 2 <= p24 <= 9:
        score += 20
    elif 0.5 <= p24 < 2:
        score += 10
    elif 9 < p24 <= 12:
        score += 6

    if 0.3 <= p1h <= 2.5:
        score += 15
    elif 0.05 <= p1h < 0.3:
        score += 8

    if -5 <= p7d <= 18:
        score += 10
    elif -10 <= p7d < -5:
        score += 5

    if vol >= 10_000_000:
        score += 10

    return score

def pre_score_coin(c):
    score = 0

    rank = c.get("market_cap_rank") or 9999
    vol = c.get("total_volume") or 0
    mc = c.get("market_cap") or 1
    p1h = c.get("price_change_percentage_1h_in_currency") or 0
    p24 = c.get("price_change_percentage_24h_in_currency") or 0
    vol_ratio = vol / mc if mc > 0 else 0

    if 220 <= rank <= 500:
        score += 20
    if 0.03 <= vol_ratio <= 0.15:
        score += 25
    if 0.5 <= p24 <= 4.5:
        score += 20
    if 0.05 <= p1h <= 0.8:
        score += 20
    if vol >= 8_000_000:
        score += 10

    return score

def heat_label(score):
    if score >= 92:
        return "🔴 Patlamak Üzere"
    if score >= 85:
        return "🟠 Isınıyor"
    return "🟡 Takip"

# =========================
# MESAJLAR
# =========================
def build_pre_message(selected, state):
    msg = f"🧠 PRE-ELITE RADAR\n🕒 {tr_str()}\n\n"

    if not selected:
        msg += "Uygun coin yok"
        return msg

    lines = []
    for c, score in selected[:5]:
        coin_id = c.get("id")
        symbol = (c.get("symbol") or "").upper()
        rank = c.get("market_cap_rank") or 0
        p1h = c.get("price_change_percentage_1h_in_currency") or 0
        p24 = c.get("price_change_percentage_24h_in_currency") or 0
        price = c.get("current_price") or 0
        first_seen = coin_id not in state["pre_seen"]

        tag = "🆕 İLK PRE-ELITE" if first_seen else "📡 PRE-ELITE"

        lines.append(
            f"{tag}\n"
            f"{symbol}\n"
            f"Rank: {rank}\n"
            f"Fiyat: ${price:.6f}\n"
            f"1s: {p1h:.2f}%\n"
            f"24s: {p24:.2f}%\n"
            f"Skor: {score}\n"
        )

        state["pre_seen"][coin_id] = {
            "symbol": symbol,
            "last_score": score,
            "last_seen": tr_str()
        }

    msg += "\n".join(lines)
    return msg

def build_elite_message(selected, state):
    msg = f"💎 OMEGA ELITE GEM RADAR\n🕒 {tr_str()}\n\n"

    if not selected:
        msg += "Uygun coin yok"
        return msg

    lines = []
    for c, score in selected[:8]:
        coin_id = c.get("id")
        symbol = (c.get("symbol") or "").upper()
        rank = c.get("market_cap_rank") or 0
        p1h = c.get("price_change_percentage_1h_in_currency") or 0
        p24 = c.get("price_change_percentage_24h_in_currency") or 0
        price = c.get("current_price") or 0
        first_seen = coin_id not in state["seen"]

        if score >= 92 and first_seen:
            level = "💥 İLK KEZ ELITE"
        elif score >= 92:
            level = "⚡ DOUBLE ALERT"
        elif score >= 85 and first_seen:
            level = "🧠 YENİ GİRDİ"
        else:
            level = "📡 RADAR"

        lines.append(
            f"{level}\n"
            f"{symbol}\n"
            f"Heat: {heat_label(score)}\n"
            f"Rank: {rank}\n"
            f"Fiyat: ${price:.6f}\n"
            f"1s: {p1h:.2f}%\n"
            f"24s: {p24:.2f}%\n"
            f"Skor: {score}\n"
        )

        state["seen"][coin_id] = {
            "symbol": symbol,
            "last_score": score,
            "last_seen": tr_str()
        }

    msg += "\n".join(lines)
    return msg

# =========================
# ANALİZ
# =========================
def analyze():
    print("Tarama başladı...")
    coins = get_all_data()

    if not coins:
        print("Veri gelmedi")
        return

    state = load_state()
    elite_selected = []
    pre_selected = []

    for c in coins:
        if not base_filter(c):
            continue

        if pre_elite_filter(c):
            pre_sc = pre_score_coin(c)
            if pre_sc >= 75:
                pre_selected.append((c, pre_sc))

        if elite_filter(c):
            sc = score_coin(c)
            if sc >= 85:
                elite_selected.append((c, sc))

    elite_selected.sort(key=lambda x: x[1], reverse=True)
    pre_selected.sort(key=lambda x: x[1], reverse=True)

    elite_message = build_elite_message(elite_selected, state)
    pre_message = build_pre_message(pre_selected, state)

    print(elite_message)
    send_telegram(elite_message)

    if pre_selected:
        print(pre_message)
        send_telegram(pre_message)

    save_state(state)

# =========================
# BOT LOOP
# =========================
def radar_loop():
    while True:
        try:
            hour = tr_now().hour
            print(f"Şu an saat: {hour}")

            if START_HOUR <= hour < END_HOUR:
                print("Çalışma saatinde")
                analyze()
                print("2 saat bekleniyor...\n")
                time.sleep(ACTIVE_SLEEP)
            else:
                print("Uyku modu\n")
                time.sleep(SLEEP_MODE)

        except Exception as e:
            print("Genel hata:", e)
            time.sleep(60)

# =========================
# MAIN
# =========================
if __name__ == "__main__":
    threading.Thread(target=radar_loop, daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
