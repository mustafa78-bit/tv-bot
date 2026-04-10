import json
import os
import time
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

import requests

# =========================================================
# AYARLAR
# =========================================================
COINGECKO_API = "https://api.coingecko.com/api/v3"
TELEGRAM_API = "https://api.telegram.org"

BOT_TOKEN = "8763528906:AAE7rwoVLNfQJaLxkPvmGttBTtcx2Avntjs"
CHAT_ID = "1307136561"

CHECK_INTERVAL = 900  # 15 dakika
SLEEP_BETWEEN_CALLS = 1.2

RANK_MIN = 200
RANK_MAX = 500
TOP_CANDIDATES_LIMIT = 10
SEEN_FILE = "seen.json"

# Minimum radar kalitesi
MIN_TOTAL_SCORE = 60
MIN_FLOW_SCORE = 6

# Temel puan ağırlıkları
WEIGHTS = {
    "rank_score": 10,
    "narrative_score": 20,
    "support_score": 20,
    "social_score": 15,
    "team_score": 10,
    "flow_score": 15,
    "technical_score": 10,
}

# Aktif anlatılar / sektörler
ACTIVE_NARRATIVES = {
    "ai": 20,
    "artificial-intelligence": 20,
    "rwa": 18,
    "real-world-assets": 18,
    "depin": 18,
    "gaming": 14,
    "layer-2": 14,
    "defi": 12,
    "solana-ecosystem": 12,
    "ethereum-ecosystem": 10,
    "meme": 8,
}

# Güçlü destek sinyalleri
STRONG_SUPPORT_KEYWORDS = [
    "binance labs",
    "coinbase ventures",
    "animoca",
    "paradigm",
    "a16z",
    "andreessen horowitz",
    "multicoin",
    "polychain",
    "pantera",
    "hashkey",
    "okx ventures",
    "dragonfly",
    "framework ventures",
]

MID_SUPPORT_KEYWORDS = [
    "arbitrum",
    "optimism",
    "polygon",
    "solana foundation",
    "ethereum foundation",
    "google cloud",
    "aws",
    "chainlink",
    "consensys",
    "ava labs",
]

# Ekip / aktivite kelimeleri
TEAM_ACTIVE_KEYWORDS = [
    "partnership",
    "integration",
    "mainnet",
    "testnet",
    "launch",
    "roadmap",
    "update",
    "release",
    "upgrade",
    "collaboration",
]

# Bilinen ekip / advisor / etkili isimler
ELITE_NAMES = [
    "vitalik buterin",
    "changpeng zhao",
    "cz",
    "brian armstrong",
    "fred ehrsam",
    "balaji srinivasan",
    "naval ravikant",
    "sam altman",
    "sergey nazarov",
    "gavin wood",
    "anatoly yakovenko",
    "sandeep nailwal",
    "hayden adams",
    "stani kulechov",
    "andre cronje",
    "silvio micali",
    "daniele sestagalli",
    "arthur hayes",
    "david sacks",
    "chris dixon",
]

HEADERS = {
    "accept": "application/json",
    "user-agent": "gem-radar-final/1.0"
}

# =========================================================
# YARDIMCI
# =========================================================
def safe_get(url: str, params: Optional[Dict[str, Any]] = None) -> Any:
    try:
        r = requests.get(url, params=params, headers=HEADERS, timeout=25)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"[HATA] GET {url} -> {e}")
        return None


def send_telegram(message: str) -> bool:
    try:
        url = f"{TELEGRAM_API}/bot{BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": CHAT_ID,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }
        r = requests.post(url, json=payload, timeout=20)
        r.raise_for_status()
        return True
    except Exception as e:
        print(f"[HATA] Telegram gönderim -> {e}")
        return False


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def text_contains_any(text: str, keywords: List[str]) -> int:
    t = (text or "").lower()
    return sum(1 for kw in keywords if kw in t)


def load_seen() -> Dict[str, Any]:
    if not os.path.exists(SEEN_FILE):
        return {"coins": {}}
    try:
        with open(SEEN_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"coins": {}}


def save_seen(data: Dict[str, Any]) -> None:
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def now_str() -> str:
    return datetime.now().strftime("%d.%m.%Y %H:%M")


def pct(v: Optional[float]) -> float:
    return float(v) if v is not None else 0.0


def human_price(price: Optional[float]) -> str:
    if price is None:
        return "?"
    if price >= 1:
        return f"${price:,.4f}"
    if price >= 0.01:
        return f"${price:,.6f}"
    return f"${price:,.8f}"


def normalize_name(name: str) -> str:
    return " ".join(word.capitalize() for word in name.split())


# =========================================================
# COINGECKO VERİ
# =========================================================
def fetch_rank_range_coins(rank_min: int, rank_max: int) -> List[Dict[str, Any]]:
    results = []
    per_page = 250

    start_page = ((rank_min - 1) // per_page) + 1
    end_page = ((rank_max - 1) // per_page) + 1

    for page in range(start_page, end_page + 1):
        data = safe_get(
            f"{COINGECKO_API}/coins/markets",
            params={
                "vs_currency": "usd",
                "order": "market_cap_desc",
                "per_page": per_page,
                "page": page,
                "sparkline": "false",
                "price_change_percentage": "1h,24h,7d",
            },
        )
        time.sleep(SLEEP_BETWEEN_CALLS)

        if not data:
            continue

        for coin in data:
            rank = coin.get("market_cap_rank")
            if rank is not None and rank_min <= rank <= rank_max:
                results.append(coin)

    return results


def fetch_coin_details(coin_id: str) -> Dict[str, Any]:
    data = safe_get(
        f"{COINGECKO_API}/coins/{coin_id}",
        params={
            "localization": "false",
            "tickers": "false",
            "market_data": "false",
            "community_data": "true",
            "developer_data": "true",
            "sparkline": "false",
        },
    )
    time.sleep(SLEEP_BETWEEN_CALLS)
    return data or {}


# =========================================================
# METİN BİRLEŞTİRME
# =========================================================
def build_text_blob(coin: Dict[str, Any], details: Dict[str, Any]) -> str:
    categories = " ".join(details.get("categories", []) or [])
    links = details.get("links", {}) or {}
    homepage = " ".join([x for x in links.get("homepage", []) if x])
    blockchain_site = " ".join([x for x in links.get("blockchain_site", []) if x])
    repos = " ".join((links.get("repos_url", {}) or {}).get("github", []) or [])
    description = ((details.get("description", {}) or {}).get("en") or "")
    name = coin.get("name", "")
    symbol = coin.get("symbol", "")
    blob = " ".join([name, symbol, categories, homepage, blockchain_site, repos, description])
    return blob.lower()


# =========================================================
# DESTEKÇİ ANALİZİ
# =========================================================
def classify_supporters(text_blob: str) -> Tuple[List[str], str, int]:
    found_strong = []
    found_mid = []

    for kw in STRONG_SUPPORT_KEYWORDS:
        if kw in text_blob:
            found_strong.append(normalize_name(kw))

    for kw in MID_SUPPORT_KEYWORDS:
        if kw in text_blob:
            found_mid.append(normalize_name(kw))

    supporters = []
    supporters.extend([f"🟢 {x}" for x in sorted(set(found_strong))])
    supporters.extend([f"🟡 {x}" for x in sorted(set(found_mid))])

    raw_score = len(set(found_strong)) * 10 + len(set(found_mid)) * 5
    score = int(clamp(raw_score, 0, 20))

    if score >= 15:
        level = "STRONG"
    elif score >= 6:
        level = "MID"
    else:
        level = "WEAK"

    return supporters, level, score


# =========================================================
# EKİP / BİLİNEN İSİM ANALİZİ
# =========================================================
def classify_elite_team(text_blob: str) -> Tuple[List[str], str, int]:
    found = []

    for name in ELITE_NAMES:
        if name in text_blob:
            display = "CZ" if name == "cz" else normalize_name(name)
            found.append(display)

    found = sorted(set(found))
    tagged = []

    if len(found) >= 2:
        for n in found:
            tagged.append(f"🟢 {n}")
        level = "STRONG"
        score = 10
    elif len(found) == 1:
        tagged.append(f"🟡 {found[0]}")
        level = "MID"
        score = 6
    else:
        level = "WEAK"
        score = 0

    return tagged, level, score


# =========================================================
# PUANLAMA
# =========================================================
def score_rank(rank: Optional[int]) -> int:
    if rank is None:
        return 0
    if 200 <= rank <= 260:
        return 10
    if 261 <= rank <= 340:
        return 8
    if 341 <= rank <= 420:
        return 6
    if 421 <= rank <= 500:
        return 4
    return 0


def score_narrative(details: Dict[str, Any], text_blob: str) -> Tuple[int, List[str]]:
    categories = [c.lower() for c in (details.get("categories", []) or [])]
    found_tags = []
    best = 0

    for tag, value in ACTIVE_NARRATIVES.items():
        if tag in categories or tag in text_blob:
            found_tags.append(tag)
            best = max(best, value)

    found_tags = sorted(set(found_tags))
    score = int(clamp(best, 0, 20))
    return score, found_tags[:5]


def score_social(details: Dict[str, Any]) -> Tuple[int, str]:
    c = details.get("community_data", {}) or {}
    twitter = c.get("twitter_followers") or 0
    reddit = c.get("reddit_subscribers") or 0
    telegram_avg = c.get("telegram_channel_user_count") or 0

    raw = 0
    if twitter >= 300000:
        raw += 8
    elif twitter >= 100000:
        raw += 6
    elif twitter >= 30000:
        raw += 4
    elif twitter >= 10000:
        raw += 2

    if reddit >= 50000:
        raw += 4
    elif reddit >= 10000:
        raw += 2

    if telegram_avg >= 50000:
        raw += 3
    elif telegram_avg >= 10000:
        raw += 1

    score = int(clamp(raw, 0, 15))

    if score >= 10:
        label = "Güçlü"
    elif score >= 5:
        label = "Orta"
    elif score >= 1:
        label = "Zayıf+"
    else:
        label = "Zayıf"

    return score, label


def score_team_activity(details: Dict[str, Any], text_blob: str) -> Tuple[int, str]:
    d = details.get("developer_data", {}) or {}

    forks = d.get("forks") or 0
    stars = d.get("stars") or 0
    subscribers = d.get("subscribers") or 0
    commits_4w = d.get("commit_count_4_weeks") or 0
    activity_hits = text_contains_any(text_blob, TEAM_ACTIVE_KEYWORDS)

    raw = 0
    if commits_4w >= 80:
        raw += 5
    elif commits_4w >= 20:
        raw += 3
    elif commits_4w >= 5:
        raw += 1

    if stars >= 1000:
        raw += 2
    elif stars >= 300:
        raw += 1

    if forks >= 150:
        raw += 1

    if subscribers >= 50:
        raw += 1

    if activity_hits >= 2:
        raw += 2
    elif activity_hits >= 1:
        raw += 1

    score = int(clamp(raw, 0, 10))

    if score >= 8:
        label = "Çok Aktif"
    elif score >= 5:
        label = "Aktif"
    elif score >= 2:
        label = "Orta"
    else:
        label = "Zayıf"

    return score, label


def score_flow(coin: Dict[str, Any]) -> Tuple[int, str, float]:
    market_cap = coin.get("market_cap") or 0
    total_volume = coin.get("total_volume") or 0
    p1h = pct(coin.get("price_change_percentage_1h_in_currency"))
    p24h = pct(coin.get("price_change_percentage_24h_in_currency"))
    p7d = pct(coin.get("price_change_percentage_7d_in_currency"))

    vol_mcap = (total_volume / market_cap) if market_cap > 0 else 0.0

    raw = 0
    if vol_mcap >= 0.20:
        raw += 7
    elif vol_mcap >= 0.10:
        raw += 5
    elif vol_mcap >= 0.05:
        raw += 3
    elif vol_mcap >= 0.03:
        raw += 1

    if p1h > 0:
        raw += 2
    if p24h > 2:
        raw += 3
    elif p24h > 0:
        raw += 1

    if p7d > 5:
        raw += 3
    elif p7d > 0:
        raw += 1

    score = int(clamp(raw, 0, 15))

    if score >= 11:
        label = "Güçlü"
    elif score >= 7:
        label = "Canlı"
    elif score >= 4:
        label = "Orta"
    else:
        label = "Zayıf"

    return score, label, vol_mcap


def score_technical(coin: Dict[str, Any]) -> Tuple[int, str, bool]:
    p1h = pct(coin.get("price_change_percentage_1h_in_currency"))
    p24h = pct(coin.get("price_change_percentage_24h_in_currency"))
    p7d = pct(coin.get("price_change_percentage_7d_in_currency"))

    raw = 0
    fake_pump = False

    if p1h > 0:
        raw += 2
    if 0 < p24h <= 12:
        raw += 4
    elif p24h > 12:
        raw += 1
        fake_pump = True

    if p7d > 0:
        raw += 2
    if p24h > 0 and p7d > 0:
        raw += 2

    if p24h > 18 or (p1h > 4 and p24h > 10):
        fake_pump = True

    score = int(clamp(raw, 0, 10))

    if fake_pump:
        label = "Fake Riski"
    elif score >= 8:
        label = "Uygun"
    elif score >= 5:
        label = "İzlenir"
    else:
        label = "Zayıf"

    return score, label, fake_pump


# =========================================================
# TOPLAM DEĞERLENDİRME
# =========================================================
def evaluate_coin(coin: Dict[str, Any]) -> Dict[str, Any]:
    details = fetch_coin_details(coin["id"])
    text_blob = build_text_blob(coin, details)

    rank_score = score_rank(coin.get("market_cap_rank"))
    narrative_score, narratives = score_narrative(details, text_blob)
    supporters, support_level, support_score = classify_supporters(text_blob)
    elite_team, elite_team_level, elite_team_score = classify_elite_team(text_blob)
    social_score, social_label = score_social(details)
    team_score_base, team_label = score_team_activity(details, text_blob)
    flow_score, flow_label, vol_mcap = score_flow(coin)
    technical_score, technical_label, fake_pump = score_technical(coin)

    # Bilinen isim varsa ekip puanını biraz güçlendir
    team_score = int(clamp(team_score_base + elite_team_score, 0, 10))

    weighted_total = (
        (rank_score / 10) * WEIGHTS["rank_score"] +
        (narrative_score / 20) * WEIGHTS["narrative_score"] +
        (support_score / 20) * WEIGHTS["support_score"] +
        (social_score / 15) * WEIGHTS["social_score"] +
        (team_score / 10) * WEIGHTS["team_score"] +
        (flow_score / 15) * WEIGHTS["flow_score"] +
        (technical_score / 10) * WEIGHTS["technical_score"]
    )

    total_score = int(round(clamp(weighted_total, 0, 100)))

    if fake_pump and total_score >= 10:
        total_score -= 10

    if support_level == "STRONG" and total_score <= 95:
        total_score += 3

    total_score = int(clamp(total_score, 0, 100))

    return {
        "id": coin["id"],
        "symbol": (coin.get("symbol") or "").upper(),
        "name": coin.get("name"),
        "rank": coin.get("market_cap_rank"),
        "price": coin.get("current_price"),
        "p1h": pct(coin.get("price_change_percentage_1h_in_currency")),
        "p24h": pct(coin.get("price_change_percentage_24h_in_currency")),
        "p7d": pct(coin.get("price_change_percentage_7d_in_currency")),
        "market_cap": coin.get("market_cap"),
        "volume": coin.get("total_volume"),
        "vol_mcap": vol_mcap,

        "rank_score": rank_score,
        "narrative_score": narrative_score,
        "support_score": support_score,
        "social_score": social_score,
        "team_score": team_score,
        "flow_score": flow_score,
        "technical_score": technical_score,
        "total_score": total_score,

        "narratives": narratives,
        "supporters": supporters,
        "support_level": support_level,
        "elite_team": elite_team,
        "elite_team_level": elite_team_level,
        "social_label": social_label,
        "team_label": team_label,
        "flow_label": flow_label,
        "technical_label": technical_label,
        "fake_pump": fake_pump,
    }


def is_trade_candidate(c: Dict[str, Any]) -> bool:
    return (
        c["total_score"] >= MIN_TOTAL_SCORE and
        c["flow_score"] >= MIN_FLOW_SCORE and
        c["p24h"] > 0 and
        c["rank"] is not None and
        RANK_MIN <= c["rank"] <= RANK_MAX
    )


# =========================================================
# MESAJ
# =========================================================
def support_lines(c: Dict[str, Any]) -> str:
    if c["supporters"]:
        return "\n".join(c["supporters"][:5])
    return "🔴 Bilinen güçlü destekçi bulunamadı"


def team_lines(c: Dict[str, Any]) -> str:
    if c["elite_team"]:
        return "\n".join(c["elite_team"][:5])
    return "🔴 Bilinen ekip / advisor ismi bulunamadı"


def narrative_line(c: Dict[str, Any]) -> str:
    if not c["narratives"]:
        return "Zayıf / Belirsiz"
    tags = ", ".join(x.upper() for x in c["narratives"][:3])
    if c["narrative_score"] >= 15:
        return f"Güçlü ({tags})"
    if c["narrative_score"] >= 8:
        return f"Orta ({tags})"
    return f"Zayıf ({tags})"


def overall_decision(c: Dict[str, Any]) -> str:
    if c["fake_pump"]:
        return "→ UZAK DUR / FAKE RİSK"
    if c["total_score"] >= 85 and c["flow_score"] >= 10:
        return "→ ELITE TAKİP"
    if c["total_score"] >= 70:
        return "→ TRADE ADAYI"
    return "→ İZLE"

def build_message(c: Dict[str, Any], first_seen: bool) -> str:
    header = "🆕 <b>İLK KEZ RADAR</b>" if first_seen else "💎 <b>GEM RADAR</b>"
    fake_line = "\n⚠️ <b>Fake Pump Riski:</b> Var" if c["fake_pump"] else ""

    msg = (
        f"{header}\n"
        f"🕒 {now_str()}\n\n"
        f"🚀 <b>{c['symbol']}</b> ({c['name']})\n"
        f"🏅 Rank: {c['rank']}\n"
        f"💰 Fiyat: {human_price(c['price'])}\n"
        f"📊 Skor: <b>{c['total_score']}/100</b>\n\n"

        f"🧠 <b>DESTEKÇİLER</b>\n"
        f"{support_lines(c)}\n"
        f"📌 Destek Gücü: <b>{c['support_level']}</b>\n\n"

        f"👨‍💻 <b>EKİP / BİLİNEN İSİMLER</b>\n"
        f"{team_lines(c)}\n"
        f"📌 Ekip Gücü: <b>{c['elite_team_level']}</b>\n\n"

        f"📚 <b>TEMEL</b>\n"
        f"• Narrative: {narrative_line(c)}\n"
        f"• Sosyal: {c['social_label']}\n"
        f"• Aktivite: {c['team_label']}\n"
        f"• Para Akışı: {c['flow_label']} (Vol/MCap: {c['vol_mcap']:.2f})\n\n"

        f"📈 <b>TEKNİK</b>\n"
        f"• 1s: {c['p1h']:.2f}%\n"
        f"• 24s: {c['p24h']:.2f}%\n"
        f"• 7g: {c['p7d']:.2f}%\n"
        f"• Teknik Durum: {c['technical_label']}\n"
        f"{fake_line}\n\n"

        f"🎯 <b>SONUÇ</b>\n"
        f"{overall_decision(c)}"
    )

    return msg


def build_summary(top_items: List[Dict[str, Any]]) -> str:
    lines = []
    for c in top_items[:5]:
        lines.append(
            f"• {c['symbol']} | Rank {c['rank']} | "
            f"Skor {c['total_score']} | 24s {c['p24h']:.2f}%"
        )

    body = "\n".join(lines) if lines else "Uygun coin bulunamadı."

    return (
        f"💎 <b>GEM RADAR ÖZET</b>\n"
        f"🕒 {now_str()}\n\n"
        f"{body}"
    )


# =========================================================
# ANA AKIŞ
# =========================================================
def run_once() -> None:
    print(f"[{now_str()}] Tarama başladı...")
    seen = load_seen()
    seen_coins = seen.setdefault("coins", {})

    market_coins = fetch_rank_range_coins(RANK_MIN, RANK_MAX)
    print(f"Bulunan coin sayısı: {len(market_coins)}")

    evaluated: List[Dict[str, Any]] = []

    for i, coin in enumerate(market_coins, start=1):
        try:
            print(f"[{i}/{len(market_coins)}] İşleniyor: {coin.get('symbol', '').upper()}")
            result = evaluate_coin(coin)

            if is_trade_candidate(result):
                evaluated.append(result)

        except Exception as e:
            print(f"[HATA] Coin işleme {coin.get('id')} -> {e}")

    evaluated.sort(key=lambda x: (x["total_score"], x["flow_score"], x["p24h"]), reverse=True)
    selected = evaluated[:TOP_CANDIDATES_LIMIT]

    print(f"Radar adayı: {len(selected)}")

    sent_count = 0

    for c in selected:
        coin_key = c["id"]
        old = seen_coins.get(coin_key, {})
        old_score = old.get("score", 0)
        first_seen = coin_key not in seen_coins

        # Spam azaltma:
        # yeni coin ise gönder
        # veya skor ciddi arttıysa gönder
        should_send = first_seen or c["total_score"] >= old_score + 8

        if should_send:
            msg = build_message(c, first_seen=first_seen)
            ok = send_telegram(msg)
            if ok:
                sent_count += 1
                time.sleep(1.0)

        seen_coins[coin_key] = {
            "symbol": c["symbol"],
            "score": c["total_score"],
            "last_seen_at": now_str(),
            "rank": c["rank"],
        }

    if selected:
        summary_msg = build_summary(selected)
        send_telegram(summary_msg)

    save_seen(seen)
    print(f"[{now_str()}] Tarama bitti. Gönderilen mesaj: {sent_count}")


def main() -> None:
    print("GEM RADAR FINAL başladı.")
    while True:
        try:
            run_once()
        except Exception as e:
            print(f"[KRITIK HATA] {e}")

        print(f"{CHECK_INTERVAL} saniye bekleniyor...")
        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
