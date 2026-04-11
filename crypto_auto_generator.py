"""
🪙 크립토 자동 기사 생성기 v1.0
═══════════════════════════════════════
CryptoYuna 스타일로 크립토 뉴스를 자동 생성하고
텍스트 + 이미지를 바로 올릴 수 있는 형태로 제공합니다.

사용법: streamlit run crypto_auto_generator.py
"""

import streamlit as st
import feedparser
from deep_translator import GoogleTranslator
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import time
import re
import html
import requests
from bs4 import BeautifulSoup
from collections import Counter
import urllib.parse
import json
import tempfile
import os
import hashlib
import shutil
from pathlib import Path

# ─────────────────────────────────────────────
#  설정
# ─────────────────────────────────────────────
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# 출력 폴더 (기본값 — UI에서 변경 가능)
DEFAULT_OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "생성된_기사")

# ─────────────────────────────────────────────
#  RSS 피드 목록
# ─────────────────────────────────────────────
RSS_FEEDS = {
    # ── 크립토 전문 미디어 ──
    "🟠 CoinDesk":        "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "📰 Cointelegraph":   "https://cointelegraph.com/rss",
    "🟣 Decrypt":         "https://decrypt.co/feed",
    "🔵 CryptoNews":      "https://cryptonews.com/news/feed/",
    "⚡ Bitcoin Magazine": "https://bitcoinmagazine.com/.rss/full/",
    "📊 The Block":       "https://www.theblock.co/rss.xml",
    "🌏 Wu Blockchain":   "https://www.wu-blockchain.com/feed",
    "🪨 CryptoSlate":     "https://cryptoslate.com/feed/",
    "📡 BeInCrypto":      "https://beincrypto.com/feed/",
    # ── 기관/ETF/월스트리트 ──
    "📈 Blockworks":      "https://blockworks.co/feed",
    "🏦 DL News":         "https://www.dlnews.com/arc/outboundfeeds/rss/",
    "💹 CNBC Crypto":     "https://www.cnbc.com/id/10001147/device/rss/rss.html",
    # ── 온체인/데이터 ──
    "🐋 Whale Alert Blog": "https://whale-alert.io/feed",
    "📉 Glassnode Blog":  "https://insights.glassnode.com/rss/",
    "🦎 CoinGecko Blog":  "https://blog.coingecko.com/feed/",
    # ── 리서치/DeFi ──
    "🔬 Messari":         "https://messari.io/rss",
    "🛡️ The Defiant":     "https://thedefiant.io/api/feed",
    "📚 Coin Bureau":     "https://coinbureau.com/feed/",
    # ── 속보 전문 ──
    "🔔 Watcher.Guru":    "https://watcher.guru/news/feed",
    "🦅 CryptoPanic":     "https://cryptopanic.com/news/rss/",
    # ── 한국 미디어 ──
    "🇰🇷 블록미디어":      "https://www.blockmedia.co.kr/feed/",
    "🇰🇷 디지털투데이":    "https://www.digitaltoday.co.kr/rss/allArticle.xml",
    "🇰🇷 코인리더스":     "http://www.coinreaders.com/rss/allArticle.xml",
}

KOREAN_FEEDS = {"🇰🇷 블록미디어", "🇰🇷 디지털투데이", "🇰🇷 코인리더스"}

# ─────────────────────────────────────────────
#  Nitter 인스턴스 (X 피드 프록시)
# ─────────────────────────────────────────────
NITTER_INSTANCES = [
    "https://xcancel.com",
    "https://nitter.poast.org",
    "https://nitter.privacydev.net",
]

# ─────────────────────────────────────────────
#  X 인플루언서 계정 (Nitter RSS로 수집)
# ─────────────────────────────────────────────
X_INFLUENCERS = {
    # ── 속보/뉴스 계정 (CryptoYuna 주요 소스) ──
    "🔔 Watcher Guru":      "WatcherGuru",
    "📊 Tier10k (db)":      "tier10k",
    "🐳 Whale Alert":       "whale_alert",
    "🦅 ZachXBT":           "zachxbt",
    # ── BTC 강세 인플루언서 (CryptoYuna가 자주 인용) ──
    "🚀 Michael Saylor":    "saylor",
    "⚡ Samson Mow":        "Excellion",
    "📊 Raoul Pal":         "RaoulGMI",
    "💰 Cathie Wood":       "CathieDWood",
    "🐂 Pompliano":         "APompliano",
    # ── 트레이더/분석가 ──
    "🎯 Willy Woo":         "woonomic",
    "📉 Peter Schiff":      "PeterSchiff",
    "📐 Peter Brandt":      "PeterLBrandt",
    "🦈 Barry Silbert":     "BarrySilbert",
    "🏦 Tom Lee":           "fundstrat",
    # ── 크립토 기업인 (CryptoYuna가 인용) ──
    "😎 CZ (Binance)":      "caboringz",
    "🔵 Kevin O'Leary":     "kevinolearytv",
    "💎 Larry Fink":        "BlackRock",
    # ── 정치/매크로/글로벌 인사 ──
    "🇺🇸 Donald Trump":     "realDonaldTrump",
    "🚗 Elon Musk":         "elonmusk",
    "🌍 Mario Nawfal":      "RoundtableSpace",
    "📡 Unusual Whales":    "unusual_whales",
    "💹 Jim Cramer":        "jimcramer",
    # ── 한국 인플루언서 ──
    "🇰🇷 CryptoYuna":      "CryptoYuna_",
    "🇰🇷 김영훈 IQ276":    "yhbryankim",
    "🇰🇷 Ki Young Ju":     "ki_young_ju",
    "🇰🇷 코인니스":        "coinness_kr",
    # ── DeFi/알트코인 전문가 ──
    "🔗 Cobie":             "coaboringz",
    "📊 Will Clemente":     "WClementeIII",
    "🧠 Arthur Hayes":      "CryptoHayes",
    "🐋 Lookonchain":       "lookonchain",
}

# ── CryptoYuna 스타일 이모지 매핑 ──
EMOJI_CATEGORIES = {
    # 긴급/속보
    "breaking": "🚨", "urgent": "🚨", "hack": "🚨", "exploit": "🚨",
    "just in": "🚨",
    # 경고
    "warn": "⚠️", "risk": "⚠️", "crash": "⚠️", "drop": "⚠️",
    "bear": "⚠️", "concern": "⚠️",
    # 핫/강세
    "surge": "🔥", "rally": "🔥", "pump": "🔥", "soar": "🔥",
    "bull": "🔥", "moon": "🔥", "record": "🔥", "ath": "🔥",
    "all-time": "🔥", "breakout": "🔥", "launch": "🔥",
    # 국가
    "trump": "🇺🇸", "us ": "🇺🇸", "america": "🇺🇸", "sec ": "🇺🇸",
    "fed ": "🇺🇸", "congress": "🇺🇸", "white house": "🇺🇸",
    "china": "🇨🇳", "chinese": "🇨🇳", "beijing": "🇨🇳",
    "japan": "🇯🇵", "boj": "🇯🇵", "yen": "🇯🇵",
    "korea": "🇰🇷", "한국": "🇰🇷",
    "eu ": "🇪🇺", "europe": "🇪🇺", "ecb": "🇪🇺",
    "el salvador": "🇸🇻", "bukele": "🇸🇻",
    "iran": "🇮🇷", "swiss": "🇨🇭", "switzerland": "🇨🇭",
    "russia": "🇷🇺", "india": "🇮🇳", "brazil": "🇧🇷",
    "uk ": "🇬🇧", "britain": "🇬🇧",
    # 기업/인물
    "saylor": "👨‍💼", "michael saylor": "👨‍💼",
    "cathie wood": "👩‍💼", "ark invest": "👩‍💼",
    "cz": "😎", "changpeng": "😎",
    "powell": "🏦", "fed chair": "🏦",
    "elon musk": "🚗", "musk": "🚗", "tesla": "🚗", "doge": "🐕",
    "arthur hayes": "🧠",
    "goldman": "🏦", "blackrock": "🏦", "jpmorgan": "🏦",
    # 토큰
    "bitcoin": "₿", "btc": "₿",
    "ethereum": "◆", "eth ": "◆",
    "stablecoin": "💵", "usdc": "🔵", "usdt": "💵",
    "solana": "🟣", "sol ": "🟣",
    "xrp": "💧",
    # 유형
    "etf": "📊", "chart": "📊", "data": "📊",
    "whale": "🐋", "transfer": "🐋",
    "regulation": "📜", "bill": "📜", "law": "📜", "tax": "📜",
    "payment": "💳", "visa": "💳", "mastercard": "💳",
    "mining": "⛏️", "miner": "⛏️",
    "war": "⚔️", "military": "⚔️", "missile": "⚔️",
    "ai ": "🤖", "ai agent": "🤖", "artificial": "🤖",
    "defi": "🔗", "nft": "🎨",
    "partnership": "🤝", "partner": "🤝", "collaborat": "🤝",
    "ipo": "📈", "listing": "📈",
}

# ── 이슈성 점수 키워드 ──
HOT_KEYWORDS = {
    "etf": 8, "blackrock": 8, "ibit": 7, "fidelity": 6, "grayscale": 6,
    "sec": 7, "spot etf": 9, "etf flow": 8, "inflow": 6, "outflow": 6,
    "morgan stanley": 7, "goldman": 7, "jpmorgan": 6,
    "coinbase": 5, "ark invest": 6, "cathie wood": 6,
    "trump": 9, "congress": 6, "regulation": 5,
    "stablecoin bill": 7, "executive order": 7, "white house": 7,
    "iran": 8, "war": 8, "missile": 8, "military": 7,
    "sanction": 7, "tariff": 7, "trade war": 8,
    "powell": 8, "fed": 7, "rate cut": 8, "rate hike": 8,
    "interest rate": 7, "inflation": 6,
    "whale": 7, "billion": 6, "all-time high": 9, "ath": 8,
    "crash": 8, "surge": 6, "rally": 6, "dump": 7,
    "liquidat": 7, "short squeeze": 8,
    "bitcoin": 4, "btc": 4, "ethereum": 4, "solana": 4,
    "xrp": 4, "stablecoin": 5,
    "saylor": 7, "microstrategy": 7, "mstr": 6,
    "el salvador": 6, "bukele": 6,
    "cz": 5, "binance": 5,
    "ai": 5, "ai agent": 7, "rwa": 5, "tokeniz": 6,
    "halving": 7,
    "payment": 5, "visa": 5, "mastercard": 5,
    "breaking": 9, "urgent": 8, "hack": 8, "exploit": 8, "lawsuit": 7,
    # 추가: 인물/기업 (CryptoYuna 인용 빈도 높음)
    "elon musk": 8, "musk": 7, "tesla": 6, "doge": 6, "dogecoin": 6,
    "kevin o'leary": 6, "raoul pal": 6, "peter brandt": 6,
    "circle": 5, "crcl": 5, "bnp paribas": 5, "citi": 5,
    "bernstein": 6, "robinhood": 5,
    "jack dorsey": 5, "block inc": 5,
    "larry fink": 7, "jamie dimon": 6,
    "arthur hayes": 6, "vitalik": 6,
    # 추가: 지정학/매크로
    "boj": 6, "ecb": 6, "china": 6, "russia": 6,
    "nuclear": 8, "ceasefire": 7, "nato": 6,
    "gdp": 5, "employment": 5, "jobs": 5, "cpi": 6, "ppi": 5,
    "debt ceiling": 7, "treasury": 6,
    # 추가: 크립토 생태계
    "airdrop": 5, "layer 2": 4, "rollup": 4,
    "bridge": 5, "cross-chain": 4, "interoper": 4,
    "staking": 4, "restaking": 5, "eigenlayer": 5,
    "memecoin": 5, "pepe": 4, "shib": 4,
    "ordinals": 5, "inscription": 5, "brc-20": 5,
}

# ── 포스트 카테고리 분류 ──
POST_CATEGORIES = {
    "🚨 속보": ["breaking", "urgent", "just in", "hack", "exploit"],
    "📊 시장/ETF": ["etf", "inflow", "outflow", "market", "trading", "chart", "rally", "surge", "crash", "dump"],
    "🏦 기관/금융": ["blackrock", "goldman", "jpmorgan", "morgan stanley", "fidelity", "bank", "institutional"],
    "📜 규제/정책": ["sec", "regulation", "bill", "law", "congress", "legislation", "compliance"],
    "🌍 지정학": ["war", "iran", "sanction", "tariff", "military", "missile", "geopolit"],
    "🏛️ 매크로": ["fed", "powell", "rate cut", "rate hike", "inflation", "gdp", "employment"],
    "🤖 기술/AI": ["ai ", "ai agent", "defi", "layer 2", "protocol", "upgrade", "blockchain"],
    "🐋 고래/온체인": ["whale", "transfer", "on-chain", "wallet", "flow"],
    "💳 채택/결제": ["payment", "visa", "mastercard", "adoption", "paypal"],
    "👨‍💼 인물/발언": ["saylor", "cz", "cathie wood", "trump", "powell", "vitalik", "says", "said"],
}


# ═══════════════════════════════════════
#  유틸리티 함수
# ═══════════════════════════════════════

def clean_text(text: str) -> str:
    text = html.unescape(text)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def parse_pub_date(date_str: str) -> datetime:
    if not date_str:
        return datetime.now(timezone.utc)
    try:
        return parsedate_to_datetime(date_str)
    except Exception:
        pass
    for fmt in ["%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S"]:
        try:
            return datetime.strptime(date_str, fmt).replace(tzinfo=timezone.utc)
        except Exception:
            continue
    return datetime.now(timezone.utc)


def format_pub_date(date_str: str) -> str:
    """발행일을 한국어 읽기 좋은 형태로 포맷"""
    pub = parse_pub_date(date_str)
    now = datetime.now(timezone.utc)
    diff = now - pub

    # 한국 시간 (UTC+9)
    from datetime import timedelta
    kst = pub + timedelta(hours=9)
    date_part = kst.strftime("%m/%d %H:%M")

    hours_ago = diff.total_seconds() / 3600
    if hours_ago < 1:
        minutes = int(diff.total_seconds() / 60)
        return f"{date_part} ({minutes}분 전)"
    elif hours_ago < 24:
        return f"{date_part} ({int(hours_ago)}시간 전)"
    elif hours_ago < 48:
        return f"{date_part} (어제)"
    else:
        days = int(hours_ago / 24)
        return f"{date_part} ({days}일 전)"


def get_category_emoji(title: str, summary: str = "") -> str:
    combined = (title + " " + summary).lower()
    for keyword, emoji in EMOJI_CATEGORIES.items():
        if keyword in combined:
            return emoji
    return "📢"


def get_post_category(title: str, summary: str = "") -> str:
    combined = (title + " " + summary).lower()
    for cat_name, keywords in POST_CATEGORIES.items():
        for kw in keywords:
            if kw in combined:
                return cat_name
    return "📢 일반"


def is_garbage_text(text: str) -> bool:
    if not text or len(text) < 20:
        return True
    num_chars = len(re.findall(r'[\d.$%,]', text))
    if num_chars / len(text) > 0.4:
        return True
    words = re.findall(r'[a-zA-Z가-힣]{2,}', text)
    if len(words) < 5:
        return True
    return False


def clean_paragraph(text: str) -> str:
    text = re.sub(r'(\d[\d,.]+\s*){5,}', '', text)
    text = re.sub(r'[0-9a-f]{20,}', '', text, flags=re.IGNORECASE)
    text = re.sub(r'(\d+\.\d+\s*){3,}', '', text)
    return text.strip()


def polish_korean(text: str) -> str:
    if not text:
        return text
    text = re.sub(r'\s+', ' ', text).strip()
    text = re.sub(r'\b(the|a|an|of the)\b', '', text, flags=re.IGNORECASE).strip()
    text = re.sub(r'\s{2,}', ' ', text)
    return text


def cut_at_sentence(text: str, max_len: int = 200) -> str:
    if len(text) <= max_len:
        return text
    truncated = text[:max_len]
    # 1) 문장 끝(다. / 요. / . / ! / ?)에서 자르기
    for ending in ['다. ', '요. ', '다.', '요.', '. ', '! ', '? ']:
        pos = truncated.rfind(ending)
        if pos > 20:
            return truncated[:pos + len(ending)].rstrip()
    last_dot = truncated.rfind('.')
    if last_dot > 20:
        return truncated[:last_dot + 1]
    # 2) 문장 끝을 못 찾으면 → 단어 경계에서 자르기 (단어 중간 잘림 방지)
    last_space = truncated.rfind(' ')
    if last_space > 20:
        return truncated[:last_space].rstrip()
    # 3) 공백도 없으면 (한국어 긴 단어열) → 한글 조사/어미 근처에서 자르기
    for i in range(min(max_len, len(text)) - 1, 20, -1):
        if text[i] in '은는이가을를에서도로의와':
            return text[:i + 1]
    return text[:max_len]


# ═══════════════════════════════════════
#  이슈성 점수 계산
# ═══════════════════════════════════════

def calc_recency_score(pub_date: datetime, max_score: float = 40.0) -> float:
    now = datetime.now(timezone.utc)
    hours_ago = (now - pub_date).total_seconds() / 3600
    if hours_ago <= 1:
        return max_score
    elif hours_ago <= 6:
        return max_score * 0.85
    elif hours_ago <= 12:
        return max_score * 0.7
    elif hours_ago <= 24:
        return max_score * 0.5
    elif hours_ago <= 48:
        return max_score * 0.25
    return max_score * 0.1


def calc_keyword_score(title: str, summary: str, max_score: float = 30.0):
    combined = (title + " " + summary).lower()
    total = 0
    matched = []
    for kw, weight in HOT_KEYWORDS.items():
        if kw in combined:
            total += weight
            matched.append(kw)
    return min(total, max_score), matched


def calc_cross_source_score(item: dict, all_items: list, max_score: float = 20.0) -> float:
    title_words = set(re.findall(r'\b[a-zA-Z]{4,}\b', item["title_en"].lower()))
    if not title_words:
        return 0
    matching_sources = set()
    for other in all_items:
        if other["link"] == item["link"]:
            continue
        other_words = set(re.findall(r'\b[a-zA-Z]{4,}\b', other["title_en"].lower()))
        if len(title_words & other_words) >= 2:
            matching_sources.add(other["source"])
    count = len(matching_sources)
    if count >= 4: return max_score
    elif count >= 3: return max_score * 0.8
    elif count >= 2: return max_score * 0.6
    elif count >= 1: return max_score * 0.3
    return 0


def calc_media_score(item: dict, max_score: float = 10.0) -> float:
    if item.get("video_url"): return max_score
    elif item.get("image_url"): return max_score * 0.5
    return 0


def calc_hot_score(item: dict, all_items: list) -> dict:
    pub_date = parse_pub_date(item.get("published", ""))
    recency = calc_recency_score(pub_date)
    keyword, matched_kw = calc_keyword_score(item["title_en"], item.get("summary_en", ""))
    cross = calc_cross_source_score(item, all_items)
    media = calc_media_score(item)
    total = recency + keyword + cross + media
    return {
        "total": round(total, 1),
        "recency": round(recency, 1),
        "keyword": round(keyword, 1),
        "cross": round(cross, 1),
        "media": round(media, 1),
        "matched_kw": matched_kw,
        "pub_datetime": pub_date,
    }


# ═══════════════════════════════════════
#  뉴스 수집
# ═══════════════════════════════════════

def extract_image_from_rss(entry) -> str:
    for media in entry.get("media_content", []):
        url = media.get("url", "")
        if url and ("image" in media.get("type", "") or media.get("medium") == "image"):
            return url
        if url and any(ext in url.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp', '.gif']):
            return url
    thumb = entry.get("media_thumbnail", [])
    if thumb:
        return thumb[0].get("url", "")
    for enc in entry.get("enclosures", []):
        if "image" in enc.get("type", ""):
            return enc.get("href", "")
    content_html = entry.get("summary", "")
    if hasattr(entry, "content"):
        for c in entry.content:
            content_html += c.get("value", "")
    img_match = re.search(r'<img[^>]*src=["\']([^"\']+)["\']', content_html)
    if img_match:
        return img_match.group(1)
    return ""


def scrape_og_image(url: str) -> str:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=8)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        og = soup.find("meta", property="og:image")
        if og and og.get("content"):
            return og["content"]
        tw = soup.find("meta", attrs={"name": "twitter:image"})
        if tw and tw.get("content"):
            return tw["content"]
    except Exception:
        pass
    return ""


def scrape_article_text(url: str) -> str:
    """기사 전체 본문을 최대한 많이 수집 (4000자)"""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        og_desc = soup.find("meta", property="og:description")
        og_text = og_desc["content"].strip() if og_desc and og_desc.get("content") else ""

        for tag in soup.find_all(["script", "style", "nav", "aside", "footer",
                                   "table", "figure", "figcaption", "iframe",
                                   "noscript", "svg"]):
            tag.decompose()
        for el in soup.find_all(attrs={"class": re.compile(r"price|ticker|widget|market|chart|sidebar|ad|banner", re.I)}):
            el.decompose()

        selectors = [
            "article", '[class*="article-body"]', '[class*="post-content"]',
            '[class*="entry-content"]', '[class*="content-body"]', "main",
        ]
        text = ""
        for sel in selectors:
            el = soup.select_one(sel)
            if el:
                paragraphs = el.find_all("p")
                clean_paras = []
                for p in paragraphs:
                    p_text = clean_paragraph(p.get_text(strip=True))
                    if p_text and not is_garbage_text(p_text):
                        clean_paras.append(p_text)
                text = " ".join(clean_paras)
                if len(text) > 300:
                    break

        if is_garbage_text(text) and og_text and not is_garbage_text(og_text):
            return og_text[:4000]
        return text[:4000] if text else og_text[:4000]
    except Exception:
        return ""


# ── 핵심 문장 선별용 가중치 키워드 ──
# 이유/근거/수치를 담고 있을 가능성이 높은 단어들
REASON_KEYWORDS = [
    # 인과관계
    "because", "due to", "as a result", "thanks to", "driven by",
    "following", "after", "amid", "since", "lead to", "caused by",
    "result of", "sparked by", "fueled by", "prompted by",
    # 수치/데이터
    "billion", "million", "trillion", "%", "percent", "$",
    "increased", "decreased", "grew", "rose", "fell", "dropped",
    "doubled", "tripled", "surged", "plunged", "hit", "reached",
    # 전망/분석
    "could", "may", "expected", "forecast", "predict", "potential",
    "likely", "according to", "analyst", "report", "study",
    # 구체적 행동
    "announced", "launched", "partnered", "acquired", "invested",
    "approved", "signed", "filed", "listed", "supported",
    "integrated", "enabled", "allows", "plans to", "will",
]


def score_sentence_importance(sentence: str, title: str = "") -> float:
    """문장의 '정보 가치' 점수를 매김 — 이유/근거/수치가 있을수록 높음"""
    s_lower = sentence.lower()
    title_lower = title.lower() if title else ""
    score = 0.0

    # 1) 이유/근거/수치 키워드 포함 (+2~3점씩)
    for kw in REASON_KEYWORDS:
        if kw in s_lower:
            score += 2.5

    # 2) 숫자가 포함된 문장 (수치 데이터 = 고가치)
    numbers = re.findall(r'\d+[\d,.]*', sentence)
    if numbers:
        score += len(numbers) * 2.0
    # $ 금액이 있으면 추가 점수
    if '$' in sentence or '달러' in sentence or '원' in sentence:
        score += 3.0
    # % 비율이 있으면 추가 점수
    if '%' in sentence or '퍼센트' in sentence:
        score += 3.0

    # 3) 제목과 너무 유사하면 감점 (제목 반복 방지)
    if title_lower:
        title_words = set(re.findall(r'[a-zA-Z]{4,}', title_lower))
        sent_words = set(re.findall(r'[a-zA-Z]{4,}', s_lower))
        if title_words and sent_words:
            overlap = len(title_words & sent_words) / max(len(title_words), 1)
            if overlap > 0.6:
                score -= 10.0  # 제목 반복이면 크게 감점

    # 4) 너무 짧은 문장 감점
    if len(sentence) < 40:
        score -= 3.0

    # 5) 인용문이 있으면 가점 (전문가 발언)
    if '"' in sentence or '"' in sentence or "'" in sentence:
        score += 2.0

    return score


def _is_off_topic_en(sentence: str, reference: str) -> bool:
    """
    문장이 기준 문장과 완전히 다른 기사에서 온 것인지 판단 (True = off-topic)

    매우 보수적으로 판단:
    - 문장에 기준에 없는 새로운 고유명사(프로젝트명, 인물명 등)가 등장하고
    - 동시에 기준의 핵심 키워드가 하나도 없을 때만 off-topic

    일반 서술문(고유명사 없는 문장)은 무조건 통과시킴
    """
    if not reference or len(reference) < 30:
        return False

    # 기준 문장의 고유명사 (대문자 시작, 불용어 제외)
    proper_stop = {"The", "This", "That", "After", "Before", "While", "When",
                   "However", "According", "Meanwhile", "But", "And", "For",
                   "Its", "His", "Her", "Has", "Was", "Are", "Not", "New"}
    ref_proper = set(re.findall(r'\b[A-Z][a-zA-Z]+\b', reference)) - proper_stop
    sent_proper = set(re.findall(r'\b[A-Z][a-zA-Z]+\b', sentence)) - proper_stop

    # 문장에 고유명사가 없으면 → 일반 서술문이므로 통과 (off-topic 아님)
    if not sent_proper:
        return False

    # 문장의 고유명사가 기준과 하나라도 겹치면 → 같은 주제
    if ref_proper and len(ref_proper & sent_proper) >= 1:
        return False

    # 문장에 기준에 없는 새 고유명사만 있음 → off-topic 가능성
    # 하지만 크립토 관련 일반 용어는 제외 (Bitcoin, Ethereum 등은 어디서나 나올 수 있음)
    crypto_common = {"Bitcoin", "BTC", "Ethereum", "ETH", "Crypto", "Blockchain",
                     "DeFi", "NFT", "SEC", "Fed", "ETF", "USD", "USDT", "USDC"}
    new_proper = sent_proper - ref_proper - crypto_common
    if not new_proper:
        return False  # 새 고유명사가 크립토 일반 용어뿐이면 통과

    # 새 고유명사가 2개 이상이면 → 다른 기사일 가능성 높음
    if len(new_proper) >= 2:
        return True

    return False


def summarize_text(text: str, translator: GoogleTranslator, max_sentences: int = 5) -> str:
    """
    기사 본문에서 핵심 문장을 선별하여 번역
    — 단순 첫 3문장이 아닌, 이유/근거/수치가 담긴 고가치 문장 우선 선택
    — 제목/도입부와 주제가 다른 문장은 제외 (다른 기사 혼입 방지)
    """
    if not text:
        return ""

    # 모든 문장 분리
    sentences = re.split(r'(?<=[.!?])\s+', text)
    if not sentences:
        return ""

    # 첫 문장은 항상 포함 (기사 도입부)
    first_sentence = sentences[0] if sentences else ""

    # 나머지 문장을 정보 가치 순으로 정렬
    scored = []
    off_topic_count = 0
    for i, s in enumerate(sentences[1:], 1):
        if len(s.strip()) < 20:
            continue

        # 주제 이탈 필터: 다른 기사에서 온 문장만 감점 (제거하지 않음)
        topic_penalty = 0.0
        if _is_off_topic_en(s, first_sentence):
            topic_penalty = -8.0  # 감점이지만, 수치/데이터가 풍부하면 살아남을 수 있음
            off_topic_count += 1

        importance = score_sentence_importance(s, first_sentence)
        # 원래 순서도 약간 반영 (앞쪽 문장 우선)
        position_bonus = max(0, 5.0 - i * 0.3)
        scored.append((s, importance + position_bonus + topic_penalty, i))

    # 점수 높은 순으로 정렬 후 상위 N개 선택
    scored.sort(key=lambda x: x[1], reverse=True)
    top_sentences = scored[:max_sentences - 1]

    # 원래 문장 순서로 재정렬
    top_sentences.sort(key=lambda x: x[2])

    # 최종 조합: 첫 문장 + 고가치 문장들
    selected = [first_sentence] + [s[0] for s in top_sentences]
    summary_en = " ".join(selected)

    # 번역 길이 제한 (넉넉하게 — 상세 내용 확보)
    if len(summary_en) > 2500:
        summary_en = summary_en[:2500]
        last_period = max(summary_en.rfind('.'), summary_en.rfind('!'), summary_en.rfind('?'))
        if last_period > 200:
            summary_en = summary_en[:last_period + 1]

    # 분할 번역 (Google Translate 5000자 제한 대응)
    try:
        if len(summary_en) > 1200:
            # 문장 단위로 2~3 파트 분할 후 각각 번역
            parts = re.split(r'(?<=[.!?])\s+', summary_en)
            mid = len(parts) // 2
            chunk1 = " ".join(parts[:mid])
            chunk2 = " ".join(parts[mid:])
            t1 = translator.translate(chunk1) if chunk1 else ""
            t2 = translator.translate(chunk2) if chunk2 else ""
            result = (t1 + " " + t2).strip()
        else:
            result = translator.translate(summary_en)
        return polish_korean(result)
    except Exception:
        return summary_en


def fetch_x_influencer(display_name: str, handle: str, count: int = 5):
    """X 인플루언서 피드를 Nitter RSS로 수집"""
    translator = GoogleTranslator(source="auto", target="ko")
    results = []
    for base_url in NITTER_INSTANCES:
        try:
            feed_url = f"{base_url}/{handle}/rss"
            feed = feedparser.parse(feed_url)
            if not feed.entries:
                continue
            for entry in feed.entries[:count]:
                text_en = clean_text(entry.get("title", "") or entry.get("description", ""))
                if not text_en or len(text_en) < 10:
                    continue

                # RT(리트윗)은 건너뛰기
                if text_en.startswith("RT @") or text_en.startswith("RT:"):
                    continue

                try:
                    text_ko = translator.translate(text_en[:500])
                    text_ko = polish_korean(text_ko) if text_ko else text_en
                except Exception:
                    text_ko = text_en

                published = entry.get("published", "")
                link = entry.get("link", f"https://x.com/{handle}")

                # 이미지 추출 시도
                image_url = extract_image_from_rss(entry)

                results.append({
                    "title_en": text_en[:200],
                    "title_ko": text_ko[:200] if text_ko else text_en[:200],
                    "summary_en": text_en,
                    "summary_ko": text_ko or text_en,
                    "published": published,
                    "link": link,
                    "source": f"🐦 {display_name}",
                    "video_url": "",
                    "image_url": image_url,
                })
            break  # 성공한 Nitter 인스턴스에서 가져왔으면 다음으로
        except Exception:
            continue
    return results


def fetch_all_news(feed_names: list, count_per_feed: int = 5, progress_callback=None,
                   influencer_names: list = None, count_per_influencer: int = 3):
    """모든 RSS 소스 + X 인플루언서에서 뉴스 수집"""
    all_items = []
    influencer_names = influencer_names or []
    total_steps = len(feed_names) + len(influencer_names)
    if total_steps == 0:
        return []

    step = 0

    # ── RSS 피드 수집 ──
    for i, feed_name in enumerate(feed_names):
        step += 1
        if progress_callback:
            progress_callback(step / total_steps, f"📡 {feed_name} 수집 중...")

        feed_url = RSS_FEEDS.get(feed_name)
        if not feed_url:
            continue

        is_korean = feed_name in KOREAN_FEEDS
        translator = GoogleTranslator(source="en", target="ko") if not is_korean else None

        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:count_per_feed]:
                title_en = clean_text(entry.get("title", ""))
                link = entry.get("link", "#")
                image_url = extract_image_from_rss(entry)
                rss_summary = clean_text(entry.get("summary", entry.get("description", "")))

                if not image_url and link and link != "#":
                    image_url = scrape_og_image(link)

                if len(rss_summary) < 200:
                    full_text = scrape_article_text(link)
                else:
                    full_text = rss_summary

                if is_korean:
                    title_ko = title_en
                    raw_text = full_text if full_text else rss_summary
                    summary_ko = cut_at_sentence(raw_text, 1000) if raw_text else ""
                else:
                    try:
                        title_ko = translator.translate(title_en)
                        title_ko = polish_korean(title_ko)
                    except Exception:
                        title_ko = title_en
                    summary_ko = summarize_text(full_text if full_text else rss_summary, translator, max_sentences=10)

                published = entry.get("published", "")

                all_items.append({
                    "title_en": title_en,
                    "title_ko": title_ko,
                    "summary_en": rss_summary,
                    "summary_ko": summary_ko,
                    "published": published,
                    "link": link,
                    "source": feed_name,
                    "image_url": image_url,
                    "video_url": "",
                })
        except Exception as e:
            continue

    # ── X 인플루언서 피드 수집 (Nitter) ──
    for display_name in influencer_names:
        step += 1
        if progress_callback:
            progress_callback(step / total_steps, f"🐦 {display_name} 수집 중...")

        handle = X_INFLUENCERS.get(display_name)
        if not handle:
            continue

        try:
            items = fetch_x_influencer(display_name, handle, count_per_influencer)
            all_items.extend(items)
        except Exception:
            continue

    # 이슈성 점수 계산
    for item in all_items:
        item["score"] = calc_hot_score(item, all_items)

    # 점수 순 정렬
    all_items.sort(key=lambda x: x["score"]["total"], reverse=True)

    if progress_callback:
        progress_callback(1.0, "✅ 수집 완료!")

    return all_items


# ═══════════════════════════════════════
#  소스 품질 등급 (중복 시 어떤 소스를 남길지 결정)
# ═══════════════════════════════════════
#  등급이 낮을수록 우선 (1=최고 품질)
#  - Tier 1: 원문 기사가 길고 분석이 깊은 매체
#  - Tier 2: 속보는 빠르지만 본문이 짧은 매체
#  - Tier 3: 집계/리라이트 매체
#  - Tier 4: X 인플루언서 (짧은 트윗)

SOURCE_QUALITY = {
    # Tier 1 — 심층 기사 매체 (원문 품질 최고)
    "🟠 CoinDesk": 1,
    "📰 Cointelegraph": 1,
    "🟣 Decrypt": 1,
    "📈 Blockworks": 1,
    "📊 The Block": 1,
    "🏦 DL News": 1,
    "🛡️ The Defiant": 2,
    "📚 Coin Bureau": 2,
    "🪨 CryptoSlate": 2,
    # Tier 2 — 빠른 속보 + 중간 품질
    "🔵 CryptoNews": 2,
    "⚡ Bitcoin Magazine": 2,
    "📡 BeInCrypto": 2,
    "🌏 Wu Blockchain": 2,
    "💹 CNBC Crypto": 2,
    "🔬 Messari": 2,
    # Tier 3 — 집계/짧은 뉴스
    "🔔 Watcher.Guru": 3,
    "🦅 CryptoPanic": 3,
    "🐋 Whale Alert Blog": 3,
    "📉 Glassnode Blog": 3,
    "🦎 CoinGecko Blog": 3,
    # 한국 매체 (고유 콘텐츠이므로 Tier 2)
    "🇰🇷 블록미디어": 2,
    "🇰🇷 디지털투데이": 2,
    "🇰🇷 코인리더스": 3,
}

def get_source_quality(source_name: str) -> int:
    """소스 품질 등급 반환 (낮을수록 좋음). X 인플루언서는 4"""
    if source_name.startswith("🐦"):
        return 4
    return SOURCE_QUALITY.get(source_name, 5)


# ═══════════════════════════════════════
#  스마트 중복 제거
# ═══════════════════════════════════════

def _normalize_crypto_text(text: str) -> str:
    """BTC→bitcoin 등 크립토 약어를 정규화하여 중복 비교 정확도 향상"""
    aliases = {
        "btc": "bitcoin", "eth": "ethereum", "sol": "solana",
        "xrp": "ripple", "doge": "dogecoin", "ada": "cardano",
        "bnb": "binancechain", "dot": "polkadot", "avax": "avalanche",
        "link": "chainlink", "matic": "polygon", "shib": "shibainucoin",
        "mstr": "microstrategy", "sec": "securitiescommission",
        "100k": "hundredthousand", "50k": "fiftythousand",
        "etfs": "etf", "inflows": "inflow", "outflows": "outflow",
        "surged": "surge", "surges": "surge", "rallied": "rally",
        "crashed": "crash", "hits": "hit", "reached": "reach",
    }
    t = text.lower()
    for short, full in aliases.items():
        t = re.sub(r'\b' + re.escape(short) + r'\b', full, t)
    return t


def deduplicate_news(items: list, threshold: float = 0.40) -> list:
    """
    스마트 중복 제거:
    1) 같은 뉴스가 여러 소스에서 나오면 → 가장 품질 좋은 소스 1개만 유지
    2) 중복된 다른 소스 이름들은 merged_sources에 기록 (복수 매체 표시용)
    3) 한국어 제목도 비교하여 한/영 크로스 중복도 제거
    4) BTC↔bitcoin 등 약어 정규화로 같은 뉴스를 정확히 인식
    """
    if not items:
        return []

    # 각 아이템에 단어셋 미리 계산 (정규화 적용)
    for item in items:
        # 영어 단어셋 (약어 정규화 후)
        normalized_en = _normalize_crypto_text(item["title_en"])
        item["_title_words_en"] = set(
            re.findall(r'\b[a-zA-Z]{3,}\b', normalized_en)
        )
        # 한국어 키워드셋 (2글자 이상)
        item["_title_words_ko"] = set(
            re.findall(r'[가-힣]{2,}', item.get("title_ko", ""))
        )
        # 숫자셋 (기사 고유 식별용 — "$50B", "23%", "100K" 등)
        item["_numbers"] = set(
            re.findall(r'\$?[\d,.]+[%KMBTkmbt조억만원]?', item["title_en"])
        )

    # 클러스터링: 유사한 기사끼리 그룹
    clusters = []  # 각 클러스터 = [아이템1, 아이템2, ...]

    for item in items:
        matched_cluster = None
        for cluster in clusters:
            # 클러스터 대표(첫 번째)와 비교
            rep = cluster[0]

            # 영어 제목 유사도
            en_sim = 0.0
            if item["_title_words_en"] and rep["_title_words_en"]:
                intersection = item["_title_words_en"] & rep["_title_words_en"]
                union = item["_title_words_en"] | rep["_title_words_en"]
                en_sim = len(intersection) / max(len(union), 1)

            # 한국어 제목 유사도
            ko_sim = 0.0
            if item["_title_words_ko"] and rep["_title_words_ko"]:
                intersection_ko = item["_title_words_ko"] & rep["_title_words_ko"]
                union_ko = item["_title_words_ko"] | rep["_title_words_ko"]
                ko_sim = len(intersection_ko) / max(len(union_ko), 1)

            # 숫자 일치 보너스 (같은 수치 → 같은 뉴스일 확률 높음)
            num_bonus = 0.0
            if item["_numbers"] and rep["_numbers"]:
                num_overlap = len(item["_numbers"] & rep["_numbers"])
                if num_overlap >= 1:
                    num_bonus = 0.15

            # 최종 유사도 = max(영어, 한국어) + 숫자보너스
            similarity = max(en_sim, ko_sim) + num_bonus

            if similarity > threshold:
                matched_cluster = cluster
                break

        if matched_cluster:
            matched_cluster.append(item)
        else:
            clusters.append([item])

    # 각 클러스터에서 최고 품질 아이템 1개 선택
    unique = []
    for cluster in clusters:
        # 정렬 기준: (1) 소스 품질 등급 낮을수록 좋음  (2) 이슈성 점수 높을수록 좋음  (3) 요약 길수록 좋음
        cluster.sort(key=lambda x: (
            get_source_quality(x["source"]),
            -x.get("score", {}).get("total", 0) if isinstance(x.get("score"), dict) else 0,
            -len(x.get("summary_ko", ""))
        ))

        best = cluster[0]

        # 중복된 다른 소스들 기록 (UI에서 "이 뉴스를 다룬 매체: A, B, C" 표시용)
        other_sources = list(set(
            item["source"] for item in cluster[1:]
            if item["source"] != best["source"]
        ))
        best["merged_sources"] = other_sources
        best["duplicate_count"] = len(cluster)

        unique.append(best)

    # 임시 키 정리
    for item in unique:
        item.pop("_title_words_en", None)
        item.pop("_title_words_ko", None)
        item.pop("_numbers", None)

    return unique


# ═══════════════════════════════════════
#  이미지 다운로드
# ═══════════════════════════════════════

def download_image(url: str, save_path: str) -> bool:
    """이미지 URL을 로컬 파일로 다운로드"""
    if not url:
        return False
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15, stream=True)
        resp.raise_for_status()
        content_type = resp.headers.get("content-type", "")

        # 이미지인지 확인
        if not any(t in content_type for t in ["image", "octet-stream"]):
            # URL 확장자로 판단
            if not any(ext in url.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp', '.gif', '.svg']):
                return False

        with open(save_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)

        # 파일 크기 확인 (1KB 미만이면 삭제)
        if os.path.getsize(save_path) < 1024:
            os.remove(save_path)
            return False

        return True
    except Exception:
        if os.path.exists(save_path):
            try:
                os.remove(save_path)
            except:
                pass
        return False


def get_image_extension(url: str) -> str:
    """URL에서 이미지 확장자 추출"""
    url_lower = url.lower().split('?')[0]
    if '.png' in url_lower: return '.png'
    if '.webp' in url_lower: return '.webp'
    if '.gif' in url_lower: return '.gif'
    if '.svg' in url_lower: return '.png'  # SVG는 PNG로
    return '.jpg'


# ═══════════════════════════════════════
#  🔥 CryptoYuna 스타일 포스트 생성
#  ───────────────────────────────────
#  16개+ 실제 게시물 분석 기반 3가지 패턴:
#
#  [패턴A] 뉴스 기사형 (가장 많음)
#    🔥 제목!
#    (빈줄)
#    설명 1~2문장
#    (빈줄)
#    - 핵심1
#    - 핵심2
#    - 핵심3
#    (빈줄)
#    요약/전망 한 줄 !!
#
#  [패턴B] 인물 발언 인용형
#    🔥 인물명 : "핵심 발언 요약"
#    (빈줄)
#    소속/직함 인물명 :
#    (빈줄)
#    "상세 인용문 1"
#    "상세 인용문 2"
#
#  [패턴C] 속보형
#    ⭐ 속보 : 제목
#    (빈줄)
#    • 핵심1
#    • 핵심2
#    • 핵심3
#    • 핵심4
#    (빈줄)
#    요약 한 줄!
#    (빈줄)
#    (출처)
# ═══════════════════════════════════════

# ── 인물 키워드 매핑 (인용형 포스트 감지용) ──
PERSON_KEYWORDS = {
    "saylor": "마이클 세일러(MicroStrategy CEO)",
    "michael saylor": "마이클 세일러(MicroStrategy CEO)",
    "cathie wood": "캐시 우드(ARK Invest CEO)",
    "cz": "CZ(바이낸스 전 CEO)",
    "changpeng zhao": "CZ(바이낸스 전 CEO)",
    "powell": "제롬 파월(연준 의장)",
    "trump": "도널드 트럼프(미국 대통령)",
    "vitalik": "비탈릭 부테린(이더리움 창시자)",
    "gensler": "게리 겐슬러(SEC 전 위원장)",
    "raoul pal": "라울 팔(매크로 전략가)",
    "peter brandt": "피터 브란트(트레이더)",
    "peter schiff": "피터 쉬프(금 투자자)",
    "larry fink": "래리 핑크(BlackRock CEO)",
    "jamie dimon": "제이미 다이먼(JPMorgan CEO)",
    "elon musk": "일론 머스크(Tesla CEO)",
    "kevin o'leary": "케빈 오리어리(Shark Tank)",
    "jack yi": "Jack Yi(LD캐피털 창립자)",
    "standard chartered": "스탠다드차타드",
    "imf": "IMF(국제통화기금)",
    "elon musk": "일론 머스크(Tesla/SpaceX CEO)",
    "musk": "일론 머스크(Tesla/SpaceX CEO)",
    "jack dorsey": "잭 도시(Block CEO)",
    "arthur hayes": "아서 헤이스(BitMEX 창립자)",
    "sam altman": "샘 알트만(OpenAI CEO)",
    "brian armstrong": "브라이언 암스트롱(Coinbase CEO)",
    "sam bankman": "SBF(FTX 전 CEO)",
    "gary gensler": "게리 겐슬러(SEC 전 위원장)",
    "paul atkins": "폴 앳킨스(SEC 위원장)",
    "janet yellen": "재닛 옐런(재무장관)",
    "xi jinping": "시진핑(중국 주석)",
    "putin": "푸틴(러시아 대통령)",
    "says": None, "said": None, "argues": None,
    "believes": None, "predicts": None, "warns": None,
}

QUOTE_MARKERS = ["says", "said", "argues", "believes", "predicts", "warns",
                 "expects", "forecasts", "claims", "states", "announces"]


def detect_post_type(title_en: str, summary_en: str) -> str:
    """포스트 유형 자동 감지: 'quote' / 'breaking' / 'news'"""
    combined = (title_en + " " + summary_en).lower()

    # 인물 발언 감지
    has_person = any(k in combined for k in PERSON_KEYWORDS if k not in QUOTE_MARKERS)
    has_quote_verb = any(q in combined for q in QUOTE_MARKERS)
    has_quotation = '"' in title_en or '"' in title_en or ':' in title_en
    if has_person and (has_quote_verb or has_quotation):
        return "quote"

    # 속보 감지
    breaking_words = ["breaking", "urgent", "just in", "hack", "exploit",
                      "crash", "war ", "missile", "military strike"]
    if any(w in combined for w in breaking_words):
        return "breaking"

    return "news"


def find_person_name(title_en: str, summary_en: str) -> str:
    """제목/요약에서 인물명 추출"""
    combined = (title_en + " " + summary_en).lower()
    for keyword, display_name in PERSON_KEYWORDS.items():
        if keyword in combined and display_name:
            return display_name
    return ""


def _calc_topic_relevance(sentence: str, title: str) -> float:
    """문장이 제목과 같은 주제인지 관련도 점수 (0.0~1.0)"""
    if not title or not sentence:
        return 0.5  # 판단 불가 → 중립

    # 제목에서 핵심 키워드 추출 (한글 2글자+, 영어 3글자+, 숫자 포함)
    title_keywords = set(re.findall(r'[가-힣]{2,}', title))
    title_keywords |= set(re.findall(r'[a-zA-Z]{3,}', title.lower()))
    title_keywords |= set(re.findall(r'\d+[%조억만달러원KMBkmb]*', title))
    # 불용어 제거
    stop_words = {"있는", "있다", "하는", "하고", "에서", "으로", "the", "and", "for", "with", "has", "are", "was", "its"}
    title_keywords -= stop_words

    if not title_keywords:
        return 0.5

    # 문장에서 키워드 추출
    sent_text = sentence.lower()
    matched = sum(1 for kw in title_keywords if kw.lower() in sent_text)
    relevance = matched / len(title_keywords)

    return relevance


def extract_clean_bullets(summary: str, title: str = "", max_count: int = 4) -> list:
    """
    요약 텍스트에서 고가치 불릿 포인트 추출
    — 이유/근거/수치가 담긴 문장을 우선 선택
    — 제목과 관련 높은 문장에 가점, 무관한 문장에 감점 (제거하지 않음)
    — 제목을 단순 반복하는 문장만 제외
    """
    if not summary:
        return []

    sentences = re.split(r'(?<=[.!?다요음함됨것중])\s+', summary)
    scored_sentences = []

    for s in sentences:
        s = s.strip()
        if len(s) < 8:
            continue
        # 숫자 도배 필터
        num_ratio = len(re.findall(r'[\d.$%,]', s)) / max(len(s), 1)
        if num_ratio > 0.5:
            continue

        # 정보 가치 점수 계산
        score = 0.0

        # 주제 관련도 → 가점/감점 (제거하지 않음)
        relevance = _calc_topic_relevance(s, title)
        score += relevance * 3.0  # 관련 높으면 가점
        if relevance < 0.05:
            score -= 5.0  # 완전 무관하면 감점 (but still kept)

        # 수치/데이터가 있으면 고가치
        if re.search(r'\d+[%조억만달러원]', s):
            score += 5.0
        if re.search(r'\d[\d,.]+', s):
            score += 2.0

        # 구체적 행동/이유 키워드 (한국어)
        reason_ko = ["때문", "이유", "덕분", "결과", "영향", "따르면",
                     "발표", "출시", "지원", "허용", "승인", "도입",
                     "파트너", "협력", "투자", "상장", "전망", "예상",
                     "가능", "계획", "목표", "전략", "확대", "성장"]
        for kw in reason_ko:
            if kw in s:
                score += 2.0

        # 제목과 너무 유사하면 감점 (단순 반복 방지)
        if title:
            title_chars = set(title.replace(" ", ""))
            sent_chars = set(s.replace(" ", ""))
            if title_chars and sent_chars:
                overlap = len(title_chars & sent_chars) / max(len(title_chars), 1)
                if overlap > 0.7:
                    score -= 10.0

        scored_sentences.append((s, score))

    # 점수 순 정렬
    scored_sentences.sort(key=lambda x: x[1], reverse=True)

    # 상위 N개 반환
    return [s[0] for s in scored_sentences[:max_count]]


def generate_yuna_style_post(item: dict) -> dict:
    """
    CryptoYuna 스타일 포스트 자동 생성
    실제 16개+ 게시물 분석 기반 — 3가지 유형 자동 감지
    """

    emoji = get_category_emoji(item["title_en"], item.get("summary_en", ""))
    category = get_post_category(item["title_en"], item.get("summary_en", ""))
    post_type = detect_post_type(item["title_en"], item.get("summary_en", ""))
    title = item["title_ko"].strip()
    summary = item.get("summary_ko", "")
    source = item.get("source", "")
    source_clean = re.sub(r'^[^\s]*\s*', '', source).strip()

    # 제목 끝 처리 (CryptoYuna: 대부분 ! 또는 !! 로 끝남)
    if not title.endswith(('!', '?', '.')):
        title += '!'

    sentences = extract_clean_bullets(summary, title, 8)

    # ════════════════════════════════════
    #  패턴B: 인물 발언 인용형
    # ════════════════════════════════════
    if post_type == "quote":
        person = find_person_name(item["title_en"], item.get("summary_en", ""))
        lines = []

        if person:
            lines.append(f"{emoji} {person} : \"{title}\"")
        else:
            lines.append(f"{emoji} {title}")

        lines.append("")

        # 인용문 (따옴표 감싸기)
        for s in sentences[:4]:
            lines.append(f"\"{cut_at_sentence(s, 200)}\"")

        if sentences and len(sentences) > 4:
            lines.append("")
            lines.append(cut_at_sentence(sentences[-1], 150))

        post_text = "\n".join(lines)

    # ════════════════════════════════════
    #  패턴C: 속보형
    # ════════════════════════════════════
    elif post_type == "breaking":
        lines = [f"{emoji} 속보 : {title}", ""]

        for s in sentences[:6]:
            lines.append(f"• {cut_at_sentence(s, 150)}")

        if sentences:
            lines.append("")
            if len(sentences) > 3:
                closing = cut_at_sentence(sentences[-1], 150)
                lines.append(closing)

        if source_clean:
            lines.append("")
            lines.append(f"({source_clean})")

        post_text = "\n".join(lines)

    # ════════════════════════════════════
    #  패턴A: 뉴스 기사형 (기본, 가장 많음)
    #  ────────────────────────────────
    #  구조:
    #    🔥 제목!
    #    (빈줄)
    #    도입부 설명 1~2문장
    #    (빈줄)
    #    - 핵심1 (상세 설명 포함)
    #    - 핵심2 (수치/근거 포함)
    #    - 핵심3 (전망/분석 포함)
    #    - 핵심4 (추가 맥락)
    #    (빈줄)
    #    전망/요약 마무리 !!
    # ════════════════════════════════════
    else:
        lines = [f"{emoji} {title}", ""]

        # 도입부 설명 2문장까지 (제목 다음에 맥락 설명)
        intro_sentences = []
        bullet_sentences = []

        for i, s in enumerate(sentences):
            if i < 2:
                intro_sentences.append(s)
            else:
                bullet_sentences.append(s)

        if intro_sentences:
            for s in intro_sentences:
                lines.append(cut_at_sentence(s, 200))
            lines.append("")

        # 불릿 포인트 — 최대 5개, 각 150자까지 (상세 내용 포함)
        for s in bullet_sentences[:5]:
            s_trimmed = cut_at_sentence(s, 150)
            lines.append(f"- {s_trimmed}")

        # 마지막 전망/요약
        if len(sentences) > 3:
            lines.append("")
            remaining = sentences[min(6, len(sentences) - 1):]
            if remaining:
                closing = cut_at_sentence(remaining[0], 150)
                if closing and not closing.endswith(('!', '?', '.', '다', '요', '!!')):
                    closing += ' !!'
                elif closing and closing.endswith('.'):
                    closing = closing[:-1] + ' !!'
                lines.append(closing)

        post_text = "\n".join(lines)

    # 빈 줄 연속 정리
    post_text = re.sub(r'\n{3,}', '\n\n', post_text).strip()

    # 발행일 포맷
    pub_raw = item.get("published", "")
    pub_display = format_pub_date(pub_raw) if pub_raw else ""

    return {
        "text": post_text,
        "post_type": post_type,
        "category": category,
        "emoji": emoji,
        "title": title,
        "score": item["score"]["total"],
        "source": source,
        "link": item.get("link", ""),
        "image_url": item.get("image_url", ""),
        "merged_sources": item.get("merged_sources", []),
        "duplicate_count": item.get("duplicate_count", 1),
        "published": pub_raw,
        "pub_display": pub_display,
    }


# ═══════════════════════════════════════
#  파일 저장
# ═══════════════════════════════════════

def save_post_package(post: dict, output_dir: str, index: int) -> dict:
    """포스트를 파일로 저장 (텍스트 + 이미지)"""

    # 폴더명: 01_카테고리_제목앞10자
    safe_title = re.sub(r'[^\w가-힣]', '', post["title"])[:15]
    cat_short = re.sub(r'[^\w가-힣]', '', post["category"])[:6]
    folder_name = f"{index:02d}_{cat_short}_{safe_title}"
    post_dir = os.path.join(output_dir, folder_name)
    os.makedirs(post_dir, exist_ok=True)

    result = {"folder": post_dir, "text_file": None, "image_file": None}

    # 텍스트 저장
    text_path = os.path.join(post_dir, "포스트.txt")
    with open(text_path, "w", encoding="utf-8") as f:
        f.write(post["text"])
        f.write(f"\n\n─────────────────\n")
        if post.get("pub_display"):
            f.write(f"발행일시: {post['pub_display']} (KST)\n")
        f.write(f"이슈성 점수: {post['score']}/100\n")
        f.write(f"카테고리: {post['category']}\n")
        f.write(f"대표 출처: {post['source']}\n")
        if post.get("merged_sources"):
            f.write(f"동일 보도: {', '.join(post['merged_sources'][:5])}\n")
        f.write(f"원문: {post['link']}\n")
    result["text_file"] = text_path

    # 이미지 다운로드
    if post.get("image_url"):
        ext = get_image_extension(post["image_url"])
        img_path = os.path.join(post_dir, f"이미지{ext}")
        if download_image(post["image_url"], img_path):
            result["image_file"] = img_path

    return result


# ═══════════════════════════════════════
#  Streamlit UI
# ═══════════════════════════════════════

st.set_page_config(
    page_title="🪙 크립토 자동 기사 생성기",
    page_icon="🪙",
    layout="wide",
)

# ── 커스텀 CSS ──
st.markdown("""
<style>
    /* 전체 테마 */
    .stApp { background-color: #0e1117; }

    /* 포스트 카드 */
    .post-card {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border-radius: 16px;
        padding: 20px;
        margin: 12px 0;
        border-left: 4px solid #e94560;
        color: #eee;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    .post-card-hot {
        border-left: 4px solid #ff6b35;
        background: linear-gradient(135deg, #1a1a2e 0%, #2a1a3e 100%);
        box-shadow: 0 0 20px rgba(233, 69, 96, 0.1);
    }
    .post-title {
        font-size: 18px;
        font-weight: bold;
        color: #fff;
        margin-bottom: 8px;
    }
    .post-content {
        font-size: 14px;
        line-height: 1.8;
        color: #d0d0d0;
        white-space: pre-wrap;
    }
    .score-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 12px;
        font-weight: bold;
        font-size: 13px;
        margin-right: 8px;
    }
    .score-hot { background: #e94560; color: white; }
    .score-mid { background: #ff8c00; color: white; }
    .score-low { background: #4a90d9; color: white; }
    .cat-badge {
        display: inline-block;
        background: rgba(255,255,255,0.1);
        padding: 4px 10px;
        border-radius: 8px;
        font-size: 12px;
        color: #aaa;
    }

    /* X 미리보기 */
    .x-preview {
        background: #000;
        border: 1px solid #333;
        border-radius: 16px;
        padding: 16px;
        color: #e7e9ea;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        max-width: 520px;
        font-size: 15px;
        line-height: 1.6;
        white-space: pre-wrap;
    }

    /* 통계 카드 */
    .stat-card {
        background: #1a1a2e;
        border-radius: 12px;
        padding: 16px;
        text-align: center;
        border: 1px solid #2a2a4e;
    }
    .stat-number { font-size: 28px; font-weight: bold; color: #e94560; }
    .stat-label { font-size: 13px; color: #888; margin-top: 4px; }
</style>
""", unsafe_allow_html=True)


# ── 타이틀 ──
st.title("🪙 크립토 자동 기사 생성기")
st.caption("CryptoYuna 스타일 · RSS 뉴스 + X 인플루언서 자동 수집 → 기사 생성 → 텍스트+이미지 패키지 저장")

# ── 사이드바 설정 ──
with st.sidebar:
    st.header("⚙️ 설정")

    st.markdown("### 📂 저장 위치")
    output_dir = st.text_input(
        "기사 저장 폴더",
        value=DEFAULT_OUTPUT_DIR,
        help="생성된 기사가 저장될 폴더 경로"
    )

    st.markdown("---")
    st.markdown("### 📰 뉴스 소스 선택")

    # ── 추천 소스 (중복 최소화 + 품질 최고) ──
    RECOMMENDED_FEEDS = {
        "🟠 CoinDesk", "📰 Cointelegraph", "🟣 Decrypt",
        "📈 Blockworks", "📊 The Block", "🌏 Wu Blockchain",
        "🔔 Watcher.Guru", "💹 CNBC Crypto",
        "🇰🇷 블록미디어",
    }

    feed_mode = st.radio(
        "소스 모드",
        ["⭐ 추천 소스 (9개, 중복 최소)", "📋 전체 소스 (22개)", "🛠 수동 선택"],
        index=0,
        help="추천: 품질 높은 대표 소스만. 전체: 모든 소스 (중복은 자동 제거됨)"
    )

    selected_feeds = []
    feed_categories = {
        "🔴 메이저 (추천)": ["🟠 CoinDesk", "📰 Cointelegraph", "🟣 Decrypt",
                              "📈 Blockworks", "📊 The Block"],
        "⚡ 속보/기타": ["🔵 CryptoNews", "⚡ Bitcoin Magazine", "🌏 Wu Blockchain",
                          "🪨 CryptoSlate", "📡 BeInCrypto", "🔔 Watcher.Guru", "🦅 CryptoPanic"],
        "🏦 기관/데이터": ["🏦 DL News", "💹 CNBC Crypto", "🐋 Whale Alert Blog",
                           "📉 Glassnode Blog", "🦎 CoinGecko Blog"],
        "🔬 리서치/DeFi": ["🔬 Messari", "🛡️ The Defiant", "📚 Coin Bureau"],
        "🇰🇷 한국 미디어": ["🇰🇷 블록미디어", "🇰🇷 디지털투데이", "🇰🇷 코인리더스"],
    }

    if feed_mode == "⭐ 추천 소스 (9개, 중복 최소)":
        selected_feeds = [f for f in RECOMMENDED_FEEDS if f in RSS_FEEDS]
    elif feed_mode == "📋 전체 소스 (22개)":
        selected_feeds = list(RSS_FEEDS.keys())
    else:
        for cat_name, feeds in feed_categories.items():
            with st.expander(cat_name, expanded=False):
                for feed in feeds:
                    if feed in RSS_FEEDS:
                        default_on = feed in RECOMMENDED_FEEDS
                        checked = st.checkbox(feed, value=default_on, key=f"feed_{feed}")
                        if checked:
                            selected_feeds.append(feed)

    st.markdown("---")
    st.markdown("### 🐦 X 인플루언서 소스")

    # ── 추천 인플루언서 (가장 뉴스 가치 높은 계정) ──
    RECOMMENDED_INFLUENCERS = {
        "🔔 Watcher Guru", "📊 Tier10k (db)",
        "🚀 Michael Saylor", "🚗 Elon Musk", "🇺🇸 Donald Trump",
        "😎 CZ (Binance)", "🐋 Lookonchain",
        "🇰🇷 CryptoYuna", "🇰🇷 코인니스",
    }

    inf_mode = st.radio(
        "인플루언서 모드",
        ["⭐ 추천 계정 (9개)", "📋 전체 계정 (30개)", "🛠 수동 선택"],
        index=0,
        help="추천: CryptoYuna가 자주 인용하는 핵심 계정만"
    )

    selected_influencers = []
    influencer_categories = {
        "🔔 속보/뉴스": ["🔔 Watcher Guru", "📊 Tier10k (db)", "🐳 Whale Alert", "🦅 ZachXBT"],
        "🚀 BTC 강세": ["🚀 Michael Saylor", "⚡ Samson Mow", "📊 Raoul Pal",
                         "💰 Cathie Wood", "🐂 Pompliano"],
        "🎯 트레이더/분석가": ["🎯 Willy Woo", "📉 Peter Schiff", "📐 Peter Brandt",
                              "🦈 Barry Silbert", "🏦 Tom Lee"],
        "😎 크립토 기업인": ["😎 CZ (Binance)", "🔵 Kevin O'Leary", "💎 Larry Fink"],
        "🌍 정치/매크로": ["🇺🇸 Donald Trump", "🚗 Elon Musk", "🌍 Mario Nawfal",
                           "📡 Unusual Whales", "💹 Jim Cramer"],
        "🇰🇷 한국": ["🇰🇷 CryptoYuna", "🇰🇷 김영훈 IQ276", "🇰🇷 Ki Young Ju", "🇰🇷 코인니스"],
        "🔗 DeFi/알트코인": ["🔗 Cobie", "📊 Will Clemente", "🧠 Arthur Hayes", "🐋 Lookonchain"],
    }

    if inf_mode == "⭐ 추천 계정 (9개)":
        selected_influencers = [inf for inf in RECOMMENDED_INFLUENCERS if inf in X_INFLUENCERS]
    elif inf_mode == "📋 전체 계정 (30개)":
        selected_influencers = list(X_INFLUENCERS.keys())
    else:
        for cat_name, influencers in influencer_categories.items():
            with st.expander(cat_name, expanded=False):
                for inf in influencers:
                    if inf in X_INFLUENCERS:
                        default_on = inf in RECOMMENDED_INFLUENCERS
                        checked = st.checkbox(inf, value=default_on, key=f"inf_{inf}")
                        if checked:
                            selected_influencers.append(inf)

    st.markdown("---")
    st.markdown("### 🎯 생성 설정")
    num_posts = st.slider("생성할 기사 수", 5, 30, 15)
    news_per_feed = st.slider("소스당 수집 수", 3, 10, 5)
    inf_per_account = st.slider("인플루언서당 수집 수", 1, 10, 3)
    min_score = st.slider("최소 이슈성 점수", 0, 50, 10)

    st.markdown("---")
    st.markdown("### 📊 점수 기준")
    st.markdown("""
    - **최신성** (40점): 최근 기사일수록 높음
    - **핫키워드** (30점): Trump, ETF, Musk 등
    - **복수 매체** (20점): 여러 매체 보도
    - **미디어** (10점): 이미지/영상 포함
    """)
    st.markdown("---")
    st.markdown(f"📰 RSS: **{len(selected_feeds)}**개 | 🐦 X: **{len(selected_influencers)}**개")


# ── 메인 영역 ──

# 생성 버튼
col_btn1, col_btn2, col_btn3 = st.columns([2, 2, 6])
with col_btn1:
    generate_btn = st.button("🚀 기사 자동 생성", type="primary", use_container_width=True)
with col_btn2:
    if st.button("📂 저장 폴더 열기", use_container_width=True):
        if os.path.exists(output_dir):
            os.startfile(output_dir) if os.name == 'nt' else os.system(f'open "{output_dir}"')
        else:
            st.warning("폴더가 아직 없습니다. 먼저 기사를 생성하세요.")

if generate_btn:
    if not selected_feeds and not selected_influencers:
        st.error("❌ 최소 1개 이상의 뉴스 소스 또는 인플루언서를 선택하세요!")
    else:
        # 저장 폴더 생성
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        batch_dir = os.path.join(output_dir, f"배치_{timestamp}")
        os.makedirs(batch_dir, exist_ok=True)

        # 1단계: 뉴스 수집
        st.markdown("### 📡 1단계: 뉴스 수집")
        progress_bar = st.progress(0)
        status_text = st.empty()

        def update_progress(pct, msg):
            progress_bar.progress(pct)
            status_text.text(msg)

        all_news = fetch_all_news(
            selected_feeds, news_per_feed, update_progress,
            influencer_names=selected_influencers,
            count_per_influencer=inf_per_account
        )
        rss_count = sum(1 for n in all_news if not n["source"].startswith("🐦"))
        x_count = sum(1 for n in all_news if n["source"].startswith("🐦"))
        status_text.text(f"✅ 총 {len(all_news)}개 수집 (RSS: {rss_count} / X: {x_count})")

        # 2단계: 중복 제거 & 필터
        st.markdown("### 🔍 2단계: 뉴스 선별")
        filtered = [n for n in all_news if n["score"]["total"] >= min_score]
        unique_news = deduplicate_news(filtered)
        top_news = unique_news[:num_posts]
        merged_count = sum(n.get("duplicate_count", 1) - 1 for n in unique_news)
        st.success(f"✅ {len(all_news)}개 수집 → 중복 {merged_count}개 병합 → 고유 {len(unique_news)}개 → 상위 {len(top_news)}개 선정")

        # 3단계: 기사 생성
        st.markdown("### ✍️ 3단계: CryptoYuna 스타일 기사 생성")
        posts = []
        gen_progress = st.progress(0)

        for i, news_item in enumerate(top_news):
            gen_progress.progress((i + 1) / len(top_news))
            post = generate_yuna_style_post(news_item)
            posts.append(post)

        gen_progress.progress(1.0)
        st.success(f"✅ {len(posts)}개 기사 생성 완료!")

        # 4단계: 파일 저장
        st.markdown("### 💾 4단계: 파일 저장")
        save_progress = st.progress(0)
        saved_results = []

        for i, post in enumerate(posts):
            save_progress.progress((i + 1) / len(posts))
            result = save_post_package(post, batch_dir, i + 1)
            saved_results.append(result)

        save_progress.progress(1.0)

        # 이미지 있는 기사 수 카운트
        with_images = sum(1 for r in saved_results if r.get("image_file"))
        st.success(f"✅ 저장 완료! (이미지 포함: {with_images}/{len(saved_results)}개)")

        # 저장된 기사를 세션에 보관
        st.session_state["posts"] = posts
        st.session_state["saved_results"] = saved_results
        st.session_state["batch_dir"] = batch_dir


# ── 생성 결과 표시 ──
if "posts" in st.session_state and st.session_state["posts"]:
    posts = st.session_state["posts"]
    saved_results = st.session_state.get("saved_results", [])
    batch_dir = st.session_state.get("batch_dir", "")

    st.markdown("---")
    st.markdown(f"## 📋 생성된 기사 ({len(posts)}건)")

    if batch_dir:
        st.info(f"📂 저장 위치: `{batch_dir}`")

    # 통계
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""<div class="stat-card">
            <div class="stat-number">{len(posts)}</div>
            <div class="stat-label">생성된 기사</div>
        </div>""", unsafe_allow_html=True)
    with col2:
        with_img = sum(1 for r in saved_results if r.get("image_file"))
        st.markdown(f"""<div class="stat-card">
            <div class="stat-number">{with_img}</div>
            <div class="stat-label">이미지 포함</div>
        </div>""", unsafe_allow_html=True)
    with col3:
        avg_score = sum(p["score"] for p in posts) / len(posts) if posts else 0
        st.markdown(f"""<div class="stat-card">
            <div class="stat-number">{avg_score:.0f}</div>
            <div class="stat-label">평균 점수</div>
        </div>""", unsafe_allow_html=True)
    with col4:
        categories = Counter(p["category"] for p in posts)
        top_cat = categories.most_common(1)[0][0] if categories else "-"
        st.markdown(f"""<div class="stat-card">
            <div class="stat-number" style="font-size:18px;">{top_cat}</div>
            <div class="stat-label">최다 카테고리</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("")

    # 기사 카드 표시
    for i, (post, saved) in enumerate(zip(posts, saved_results)):
        score = post["score"]
        score_class = "score-hot" if score >= 50 else "score-mid" if score >= 30 else "score-low"
        card_class = "post-card post-card-hot" if score >= 50 else "post-card"

        pub_short = post.get("pub_display", "").split("(")[0].strip() if post.get("pub_display") else ""
        time_tag = f"  |  🕐 {pub_short}" if pub_short else ""
        with st.expander(f"{post['emoji']} {post['title'][:50]}  |  점수: {score:.0f}{time_tag}  |  {post['category']}", expanded=(i < 3)):

            col_left, col_right = st.columns([3, 2])

            with col_left:
                st.markdown("**📝 포스트 내용:**")
                st.markdown(f"""<div class="x-preview">{post['text']}</div>""", unsafe_allow_html=True)

                # 복사 버튼
                st.code(post["text"], language=None)

            with col_right:
                st.markdown("**📊 정보:**")
                if post.get("pub_display"):
                    st.markdown(f"- 🕐 **{post['pub_display']}**")
                st.markdown(f"- 이슈성 점수: **{score:.0f}/100**")
                post_type_label = {"quote": "💬 인물발언형", "breaking": "🚨 속보형", "news": "📰 뉴스기사형"}.get(post.get("post_type", "news"), "📰 뉴스기사형")
                st.markdown(f"- 포스트 유형: {post_type_label}")
                st.markdown(f"- 카테고리: {post['category']}")
                st.markdown(f"- 대표 출처: {post['source']}")
                if post.get("merged_sources") and len(post["merged_sources"]) > 0:
                    other = ", ".join(post["merged_sources"][:4])
                    st.markdown(f"- 📡 동일 뉴스 {post['duplicate_count']}개 매체: {other}")
                if post.get("link"):
                    st.markdown(f"- [원문 보기]({post['link']})")

                # 이미지 표시
                if saved.get("image_file") and os.path.exists(saved["image_file"]):
                    st.markdown("**🖼️ 첨부 이미지:**")
                    try:
                        st.image(saved["image_file"], use_container_width=True)
                    except Exception:
                        st.caption("(이미지 미리보기 불가)")
                elif post.get("image_url"):
                    st.markdown("**🖼️ 이미지 URL:**")
                    try:
                        st.image(post["image_url"], use_container_width=True)
                    except Exception:
                        st.caption(f"URL: {post['image_url'][:80]}...")

                # 파일 위치
                if saved.get("folder"):
                    st.caption(f"📂 {saved['folder']}")

    # 전체 기사 일괄 미리보기
    st.markdown("---")
    st.markdown("### 📋 전체 기사 텍스트 (복사용)")
    all_texts = "\n\n" + "═" * 40 + "\n\n"
    all_texts = all_texts.join([
        f"[{i+1}/{len(posts)}] {p['category']}  |  🕐 {p.get('pub_display', '?')}\n{'─' * 30}\n{p['text']}"
        for i, p in enumerate(posts)
    ])
    st.text_area("전체 기사", value=all_texts, height=400, key="all_texts_area")
