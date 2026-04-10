import requests
from bs4 import BeautifulSoup
from datetime import datetime

# ✅ BURAYA DİREKT YAZ (TEST İÇİN)
BOT_TOKEN = "8735115726:AAHVB0gR_z-Qyzs-ot99ilbDmr_D9tmoIt4"
CHAT_ID = "1307136561"

KEYWORDS = ["list", "listing", "will list", "new listing"]

SOURCES = [
    ("BINANCE", "https://www.binance.com/en/support/announcement/list/48"),
    ("BYBIT", "https://announcements.bybit.com/en/?category=new_crypto"),
    ("OKX", "https://www.okx.com/help/section/announcements-new-listings"),
]

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


def send_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": CHAT_ID,
        "text": message
    }
    r = requests.post(url, data=data)
    print("Telegram status:", r.status_code)


def is_listing(title):
    return any(k in title.lower() for k in KEYWORDS)


def fetch(url, base, name):
    items = []
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")

        for a in soup.find_all("a", href=True):
            title = a.get_text(strip=True)
            link = a["href"]

            if len(title) < 10:
                continue

            if not link.startswith("http"):
                link = base + link

            if is_listing(title):
                items.append((name, title, link))
    except Exception as e:
        print(name, "hata:", e)

    return items[:3]


def main():
    print("Checking listing news...")

    data = []
    data += fetch(SOURCES[0][1], "https://www.binance.com", "BINANCE")
    data += fetch(SOURCES[1][1], "https://announcements.bybit.com", "BYBIT")
    data += fetch(SOURCES[2][1], "https://www.okx.com", "OKX")

    now = datetime.now().strftime("%d.%m.%Y %H:%M")

    if not data:
        msg = f"📭 Listing yok\n🕒 {now}"
    else:
        msg = f"🚨 LISTING NEWS\n🕒 {now}\n\n"
        for s, t, l in data:
            msg += f"{s}\n{t}\n{l}\n\n"

    send_telegram(msg)
    print("Bitti.")


if __name__ == "__main__":
    main()