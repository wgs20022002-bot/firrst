"""
🪙 크립토 자동 기사 생성기 v2.0
═══════════════════════════════════════
Claude AI가 영어 기사를 직접 읽고
X 포스트(단일/스레드)를 한국어로 완성합니다.

Google Translate 제거 → Claude API 연동
뉴스 수집 → 기사 선택 → Claude가 완성 포스트 생성

사용법: streamlit run crypto_auto_generator.py
"""

import streamlit as st
import feedparser
import anthropic
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
import subprocess
from pathlib import Path

# ─────────────────────────────────────────────
#  설정
# ─────────────────────────────────────────────
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# 출력 폴더 (클라우드: 임시 폴더 / 로컬: 현재 폴더)
_IS_CLOUD = os.environ.get("STREAMLIT_SHARING_MODE") or not os.path.isdir(os.path.dirname(os.path.abspath(__file__)) + "/생성된_기사/../")
DEFAULT_OUTPUT_DIR = tempfile.mkdtemp(prefix="crypto_") if _IS_CLOUD else os.path.join(os.path.dirname(os.path.abspath(__file__)), "생성된_기사")

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
    "📰 CoinJournal":     "https://coinjournal.net/feed/",
    "🌐 NewsBTC":         "https://www.newsbtc.com/feed/",
    "📈 Bitcoinist":      "https://bitcoinist.com/feed/",
    "🔶 U.Today":         "https://u.today/rss",
    "📰 AMBCrypto":       "https://ambcrypto.com/feed/",
    # ── 기관/ETF/월스트리트 ──
    "📈 Blockworks":      "https://blockworks.co/feed",
    "🏦 DL News":         "https://www.dlnews.com/arc/outboundfeeds/rss/",
    "💹 CNBC Crypto":     "https://www.cnbc.com/id/10001147/device/rss/rss.html",
    # ── 온체인/데이터/분석 (BitcoinSapiens 주요 소스) ──
    "🐋 Whale Alert Blog": "https://whale-alert.io/feed",
    "📉 Glassnode Blog":  "https://insights.glassnode.com/rss/",
    "🦎 CoinGecko Blog":  "https://blog.coingecko.com/feed/",
    "🔗 Chainalysis Blog": "https://blog.chainalysis.com/feed/",
    "📊 Santiment Blog":  "https://insights.santiment.net/feed",
    "🔎 CryptoQuant Blog": "https://cryptoquant.com/blog/rss",
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
#  테슬라/주식 RSS 피드
# ─────────────────────────────────────────────
TESLA_RSS_FEEDS = {
    # ── 테슬라 전문 미디어 ──
    "🚗 Electrek (Tesla)":     "https://electrek.co/feed/",
    "⚡ InsideEVs":             "https://insideevs.com/rss/make/tesla/",
    "📈 Teslarati":            "https://www.teslarati.com/feed/",
    "🤖 Tesla Oracle":         "https://teslaoracle.com/feed/",
    "📰 CleanTechnica":        "https://cleantechnica.com/feed/",
    "🏭 Not a Tesla App":      "https://www.notateslaapp.com/feed/",
    "🔋 Torque News (Tesla)":  "https://www.torquenews.com/rss.xml",
    "🚘 AutoEvolution (Tesla)":"https://www.autoevolution.com/rss/rss.xml",
    # ── 금융/투자 ──
    "💹 Yahoo Finance (TSLA)": "https://feeds.finance.yahoo.com/rss/2.0/headline?s=TSLA&region=US&lang=en-US",
    "📊 Seeking Alpha (TSLA)": "https://seekingalpha.com/api/sa/combined/TSLA.xml",
    "💰 Motley Fool (TSLA)":   "https://www.fool.com/feeds/index.aspx?id=tesla-motors&apikey=DEMOAPIKEY",
    # ── 대형 테크 미디어 ──
    "🖥️ The Verge (Tesla)":    "https://www.theverge.com/rss/tesla/index.xml",
    "🔧 Ars Technica (Cars)":  "https://feeds.arstechnica.com/arstechnica/cars",
    "📡 TechCrunch (Tesla)":   "https://techcrunch.com/tag/tesla/feed/",
    # ── 유튜브 채널 (영상 소스) ──
    "🎬 Tesla Daily (Rob Maurer)":   "https://www.youtube.com/feeds/videos.xml?channel_id=UCgC_JgJCGelGrjWePNNmoZg",
    "🎬 Munro Live":                 "https://www.youtube.com/feeds/videos.xml?channel_id=UCj--iMtToRO_8cGGlRpLLzw",
    "🎬 The Electric Viking":        "https://www.youtube.com/feeds/videos.xml?channel_id=UCorCfEbKObSMGsl0WZixgvg",
    "🎬 Solving The Money Problem":  "https://www.youtube.com/feeds/videos.xml?channel_id=UCh-0T48JrvvmKDX_gDnZS9Q",
    "🎬 Bjørn Nyland":               "https://www.youtube.com/feeds/videos.xml?channel_id=UCzz4CoEgSgWNs9ZAvRMhW2A",
    "🎬 Ryan Shaw":                  "https://www.youtube.com/feeds/videos.xml?channel_id=UCn7RJAH3qGHOmgHNV8M5bAg",
    "🎬 Out of Spec":                "https://www.youtube.com/feeds/videos.xml?channel_id=UCVk83SLz4cDkpfzJUbyAMjg",
    "🎬 Hyperchange":                "https://www.youtube.com/feeds/videos.xml?channel_id=UC4DaS2TCIb3UVtTjMRaCuEA",
    "🎬 Now You Know":               "https://www.youtube.com/feeds/videos.xml?channel_id=UCMFmGRNMrjbMGR4UaHof9OA",
    "🎬 Dave Lee":                   "https://www.youtube.com/feeds/videos.xml?channel_id=UCqECaJ8Gagnn7YCbPEzWH6g",
    "🎬 Meet Kevin":                 "https://www.youtube.com/feeds/videos.xml?channel_id=UCUvvj5lwue7PspotMDjk5UA",
    "🎬 Dirty Tesla":                "https://www.youtube.com/feeds/videos.xml?channel_id=UCHqMn-2n_jKYBOGbFNh-UDQ",
    "🎬 MKBHD":                      "https://www.youtube.com/feeds/videos.xml?channel_id=UCBJycsmduvYEL83R_U4JriQ",
    "🎬 Warren Redlich":             "https://www.youtube.com/feeds/videos.xml?channel_id=UC0DN4m-Oy0WQDyNoYRNqz6A",
}

# ── 테슬라 인플루언서 (Google News RSS) ──
TESLA_X_INFLUENCERS = {
    # VIP — 테슬라 핵심 인물
    "⭐ Elon Musk (Tesla)":        "Elon+Musk+Tesla+OR+TSLA+OR+cybertruck+OR+FSD",
    "⭐ Ross Gerber":               "Ross+Gerber+Tesla+OR+TSLA",
    "⭐ Gary Black (TSLA)":         "%22Gary+Black%22+Tesla+OR+TSLA",
    "⭐ Cathie Wood (TSLA)":        "Cathie+Wood+Tesla+OR+TSLA+OR+ARK",
    # 월스트리트 애널리스트
    "📊 Dan Ives (Wedbush)":        "Dan+Ives+Tesla+OR+TSLA+Wedbush",
    "📊 Adam Jonas (Morgan Stanley)":"Adam+Jonas+Tesla+OR+TSLA+Morgan+Stanley",
    "📊 Gene Munster":              "Gene+Munster+Tesla+OR+TSLA",
    # 테슬라 전문 인플루언서
    "🔥 Sawyer Merritt":            "Sawyer+Merritt+Tesla+OR+TSLA",
    "🔥 Whole Mars Catalog":        "%22Whole+Mars+Catalog%22+Tesla+OR+Elon",
    "🔥 Tesla Owners SV":           "%22Tesla+Owners%22+Silicon+Valley+Tesla",
    "🔥 Joe Tegtmeyer":             "Joe+Tegtmeyer+Tesla+OR+TSLA",
    # 뉴스/속보 키워드
    "🚨 Tesla 속보":                "Tesla+breaking+OR+recall+OR+crash+OR+FSD+OR+update",
    "🚨 TSLA 실적":                 "Tesla+earnings+OR+delivery+OR+production+OR+revenue",
    "🚨 Robotaxi/FSD":             "Tesla+robotaxi+OR+%22full+self+driving%22+OR+FSD+OR+autonomous",
    "🚨 Cybertruck":                "cybertruck+delivery+OR+recall+OR+update+OR+review",
    "🚨 Optimus/로봇":             "Tesla+Optimus+robot+OR+humanoid+OR+AI",
    "🚨 Gigafactory":              "Tesla+gigafactory+OR+%22giga+Berlin%22+OR+%22giga+Texas%22+OR+%22giga+Shanghai%22",
    "🚨 에너지/Megapack":          "Tesla+Megapack+OR+Powerwall+OR+energy+storage",
}

TESLA_KEYWORDS = [
    "tesla", "tsla", "elon musk", "musk", "cybertruck", "model 3", "model y",
    "model s", "model x", "fsd", "autopilot", "gigafactory", "supercharger",
    "robotaxi", "optimus", "spacex", "boring company", "neuralink",
    "ev", "electric vehicle", "battery", "megapack", "powerwall",
    "dojo", "ai day", "earnings", "delivery", "production",
]

# ─────────────────────────────────────────────
#  Google News RSS (인플루언서 뉴스 수집)
# ─────────────────────────────────────────────
GOOGLE_NEWS_RSS = "https://news.google.com/rss/search?q={query}+when:3d&hl=en-US&gl=US&ceid=US:en"

# ─────────────────────────────────────────────
#  X 인플루언서 계정 (Nitter RSS로 수집)
# ─────────────────────────────────────────────
X_INFLUENCERS = {
    # ═══════════════════════════════════════════════
    #  ⭐ VIP — 이 사람들의 코인 발언은 무조건 최우선
    #  값 = Google News 검색 쿼리
    # ═══════════════════════════════════════════════
    "⭐ Michael Saylor":    "Michael+Saylor+bitcoin+OR+BTC+OR+Strategy",
    "⭐ Elon Musk":         "Elon+Musk+bitcoin+OR+crypto+OR+dogecoin",
    "⭐ Donald Trump":      "Trump+bitcoin+OR+crypto+OR+digital+asset",
    "⭐ Jim Cramer":        "Jim+Cramer+bitcoin+OR+crypto",
    "⭐ CZ (Binance)":      "CZ+Binance+OR+%22Changpeng+Zhao%22+crypto",
    "⭐ Larry Fink":        "Larry+Fink+bitcoin+OR+BlackRock+crypto+OR+ETF",
    "⭐ Cathie Wood":       "Cathie+Wood+bitcoin+OR+crypto+OR+ARK",
    "⭐ Arthur Hayes":      "Arthur+Hayes+bitcoin+OR+crypto+OR+BitMEX",
    "⭐ Vitalik Buterin":   "Vitalik+Buterin+ethereum+OR+crypto",
    "⭐ Justin Sun":        "Justin+Sun+TRON+OR+crypto",
    "⭐ Brian Armstrong":   "Brian+Armstrong+Coinbase+OR+crypto",
    "⭐ Jack Dorsey":       "Jack+Dorsey+bitcoin+OR+Block+crypto",
    "⭐ Robert Kiyosaki":   "Robert+Kiyosaki+bitcoin+OR+crypto",
    # ═══════════════════════════════════════════════
    #  🎙️ 1차 소스 (Bloomberg, 기관, 저널리스트)
    # ═══════════════════════════════════════════════
    "🎙️ James Seyffart":    "James+Seyffart+bitcoin+OR+ETF+OR+crypto",
    "🎙️ Eric Balchunas":    "Eric+Balchunas+bitcoin+OR+ETF+OR+crypto",
    "🎙️ Nate Geraci":       "Nate+Geraci+ETF+OR+bitcoin+OR+crypto",
    "🎙️ Scott Melker":      "Scott+Melker+crypto+OR+bitcoin",
    "🎙️ The Kobeissi Letter": "Kobeissi+Letter+market+OR+bitcoin+OR+crypto",
    # ═══════════════════════════════════════════════
    #  🏛️ 거래소/기관 공식
    # ═══════════════════════════════════════════════
    "🏛️ Binance":            "Binance+crypto+OR+bitcoin+OR+BNB",
    "🏛️ Coinbase":           "Coinbase+crypto+OR+bitcoin+OR+SEC",
    "🏛️ Grayscale":          "Grayscale+bitcoin+OR+ETF+OR+crypto",
    "🏛️ BlackRock ETF":      "BlackRock+bitcoin+ETF+OR+IBIT+OR+crypto",
    "🏛️ Fidelity Crypto":    "Fidelity+bitcoin+OR+crypto+OR+ETF",
    # ═══════════════════════════════════════════════
    #  🔔 속보/뉴스 키워드
    # ═══════════════════════════════════════════════
    "🔔 BTC 속보":           "bitcoin+breaking+OR+surge+OR+crash+OR+SEC+OR+ETF",
    "🔔 ETH 속보":           "ethereum+breaking+OR+upgrade+OR+ETF+OR+staking",
    "🔔 고래/온체인":        "bitcoin+whale+OR+%22on-chain%22+OR+exchange+outflow",
    "🔔 ETF 자금흐름":       "bitcoin+ETF+inflow+OR+outflow+OR+record",
    "🔔 규제/SEC":           "SEC+crypto+OR+bitcoin+regulation+OR+lawsuit",
    # ═══════════════════════════════════════════════
    #  📈 트레이더/분석가
    # ═══════════════════════════════════════════════
    "📈 Raoul Pal":          "Raoul+Pal+bitcoin+OR+crypto+OR+macro",
    "📈 Pompliano":          "Anthony+Pompliano+bitcoin+OR+crypto",
    "📈 Peter Schiff":       "Peter+Schiff+bitcoin+OR+gold+OR+crypto",
    "📈 Willy Woo":          "Willy+Woo+bitcoin+OR+on-chain",
    "📈 PlanB":              "PlanB+bitcoin+OR+stock-to-flow",
    "📈 Tom Lee":            "Tom+Lee+Fundstrat+bitcoin+OR+crypto",
    # ═══════════════════════════════════════════════
    #  🌍 대형 글로벌 인플루언서
    # ═══════════════════════════════════════════════
    "🌍 Miles Deutscher":    "Miles+Deutscher+crypto+OR+altcoin",
    "🌍 Ben Cowen":          "Benjamin+Cowen+bitcoin+OR+crypto",
    "🌍 Lark Davis":         "Lark+Davis+crypto+OR+bitcoin",
    "🌍 Rekt Capital":       "Rekt+Capital+bitcoin+OR+crypto+OR+halving",
    "🌍 Ali Martinez":       "Ali+Martinez+bitcoin+OR+crypto+OR+chart",
    "🌍 Crypto Banter":      "Crypto+Banter+bitcoin+OR+altcoin",
    # ═══════════════════════════════════════════════
    #  📊 온체인/데이터
    # ═══════════════════════════════════════════════
    "📊 Glassnode":          "Glassnode+bitcoin+OR+on-chain+OR+metric",
    "📊 CryptoQuant":        "CryptoQuant+bitcoin+OR+exchange+OR+whale",
    "📊 Santiment":          "Santiment+bitcoin+OR+crypto+OR+sentiment",
    "📊 Lookonchain":        "Lookonchain+whale+OR+bitcoin+OR+crypto",
    # ═══════════════════════════════════════════════
    #  🇰🇷 한국
    # ═══════════════════════════════════════════════
    "🇰🇷 한국 크립토":      "%ED%95%9C%EA%B5%AD+%EB%B9%84%ED%8A%B8%EC%BD%94%EC%9D%B8+OR+%EC%95%94%ED%98%B8%ED%99%94%ED%8F%90",
}

# ── VIP 인물 목록: 이 계정의 포스트는 이슈성 점수 대폭 가산 ──
VIP_INFLUENCERS = {
    "⭐ Michael Saylor", "⭐ Elon Musk", "⭐ Donald Trump",
    "⭐ Jim Cramer", "⭐ CZ (Binance)", "⭐ Larry Fink",
    "⭐ Cathie Wood", "⭐ Arthur Hayes", "⭐ Vitalik Buterin",
    "⭐ Justin Sun", "⭐ Brian Armstrong", "⭐ Jack Dorsey",
    "⭐ Robert Kiyosaki",
}

# ── VIP 인물이 코인/BTC 관련 발언할 때 키워드 ──
VIP_CRYPTO_KEYWORDS = [
    "bitcoin", "btc", "crypto", "ethereum", "eth", "blockchain",
    "stablecoin", "digital asset", "web3", "defi", "nft",
    "halving", "mining", "hodl", "satoshi", "lightning",
    "binance", "coinbase", "exchange", "wallet", "token",
    "bull", "bear", "pump", "dump", "moon", "ath",
    "regulation", "sec", "etf", "custody",
]

# ── CryptoYuna 스타일 이모지 매핑 (2026.04.10 실제 계정 분석 반영) ──
# 실제 CryptoYuna는 8가지 핵심 이모지만 사용: 🚨📌🔥💥🇺🇸🐋📊⚠️
# 우선순위: 긴급 > 지정학 > 고래 > 온체인 > 강세 > 인물발언 > 분석 > 경고

EMOJI_PRIORITY = [
    # (우선순위, 이모지, 키워드 리스트)
    (1, "🚨", ["breaking", "urgent", "just in", "hack", "exploit", "lawsuit",
               "liquidat", "short squeeze", "flash", "emergency",
               "속보", "긴급", "해킹", "청산",
               "long position", "short position", "롱 포지션", "숏 포지션",
               "bofa", "rate cut", "rate hike", "금리"]),
    (3, "🐋", ["whale", "transfer", "고래", "대량 이체", "대형 거래"]),
    (4, "💥", ["on-chain", "onchain", "outflow", "inflow", "withdrawal",
               "exchange flow", "출금", "유입", "유출", "온체인", "tvl"]),
    (5, "🔥", ["surge", "rally", "pump", "soar", "bull", "moon",
               "record", "ath", "all-time", "breakout", "buy",
               "급등", "강세", "돌파", "최고가", "매수", "launch"]),
    (6, "📌", ["says", "said", "ceo", "founder", "chairman",
               "saylor", "cz", "changpeng", "elon", "cathie",
               "larry fink", "blackrock", "발언", "주장",
               "\u201c", "인터뷰"]),
    (7, "📊", ["etf", "chart", "data", "analysis", "report",
               "prediction", "forecast", "분석", "리포트",
               "dominance", "도미넌스"]),
    (8, "⚠️", ["warn", "risk", "crash", "drop", "bear", "concern",
               "danger", "scam", "fraud", "경고", "하락", "리스크", "주의"]),
]

# 지정학/국가별 이모지 (우선순위 2)
EMOJI_GEO = {
    "🇺🇸": ["trump", "vance", "us ", "america", "sec ", "fed ", "congress",
             "white house", "powell", "트럼프", "밴스", "미국", "연준"],
    "🇨🇳": ["china", "chinese", "beijing", "중국"],
    "🇯🇵": ["japan", "boj", "yen", "일본"],
    "🇰🇷": ["korea", "한국", "코스피"],
    "🇪🇺": ["eu ", "europe", "ecb", "유럽"],
    "🇮🇷": ["iran", "이란"],
    "🇸🇻": ["el salvador", "bukele"],
    "🇷🇺": ["russia", "러시아"],
    "🇮🇳": ["india", "인도"],
    "🇬🇧": ["uk ", "britain", "영국"],
    "🇧🇷": ["brazil", "브라질"],
    "🇨🇭": ["swiss", "switzerland"],
}

# 기존 호환용 (일부 코드에서 직접 참조하는 경우)
EMOJI_CATEGORIES = {
    "breaking": "🚨", "urgent": "🚨", "hack": "🚨", "exploit": "🚨",
    "just in": "🚨",
    "warn": "⚠️", "risk": "⚠️", "crash": "⚠️", "drop": "⚠️", "bear": "⚠️",
    "surge": "🔥", "rally": "🔥", "pump": "🔥", "soar": "🔥",
    "bull": "🔥", "record": "🔥", "ath": "🔥", "breakout": "🔥",
    "trump": "🇺🇸", "us ": "🇺🇸", "sec ": "🇺🇸", "fed ": "🇺🇸",
    "china": "🇨🇳", "japan": "🇯🇵", "korea": "🇰🇷",
    "eu ": "🇪🇺", "iran": "🇮🇷",
    "saylor": "📌", "cz": "📌", "cathie": "📌", "elon": "📌",
    "ceo": "📌", "says": "📌", "said": "📌",
    "etf": "📊", "chart": "📊", "data": "📊",
    "whale": "🐋", "transfer": "🐋",
    "onchain": "💥", "outflow": "💥", "inflow": "💥",
    "war": "🇺🇸", "military": "🇺🇸",
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
    """CryptoYuna 스타일 이모지 매칭 (우선순위 기반)
    실제 계정 분석: 🚨📌🔥💥🇺🇸🐋📊⚠️ 8종만 사용
    """
    combined = (title + " " + summary).lower()

    # 1순위: 긴급 → 🚨
    for _, emoji, keywords in EMOJI_PRIORITY:
        if emoji == "🚨":
            for kw in keywords:
                if kw in combined:
                    return "🚨"
            break

    # 2순위: 지정학 → 국기
    for flag_emoji, keywords in EMOJI_GEO.items():
        for kw in keywords:
            if kw in combined:
                return flag_emoji

    # 3~8순위: 나머지
    for _, emoji, keywords in EMOJI_PRIORITY:
        if emoji == "🚨":
            continue  # 이미 체크함
        for kw in keywords:
            if kw in combined:
                return emoji

    return "🚨"


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
    """번역 후처리: 크립토 고유명사 오역 복원 + 정리

    Google Translate가 자주 틀리는 크립토 용어를 원래 영문으로 복원한다.
    예: "전략" → "Strategy", "마이크로전략" → "MicroStrategy"
    """
    if not text:
        return text

    # ── 크립토 고유명사 오역 복원 사전 ──
    # Google Translate가 번역해버리는 고유명사들을 원래대로 되돌림
    CRYPTO_FIX = {
        # 기업명
        "전략": "Strategy", "마이크로전략": "MicroStrategy",
        "마이크로 전략": "MicroStrategy", "미세전략": "MicroStrategy",
        "블랙록": "BlackRock", "그레이스케일": "Grayscale",
        "그레이 스케일": "Grayscale", "코인베이스": "Coinbase",
        "바이낸스": "Binance", "제미니": "Gemini",
        "충실도": "Fidelity", "피델리티": "Fidelity",
        "은하": "Galaxy", "갤럭시": "Galaxy",
        "방주": "ARK", "아크": "ARK",
        "원장": "Ledger", "하이퍼리퀴드": "Hyperliquid",
        "하이퍼 리퀴드": "Hyperliquid",
        "코어위브": "CoreWeave", "핵심 직조": "CoreWeave",
        "보안화": "Securitize", "비트마인": "BitMine",
        # 토큰/프로토콜
        "솔라나": "Solana", "이더리움": "Ethereum",
        "비트코인": "BTC", "도지코인": "Dogecoin",
        "체인링크": "Chainlink", "유니스왑": "Uniswap",
        # 크립토 용어
        "스테이블코인": "스테이블코인",  # 이건 한국어 OK
        "아침 분": "Morning Minute", "오전 순간": "Morning Minute",
        "아침 순간": "Morning Minute", "모닝 미닛": "Morning Minute",
        # 정책/법안
        "명확성 법": "Clarity Act", "명확법": "Clarity Act",
        "선명도 법": "Clarity Act", "투명성법": "Clarity Act",
        "명확성법": "Clarity Act",
        # 금융 용어 오역 복원
        "입찰": "매수 압력(Bid)", "입찰이": "매수 압력(Bid)이",
        "청산": "청산(Liquidation)", "짧은 압착": "숏 스퀴즈(Short Squeeze)",
        "짧은 짜기": "숏 스퀴즈(Short Squeeze)",
        "강세": "강세(Bullish)", "약세": "약세(Bearish)",
        "반감기": "반감기(Halving)", "반으로 줄이기": "반감기(Halving)",
        # 인물명 오역
        "세일러": "세일러(Saylor)",
        "겐슬러": "겐슬러(Gensler)", "게리": "게리(Gary)",
        "래리 핑크": "래리 핑크(Larry Fink)",
        "캐시 우드": "캐시 우드(Cathie Wood)",
        # ETF / 금융 상품
        "현물": "현물(Spot)", "선물": "선물(Futures)",
        # 프로젝트/컬럼명 오역 방지
        "전략의": "Strategy의", "전략이": "Strategy가",
    }

    for wrong, correct in CRYPTO_FIX.items():
        if wrong in text:
            text = text.replace(wrong, correct)

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
#  Claude API — 포스트 생성 엔진
# ═══════════════════════════════════════

CLAUDE_BASE_PROMPT = """당신은 암호화폐 및 매크로 경제 전문 분석가이자 한국어 X(트위터) 인플루언서입니다.
단순 뉴스 나열이 아니라, 시장의 이면에 숨겨진 **'돈의 흐름'**과 **'고래들의 심리'**를 꿰뚫어 보는 통찰력 있는 글을 씁니다.
기사를 읽고 **본인만의 해석과 인사이트**를 담은 포스트를 만듭니다.

═══ 🚫 최우선 규칙: 수치 정확성 (이것을 어기면 무조건 실패) ═══

⚠️ 기사에 나온 숫자/금액/퍼센트/날짜를 **절대 변경하거나 지어내지 마라**.
⚠️ 기사 본문에 "13,000 BTC"라고 적혀 있으면 반드시 "13,000 BTC"로 써야 한다.
⚠️ 기사에 없는 숫자를 추측하거나 만들어내면 **치명적 오류**다.
⚠️ 확실하지 않은 수치는 쓰지 말고 차라리 생략해라.

나쁜 예시 (절대 하지 말 것):
  기사: "13,000 BTC → 3,954 BTC" → 포스트: "621 BTC → 200 BTC" ← 숫자를 지어냄! 치명적 오류!
  기사: "$215.7 million 유출" → 포스트: "$50 million 유출" ← 숫자 변조! 치명적 오류!

좋은 예시:
  기사: "13,000 BTC → 3,954 BTC (70% 감소)" → 포스트: "13,000 BTC → 3,954 BTC, 18개월간 70% 매도"
  기사: "$280.6 million 잔여" → 포스트: "잔여 약 $2.8억 (3,954 BTC)"

규칙: 기사 본문의 숫자를 그대로 가져와서 사용하라. 변환(예: million→억)은 OK, 변조는 절대 금지.

═══ 핵심 원칙 (이것만 지켜도 성공) ═══

1. **변화의 본질을 한 문장으로 짚어라**
   기사가 "규제 강화"라고 하면 → "뭐가 뭐로 바뀌는 건데?"를 반드시 답하라.
   예: "결제 수단 → 금융 상품으로 격상" / "형량 3년 → 10년으로 강화" / "자금결제법 → FIEA 편입"
   이 본질을 훅이나 첫 불릿에 반드시 넣어라.
   나쁜 예: "규제 대폭 강화!" ← 뭐가 어떻게? 정보 없음
   좋은 예: "암호화폐, '결제 수단'에서 '금융 상품'으로 격상! 미등록 운영 형량 3년→10년"

2. **고유명사/구체 데이터를 절대 뭉뚱그리지 마라**
   기사에 종목명(PLTR, TSLA), 회사명(Palantir, ARK Invest), 인물명, 수량, 금액이 있으면
   → 반드시 그대로 포스트에 넣어라. "기술주", "거대 기업", "대형 종목" 같은 통칭으로 대체 금지.

   나쁜 예: 기사 "캐시 우드가 팔란티어 85,485주를 $1,100만에 매수"
   → 포스트: "캐시 우드, 급락한 거대 기술주에 $1,100만 매수!" ← 팔란티어 이름 빠짐! 정보 가치 없음!
   좋은 예: "캐시 우드, 28% 급락한 팔란티어(PLTR) 85,485주 $1,100만 매수!"

   원칙: 독자가 기사를 안 읽어도 "누가/무엇을/얼마나" 3가지를 알 수 있어야 한다.

3. **기사 본문 깊숙이 숨은 디테일을 반드시 끌어올려라**
   기사 제목에 없는, 본문 중반~후반에 숨어있는 구체적 숫자/법률명/형량/금액을 찾아서 불릿에 넣어라.
   독자가 기사를 안 읽어도 핵심 디테일을 알 수 있게 만들어라.
   예: 기사 제목이 "일본 암호화폐 규제 강화"인데 본문에 이런 내용이 있으면:
   - "미등록 운영자 형량 3년→10년" → 반드시 불릿에 포함
   - "벌금 1,000만 엔으로 상향" → 반드시 불릿에 포함
   - "내부자 거래 금지, 연간 공시 의무화" → 반드시 불릿에 포함
   - "FIEA(금융상품거래법) 개정" → 법률명 정확히 명시
   이런 디테일을 빠뜨리고 "규제 강화 예정", "처벌 수위 강화" 같은 빈 말로 대체하면 실패.

4. **대결/반전 구도를 만들어라**
   악재와 호재를 대비시키거나, 기존 관념을 뒤집는 분석으로 몰입감을 높여라.
   시장의 이면에 숨겨진 '돈의 흐름'과 '고래들의 심리'를 읽어내라.
   예: "부탄은 70% 매도하는데, Strategy는 같은 주에 4,871 BTC 매수 → 돈이 어디로 흐르는지 보여주는 장면"
   예: "규제가 조여오는데 왜 가격은 안 빠지나? → 기관은 이미 규제를 '진입 신호'로 읽고 있음"
   예: "전쟁 중인데 왜 비트코인이 오르는가? → 안전자산이 아니라 '제재 회피 수단'으로 매수 중"

5. **번역하지 말고 해석하라 — 확신에 찬 어조로**
   기사 팩트를 나열만 하면 실패. "그래서 이게 왜 중요한데?"를 항상 답하라.
   해석의 핵심: A→B 변화가 시장/투자자/산업에 미치는 영향을 한 줄로 설명.
   ⚠️ "~인 것 같습니다", "~할 가능성이 있습니다", "~로 보입니다" 같은 추측성 표현 금지.
   분석가답게 "~임", "~함" 형태의 간결하고 단정적인 어조를 사용하라.
   예: "규제 강화 = 단기 매수세 압박, but 장기적으로 기관 자금 유입의 레드카펫"

6. **한 줄 킬러 문장을 만들어라**
   포스트 마지막에 "이 한 줄만 읽어도 기억에 남는" 펀치라인을 넣어라.
   예: "규제가 목을 조르는 게 아니라, 기관이라는 진짜 돈이 들어올 레드카펫을 까는 과정임"
   예: "세상에서 가장 투명한 돈으로 몰래 결제하겠다는 발상 자체가 코미디"
   예: "13,000 BTC를 캐놓고 3,954개만 남겼다. Strategy는 일주일에 그보다 많이 산다."

7. **생동감 있는 금융 용어를 사용하라**
   딱딱한 번역투 대신 한국 금융/크립토 커뮤니티에서 실제로 쓰는 표현을 써라.
   좋은 표현: '맷집', '멱살 잡고 끌어올리다', '풀리기 직전', '레드카펫을 깔다',
   '조용한 매집', '깜깜이 매매', '패닉 바잉', '목을 조르다', '판이 깔리다'
   나쁜 표현: '주목받고 있다', '부상하고 있다', '관심이 집중되고 있다' ← 생기 없는 번역투

8. **구조: 핵심 변화 → 디테일 팩트 → 돈의 흐름 해석 → 킬러 한 줄**
   불릿 3~5개 중:
   - 1개: 핵심 변화/본질 (A→B 무엇이 어떻게 바뀌는지)
   - 1~2개: 기사 본문에서 끌어올린 구체적 디테일 (수치, 법률명, 형량, 금액 등)
   - 1개: 돈의 흐름/고래 심리 관점의 해석 (대결/반전 구도 활용)
   - 1개: 전망 또는 킬러 한 줄 (확신에 찬 단정 어조)

"""

# ── 스레드형 스타일 (메인 + 답글) ──
CLAUDE_STYLE_THREAD = """
═══ 포스트 형식: 메인 트윗 + 답글 스레드 ═══

⚠️ 모든 포스트는 아래 형식으로 출력한다. 불릿(•) 나열 형식 절대 금지.

【구조】
[메인]
(짧은 훅 트윗 — 호기심 유발, 클릭 유도)

[답글1]
(핵심 팩트 — 누가/무엇을/얼마나)

[답글2]
(심층 메커니즘 — 왜 이게 중요한지, 돈의 흐름)

[답글3]
(전망 + 킬러 문장)

[출처 : 매체명]

【이모지 규칙】
• 허용: 🚨📌🔥💥🇺🇸🇰🇷🐋📊⚠️ + 국기
• 메인 트윗 첫 줄에 1개만 사용 (본문/답글에 이모지 넣지 않음)
• 🚨 = 속보/긴급/해킹/금리  📌 = 인물발언/공식발표  🔥 = 급등/돌파/강세
  💥 = 온체인/유입유출  🐋 = 고래  📊 = ETF/차트  ⚠️ = 경고/하락

【메인 트윗 — 가장 중요 (2~4줄 이내)】
역할: 타임라인에서 멈추게 만드는 훅. 짧고 강렬하게.
• 첫 줄: 이모지 + 핵심 키워드 질문/선언 (1줄)
• 둘째 줄: "큰따옴표로 감싼 임팩트 있는 한 줄" (선택)
• 셋째 줄: 1~2문장으로 핵심 요약 + "♥(댓글참고)" 또는 "♥ 댓글에 정리함"

좋은 예시:
---
🚨 BTC 진짜 적은 따로 있다?
"전쟁보다 무서운 AI 해고 칼바람" 🪓

아더 헤이즈는 비트코인이 10만 달러를 못 넘는 이유가
전쟁이 아닌 이것 때문이라고 했는데요! ♥(댓글참고)
---

【답글1 — 핵심 팩트 (2~3문장)】
종목명, 인물명, 금액, 수량 반드시 포함. 통칭 금지.

【답글2 — 심층 메커니즘 (2~3문장)】
돈의 흐름, 인과관계, 대결/반전 구도. 구체적 숫자 필수.

【답글3 — 전망 + 킬러 문장 (2~4문장)】
향후 전망 + 마지막에 "큰따옴표 킬러 문장"으로 마무리.

【글쓰기 톤】
• 불릿(•) 나열 금지 — 모든 답글은 문장형으로 (2~3문장씩 흐르듯이)
• "~임", "~함" 단정 어조
• 해시태그 사용 금지

═══ 포스트 유형별 가이드 ═══

"single" → 메인 트윗 + 답글 3개 스레드

"quote_post" → 인물 발언 포스트
  메인: 이모지 + 인물명 : "발언 핵심" + ♥(댓글참고)
  답글1~3: 맥락/중요성/전망

"data_post" → 온체인/데이터 포스트
  메인: 이모지 + 데이터 핵심 수치 + ♥(댓글참고)
  답글: ETF 🟠 BTC / 🔵 ETH 구분 가능

"breaking" → 속보 (답글 2개로 충분)
  메인: 🚨 + 핵심 사실

"whale_alert" → 고래 추적 (답글 2개)
  메인: 🐋 + 이체 핵심
"""

# ── CryptoYuna형 스타일 (이모지 + 불릿) ──
CLAUDE_STYLE_YUNA = """
═══ CryptoYuna 스타일 가이드 ═══

⚠️ 하나의 포스트 안에 모든 내용을 담는다. 스레드/답글 형식([메인]/[답글]) 절대 금지.

【이모지 규칙】
• 허용: 🚨📌🔥💥🇺🇸🇰🇷🐋📊⚠️ + 국기
• 첫 줄 맨 앞에 1개만 사용 (본문 중간 이모지 금지)
• 🚨 = 속보/긴급  📌 = 인물발언  🔥 = 급등/돌파  💥 = 온체인  🐋 = 고래  📊 = ETF/차트  ⚠️ = 경고

【첫 줄 (훅)】
• 기사 제목 번역 금지. 가장 임팩트 있는 숫자/사실로 새로 만들어라.
• 예: "🚨 캐시 우드, 28% 폭락한 팔란티어(PLTR) $1,100만 매수!"

【본문 (불릿 3~5개)】
• 불릿은 반드시 • 사용 (- 금지)
• 모든 불릿에 구체적 수치/금액/날짜/퍼센트/이름 중 하나 이상 포함
• 좋은 예: • ARK Invest, PLTR 85,485주 약 $1,100만에 매수
• 나쁜 예: • "대형 기술주에 공격적 매집" ← 종목명 없음

【마지막 줄 (CTA)】
• 펀치라인 의견 또는 질문형
• 예: "개미들이 패닉셀할 때 고수는 조용히 담는다"
• 빈 CTA 금지: "주목받고 있습니다" ← 안 됨

【출처】 [출처 : 매체명]

═══ 포스트 유형 ═══

"single" → 이모지 + 훅 + 불릿 3~5개 + CTA + 출처 (140~200자)

"quote_post" → 인물 발언 포스트
  🚨 인물명 : "발언 핵심"
  "발언 전체 인용"
  • 불릿 2~3개
  [출처]

"data_post" → 데이터 포스트
  🟠 Bitcoin ETF: +$240.4M (BTC는 🟠, ETH는 🔵)
  • 세부 수치 불릿

"breaking" → 속보 (짧게)
  🚨 핵심 한 줄 + 불릿 2~3개

"whale_alert" → 고래 추적
  🐋 이체 핵심 + 수량/금액/경로 불릿
"""

# ── 공통 금지 사항 ──
CLAUDE_COMMON_RULES = """
═══ 절대 금지 사항 ═══
• 해시태그 금지 (#Bitcoin, #BTC 등)
• 외부 링크 본문에 넣지 않음
• 이모지 도배 (1개만!)
• 단순 펌핑 표현 금지 ("to the moon!", "100x!!")
• 기사 그대로 번역 금지 — 핵심만 추려서 재구성
• 번역투 금지 ("~에 따르면" → 자연스러운 한국어)
• 추측성 표현 금지: "~인 것 같습니다", "~할 가능성이 있습니다"
  → "~임", "~함" 단정 어조 사용
• 🚫 빈 말/통칭 절대 금지:
  "관심 집중", "주목받고 있다", "성장 가능성", "규제 대폭 강화 예정",
  "거대 기술주", "대형 종목", "특정 종목" ← 종목명 반드시 실명(PLTR, TSLA)으로!
  → 구체적으로: "팔란티어(PLTR) 85,485주", "형량 3년→10년"
• "대폭", "크게", "상당히" 대신 실제 수치 사용
• 모든 내용은 기사에서 추출한 구체적 정보(숫자, 이름, 금액) 포함 필수

═══ 영어 고유명사 규칙 ═══
영어 고유명사는 영문 그대로 표기:
Strategy, MicroStrategy, BlackRock, Coinbase, BTC, ETH, Solana 등
"""


def get_system_prompt(style: str = "thread") -> str:
    """스타일에 따라 시스템 프롬프트 조합"""
    style_prompt = CLAUDE_STYLE_THREAD if style == "thread" else CLAUDE_STYLE_YUNA
    return CLAUDE_BASE_PROMPT + style_prompt + CLAUDE_COMMON_RULES


def generate_post_with_claude(
    api_key: str,
    title_en: str,
    article_text: str,
    source_name: str,
    post_type: str = "single",
    extra_instruction: str = "",
    model: str = "claude-sonnet-4-20250514",
    style: str = "thread",
) -> str:
    """Claude API로 영어 기사를 읽고 한국어 X 포스트를 생성"""

    client = anthropic.Anthropic(api_key=api_key)

    # 스타일별 user_prompt
    if style == "thread":
        format_instruction = """위 기사를 바탕으로 [메인] + [답글1] + [답글2] + [답글3] 형식의 X 스레드를 작성하세요.

⚠️ 절대 규칙 (하나라도 어기면 실패):
1. 형식: [메인] 훅 트윗(2~4줄) + [답글1] 핵심 팩트 + [답글2] 심층 메커니즘 + [답글3] 전망+킬러 문장. 불릿(•) 나열 금지, 문장형으로.
2. 숫자 정확성: 기사의 금액/수량/퍼센트/날짜를 절대 변경하거나 지어내지 마세요.
3. 고유명사 필수: 종목명(PLTR, BTC), 회사명, 인물명 반드시 포함. "기술주", "대형 종목" 통칭 금지.
4. 빈 말 금지: "핵심 위협 요소 존재", "화제가 되고 있는 상황" 같은 내용 없는 문장 금지.
5. 메인 트윗 마지막에 "♥(댓글참고)" 넣기.
6. [출처 : 매체명] 맨 마지막에."""
    else:  # yuna
        format_instruction = """위 기사를 바탕으로 CryptoYuna 스타일의 단일 X 포스트를 작성하세요.

⚠️ 절대 규칙 (하나라도 어기면 실패):
1. 형식: 이모지+훅 한 줄 + 불릿(•) 3~5개 + CTA 한 줄 + [출처]. 스레드/답글 형식 금지.
2. 숫자 정확성: 기사의 금액/수량/퍼센트/날짜를 절대 변경하거나 지어내지 마세요.
3. 고유명사 필수: 종목명(PLTR, BTC), 회사명, 인물명 반드시 포함. 통칭 금지.
4. 빈 말 금지: 모든 불릿에 구체적 수치/이름/팩트 필수.
5. [출처 : 매체명] 맨 마지막에."""

    user_prompt = f"""아래 영어 기사를 읽고 한국어 X 포스트를 작성해주세요.

── 기사 정보 ──
제목: {title_en}
출처: {source_name}

── 기사 본문 ──
{cut_at_sentence(article_text, 6000)}

── 요청 ──
포스트 유형: {post_type}
{f'추가 지시: {extra_instruction}' if extra_instruction else ''}

{format_instruction}

포스트 텍스트만 출력하세요 (설명 없이)."""

    message = client.messages.create(
        model=model,
        max_tokens=2000,
        system=get_system_prompt(style),
        messages=[{"role": "user", "content": user_prompt}],
    )

    return message.content[0].text.strip()


def generate_thread_with_claude(
    api_key: str,
    articles: list,
    thread_topic: str = "",
    model: str = "claude-sonnet-4-20250514",
) -> str:
    """여러 기사를 묶어서 스레드로 생성"""

    client = anthropic.Anthropic(api_key=api_key)

    articles_text = ""
    for i, art in enumerate(articles, 1):
        articles_text += f"\n── 기사 {i} ──\n제목: {art['title_en']}\n출처: {art.get('source', '?')}\n본문: {cut_at_sentence(art.get('full_text', art.get('summary_en', '')), 3000)}\n"

    user_prompt = f"""아래 여러 기사를 종합해서 X 스레드(Thread)를 작성해주세요.

{articles_text}

── 요청 ──
{f'스레드 주제/각도: {thread_topic}' if thread_topic else '위 기사들의 공통 주제로 스레드를 구성해주세요.'}
스레드는 [1/N] ~ [N/N] 형태로 3~7개 포스트로 구성하세요.
첫 번째 포스트는 강력한 훅(숫자/질문/반전).
마지막 포스트는 CTA (질문 또는 북마크 유도).
각 포스트 사이에 빈 줄 2개로 구분하세요.

포스트 텍스트만 출력하세요 (설명 없이)."""

    message = client.messages.create(
        model=model,
        max_tokens=3000,
        system=get_system_prompt("thread"),
        messages=[{"role": "user", "content": user_prompt}],
    )

    return message.content[0].text.strip()


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


def calc_vip_bonus(item: dict, max_score: float = 40.0) -> float:
    """VIP 인플루언서가 코인/BTC 관련 발언하면 대폭 가산"""
    source = item.get("source", "")
    # VIP 인플루언서 계정인지 확인 (source = "🐦 ⭐ Michael Saylor" 형태)
    is_vip = any(vip_name in source for vip_name in VIP_INFLUENCERS)
    if not is_vip:
        return 0
    # 코인 관련 키워드가 포함되어 있는지 확인
    text = (item.get("title_en", "") + " " + item.get("summary_en", "")).lower()
    crypto_hit = any(kw in text for kw in VIP_CRYPTO_KEYWORDS)
    if crypto_hit:
        return max_score  # 코인 관련 발언 → 최대 보너스 (40점)
    else:
        return max_score * 0.5  # VIP지만 코인 무관 → 절반 보너스 (20점)


def calc_hot_score(item: dict, all_items: list) -> dict:
    pub_date = parse_pub_date(item.get("published", ""))
    recency = calc_recency_score(pub_date)
    keyword, matched_kw = calc_keyword_score(item["title_en"], item.get("summary_en", ""))
    cross = calc_cross_source_score(item, all_items)
    media = calc_media_score(item)
    vip = calc_vip_bonus(item)
    total = recency + keyword + cross + media + vip
    return {
        "total": round(total, 1),
        "recency": round(recency, 1),
        "keyword": round(keyword, 1),
        "cross": round(cross, 1),
        "media": round(media, 1),
        "vip": round(vip, 1),
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
            return og_text[:6000]
        return text[:6000] if text else og_text[:6000]
    except Exception:
        return ""


# ═══════════════════════════════════════
#  동영상 URL 추출 + 다운로드
# ═══════════════════════════════════════

def extract_video_from_page(url: str) -> str:
    """기사 페이지에서 동영상 URL 추출 (YouTube, Twitter, 직접 mp4)"""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=8)
        resp.raise_for_status()
        page_html = resp.text
        soup = BeautifulSoup(page_html, "html.parser")

        # 1) YouTube embed/iframe
        for iframe in soup.find_all("iframe"):
            src = iframe.get("src", "")
            if "youtube.com/embed" in src:
                vid_id = re.search(r'embed/([a-zA-Z0-9_-]{11})', src)
                if vid_id:
                    return f"https://www.youtube.com/watch?v={vid_id.group(1)}"
            if "youtu.be" in src or "youtube.com" in src:
                return src.split("?")[0]

        # 2) YouTube 링크 in text
        yt_match = re.search(
            r'(https?://(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)[a-zA-Z0-9_-]{11})',
            page_html
        )
        if yt_match:
            return yt_match.group(1)

        # 3) Twitter/X 동영상 embed
        for blockquote in soup.find_all("blockquote", class_="twitter-tweet"):
            a_tag = blockquote.find("a", href=re.compile(r'twitter\.com|x\.com'))
            if a_tag:
                return a_tag["href"]

        # 4) og:video meta tag
        og_video = soup.find("meta", property="og:video")
        if og_video and og_video.get("content"):
            return og_video["content"]
        og_video_url = soup.find("meta", property="og:video:url")
        if og_video_url and og_video_url.get("content"):
            return og_video_url["content"]

        # 5) 직접 mp4 링크
        mp4_match = re.search(r'(https?://[^\s"\'<>]+\.mp4)', page_html)
        if mp4_match:
            return mp4_match.group(1)

        # 6) <video> 태그의 src
        video_tag = soup.find("video")
        if video_tag:
            src = video_tag.get("src") or ""
            if src:
                return src
            source_tag = video_tag.find("source")
            if source_tag and source_tag.get("src"):
                return source_tag["src"]

    except Exception:
        pass
    return ""


def extract_video_from_rss(entry) -> str:
    """RSS 엔트리에서 동영상 URL 직접 추출"""
    # media:content 에서 video 타입
    for media in entry.get("media_content", []):
        mtype = media.get("type", "")
        url = media.get("url", "")
        if "video" in mtype and url:
            return url
    # enclosure 에서 video 타입
    for enc in entry.get("enclosures", []):
        if "video" in enc.get("type", ""):
            return enc.get("href", "")
    return ""


def download_video_ytdlp(video_url: str, save_dir: str, filename: str = "video") -> str:
    """yt-dlp Python API로 동영상 다운로드 (Streamlit Cloud 호환)"""
    try:
        import yt_dlp
        os.makedirs(save_dir, exist_ok=True)
        out_path = os.path.join(save_dir, f"{filename}.%(ext)s")
        ydl_opts = {
            'format': 'best[ext=mp4]/best',
            'outtmpl': out_path,
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
            'socket_timeout': 30,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
        # 실제 저장된 파일 찾기
        for f in os.listdir(save_dir):
            if f.startswith(filename) and not f.endswith(".part"):
                return os.path.join(save_dir, f)
    except ImportError:
        pass  # yt-dlp 미설치
    except Exception:
        pass
    return ""


def quick_translate_title(title_en: str, is_korean: bool = False) -> str:
    """제목만 빠르게 한글 번역 (미리보기용, Google Translate)"""
    if is_korean or not title_en:
        return title_en
    try:
        translator = GoogleTranslator(source="en", target="ko")
        result = translator.translate(title_en[:200])
        return polish_korean(result) if result else title_en
    except Exception:
        return title_en


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


def summarize_text(text: str, translator=None, max_sentences: int = 5) -> str:
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


def fetch_x_influencer(display_name: str, query: str, count: int = 5, max_days: int = 3):
    """Google News RSS로 인플루언서/키워드 관련 뉴스 수집 (max_days 이내만)"""
    results = []
    try:
        feed_url = GOOGLE_NEWS_RSS.format(query=query)
        feed = feedparser.parse(feed_url)
        if not feed.entries:
            return results

        now_utc = datetime.now(timezone.utc)
        for entry in feed.entries[:count * 3]:  # 날짜 필터로 걸러질 것 대비 여유분
            title_en = clean_text(entry.get("title", ""))
            if not title_en or len(title_en) < 10:
                continue

            published = entry.get("published", "")
            # 3일 이내 기사만 허용
            pub_dt = parse_pub_date(published)
            age_days = (now_utc - pub_dt).total_seconds() / 86400
            if age_days > max_days:
                continue
            link = entry.get("link", "")
            # Google News 소스 추출 (제목 뒤에 " - 매체명" 형태)
            source_media = ""
            if " - " in title_en:
                parts = title_en.rsplit(" - ", 1)
                title_en = parts[0]
                source_media = parts[1] if len(parts) > 1 else ""

            summary_en = clean_text(entry.get("summary", entry.get("description", "")))
            # HTML 태그 제거
            summary_en = re.sub(r'<[^>]+>', '', summary_en)

            # 기사 본문 스크래핑 (RSS summary는 보통 1~2줄이라 부족)
            full_text = ""
            if link:
                try:
                    full_text = scrape_article_text(link)
                except Exception:
                    full_text = ""
            if not full_text or len(full_text) < 200:
                full_text = summary_en if summary_en else title_en

            title_ko = quick_translate_title(title_en[:200])

            results.append({
                "title_en": title_en[:200],
                "title_ko": title_ko,
                "summary_en": summary_en if summary_en else title_en,
                "summary_ko": "",
                "full_text": full_text,
                "published": published,
                "link": link,
                "source": f"🔍 {display_name}" + (f" ({source_media})" if source_media else ""),
                "video_url": "",
                "image_url": "",
                "is_korean": False,
            })

    except Exception:
        pass
    return results[:count]  # 날짜 필터 후 count 제한


def fetch_all_news(feed_names: list, count_per_feed: int = 5, progress_callback=None,
                   influencer_names: list = None, count_per_influencer: int = 3,
                   feed_dict: dict = None, max_days: int = 3,
                   influencer_dict: dict = None):
    """모든 RSS 소스 + X 인플루언서에서 뉴스 수집. feed_dict/influencer_dict로 커스텀 피드 사용 가능."""
    all_items = []
    influencer_names = influencer_names or []
    if feed_dict is None:
        feed_dict = RSS_FEEDS
    if influencer_dict is None:
        influencer_dict = X_INFLUENCERS
    total_steps = len(feed_names) + len(influencer_names)
    if total_steps == 0:
        return []

    step = 0

    # ── RSS 피드 수집 ──
    for i, feed_name in enumerate(feed_names):
        step += 1
        if progress_callback:
            progress_callback(step / total_steps, f"📡 {feed_name} 수집 중...")

        feed_url = feed_dict.get(feed_name)
        if not feed_url:
            continue

        is_korean = feed_name in KOREAN_FEEDS

        try:
            feed = feedparser.parse(feed_url)
            now_utc = datetime.now(timezone.utc)
            added = 0
            for entry in feed.entries:
                if added >= count_per_feed:
                    break
                title_en = clean_text(entry.get("title", ""))
                published = entry.get("published", "")

                # 날짜 필터: max_days 이내 기사만
                pub_dt = parse_pub_date(published)
                age_days = (now_utc - pub_dt).total_seconds() / 86400
                if age_days > max_days:
                    continue

                link = entry.get("link", "#")
                image_url = extract_image_from_rss(entry)
                rss_summary = clean_text(entry.get("summary", entry.get("description", "")))

                if not image_url and link and link != "#":
                    image_url = scrape_og_image(link)

                # 기사 본문 확보
                if len(rss_summary) < 200:
                    full_text = scrape_article_text(link)
                else:
                    full_text = rss_summary

                # 동영상 URL 추출
                video_url = extract_video_from_rss(entry)
                if not video_url and link and link != "#":
                    video_url = extract_video_from_page(link)

                # 제목 1차 번역 (미리보기용)
                title_ko = quick_translate_title(title_en, is_korean)

                added += 1
                all_items.append({
                    "title_en": title_en,
                    "title_ko": title_ko,
                    "summary_en": rss_summary,
                    "summary_ko": "",
                    "full_text": full_text or rss_summary,
                    "published": published,
                    "link": link,
                    "source": feed_name,
                    "image_url": image_url,
                    "video_url": video_url,
                    "is_korean": is_korean,
                })
        except Exception as e:
            continue

    # ── X 인플루언서 피드 수집 (Google News RSS) ──
    import time as _time
    for idx, display_name in enumerate(influencer_names):
        step += 1
        if progress_callback:
            progress_callback(step / total_steps, f"🐦 {display_name} 수집 중...")

        handle = influencer_dict.get(display_name)
        if not handle:
            continue

        try:
            items = fetch_x_influencer(display_name, handle, count_per_influencer, max_days=max_days)
            all_items.extend(items)
        except Exception:
            continue

        # Google News RSS 부하 방지: 최소 딜레이
        _time.sleep(0.3)

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
    # ── 테슬라 소스 ──
    "🚗 Electrek (Tesla)": 1,
    "📈 Teslarati": 1,
    "⚡ InsideEVs": 2,
    "🏭 Not a Tesla App": 2,
    "🤖 Tesla Oracle": 2,
    "📰 CleanTechnica": 2,
    "🔋 Torque News (Tesla)": 3,
    "🚘 AutoEvolution (Tesla)": 3,
    "💹 Yahoo Finance (TSLA)": 2,
    "📊 Seeking Alpha (TSLA)": 2,
    "💰 Motley Fool (TSLA)": 3,
    "🖥️ The Verge (Tesla)": 1,
    "🔧 Ars Technica (Cars)": 2,
    "📡 TechCrunch (Tesla)": 1,
    # 유튜브 (독점 영상 콘텐츠이므로 Tier 1~2)
    "🎬 Tesla Daily (Rob Maurer)": 1,
    "🎬 Munro Live": 1,
    "🎬 Dave Lee": 1,
    "🎬 Meet Kevin": 2,
    "🎬 MKBHD": 1,
    "🎬 The Electric Viking": 2,
    "🎬 Bjørn Nyland": 2,
    "🎬 Hyperchange": 2,
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


def detect_post_type(title_en: str, summary_en: str, source: str = "") -> str:
    """포스트 유형 자동 감지 → UI selectbox 기본값 추천용"""
    title_lower = title_en.lower()
    combined = (title_en + " " + summary_en).lower()

    # 인물 발언 감지 → quote_post
    has_person = any(k in title_lower for k in PERSON_KEYWORDS if k not in QUOTE_MARKERS)
    has_quote_verb = any(q in title_lower for q in QUOTE_MARKERS)
    has_quotation = '"' in title_en or '\u201c' in title_en or ':' in title_en
    if has_person and (has_quote_verb or has_quotation):
        return "quote_post"

    # 고래 움직임 감지 → whale_alert
    whale_words = ["whale", "transfer", "moved", "deposit", "withdraw",
                   "exchange inflow", "exchange outflow", "고래"]
    if any(w in combined for w in whale_words):
        return "whale_alert"

    # 속보 감지 → breaking
    breaking_words = ["breaking", "urgent", "just in", "hack", "exploit",
                      "crash", "war ", "missile", "military strike", "arrested"]
    if any(w in combined for w in breaking_words):
        return "breaking"

    # 온체인/데이터 감지 → data_post
    data_words = ["on-chain", "onchain", "etf flow", "etf inflow", "etf outflow",
                  "tvl", "dominance", "exchange reserve", "hashrate", "mining",
                  "supply", "realized", "mvrv", "nupl"]
    if any(w in combined for w in data_words):
        return "data_post"

    return "single"


def find_person_name(title_en: str, summary_en: str) -> str:
    """제목에서 인물명 추출 (본문 인물 오귀속 방지 — 제목 우선)"""
    title_lower = title_en.lower()
    # 1차: 제목에서만 찾기
    for keyword, display_name in PERSON_KEYWORDS.items():
        if keyword in title_lower and display_name:
            return display_name
    # 2차: 제목에 인물이 없으면 빈 문자열 (본문 인물을 헤드라인 화자로 잘못 쓰지 않음)
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
    2026.04.10 실제 @CryptoYuna_ 계정 분석 반영

    핵심 변경:
    - 불릿은 • 사용 (- 아님, 실제 CryptoYuna 패턴)
    - 인물 발언은 헤드라인에 인물명 : "발언" 형태
    - 해시태그 사용 안 함 (실제 CryptoYuna는 해시태그 거의 안 씀)
    - 출처 표기: [출처 : OOO]
    - 글자 잘림 방지: 문장 단위로 온전하게 유지
    """

    emoji = get_category_emoji(item["title_en"], item.get("summary_en", ""))
    category = get_post_category(item["title_en"], item.get("summary_en", ""))
    post_type = detect_post_type(item["title_en"], item.get("summary_en", ""))
    title = item["title_ko"].strip()
    summary = item.get("summary_ko", "")
    source = item.get("source", "")
    source_clean = re.sub(r'^[^\s]*\s*', '', source).strip() if source else ""

    # 제목 끝 처리 (CryptoYuna: ! 또는 자연스러운 끝)
    if not title.endswith(('!', '?', '.', '다', '요')):
        title += '!'

    sentences = extract_clean_bullets(summary, title, 8)

    # ════════════════════════════════════
    #  패턴B: 인물 발언 인용형
    #  예: 📌 CZ : "암호화폐, 5년 뒤 인터넷처럼 일상화될 것"
    # ════════════════════════════════════
    if post_type == "quote":
        person = find_person_name(item["title_en"], item.get("summary_en", ""))
        lines = []

        # 헤드라인: 인물명 : "제목"
        if person:
            # 제목에서 따옴표 안 내용 추출 시도
            quote_match = re.search(r'["\u201c](.+?)["\u201d]', title)
            if quote_match:
                lines.append(f'{emoji} {person} : "{quote_match.group(1)}"')
            else:
                lines.append(f'{emoji} {person} : "{title}"')
        else:
            lines.append(f"{emoji} {title}")

        lines.append("")

        # 불릿 포인트로 핵심 정보 (• 사용, 따옴표 안 감쌈)
        for s in sentences[:4]:
            lines.append(f"• {s}")

        post_text = "\n".join(lines)

    # ════════════════════════════════════
    #  패턴C: 속보형
    #  예: 🚨 트럼프 내부자, BTC+ETH 총 2.03억 달러 롱 포지션 오픈!
    # ════════════════════════════════════
    elif post_type == "breaking":
        lines = [f"{emoji} {title}", ""]

        for s in sentences[:5]:
            lines.append(f"• {s}")

        post_text = "\n".join(lines)

    # ════════════════════════════════════
    #  패턴A: 뉴스 기사형 (기본, 가장 많음)
    #  예: 💥 Binance 이더리움 출금량, 2025년 이후 최고치 폭발
    #      • 핵심1
    #      • 핵심2
    # ════════════════════════════════════
    else:
        lines = [f"{emoji} {title}", ""]

        # 전체 불릿으로 통일 (• 사용, 실제 CryptoYuna 패턴)
        for s in sentences[:5]:
            lines.append(f"• {s}")

        post_text = "\n".join(lines)

    # 출처 표기 (실제 CryptoYuna: [출처 : OOO] 형태)
    if source_clean:
        post_text += f"\n\n[출처 : {source_clean}]"

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
    page_title="🪙 크립토 포스트 생성기",
    page_icon="🪙",
    layout="wide",
    initial_sidebar_state="collapsed",  # 모바일에서 사이드바 기본 접힘
)

# ── 모바일 최적화 CSS ──
st.markdown("""
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<style>
    /* ── 전체 테마 ── */
    .stApp {
        background-color: #0e1117;
        color: #e0e0e0;
    }

    /* ── Streamlit 위젯 글씨 가시성 (다크 테마) ── */

    /* 사이드바 전체 */
    section[data-testid="stSidebar"] {
        background-color: #0e1117;
        color: #e0e0e0;
    }
    section[data-testid="stSidebar"] .stMarkdown,
    section[data-testid="stSidebar"] .stMarkdown p,
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] .stRadio label,
    section[data-testid="stSidebar"] span,
    section[data-testid="stSidebar"] .stCheckbox label span {
        color: #e0e0e0 !important;
    }

    /* 모든 label / caption / markdown 텍스트 */
    .stMarkdown, .stMarkdown p, .stMarkdown li,
    .stCaption, label,
    .stTextInput label, .stSelectbox label,
    .stRadio label, .stSlider label,
    .stNumberInput label, .stCheckbox label,
    .stMultiSelect label, .stTextArea label,
    .stTabs [data-baseweb="tab"] {
        color: #e0e0e0 !important;
    }

    /* selectbox 내부 텍스트 + 배경 */
    .stSelectbox [data-baseweb="select"],
    .stSelectbox [data-baseweb="select"] *,
    .stMultiSelect [data-baseweb="select"],
    .stMultiSelect [data-baseweb="select"] * {
        color: #e0e0e0 !important;
        background-color: #1a1a2e !important;
    }

    /* text_input, number_input, textarea 내부 */
    .stTextInput input, .stNumberInput input, .stTextArea textarea {
        color: #e0e0e0 !important;
        background-color: #1a1a2e !important;
        border: 1px solid #333 !important;
    }
    .stTextInput input::placeholder, .stTextArea textarea::placeholder {
        color: #888 !important;
    }

    /* 드롭다운 팝오버 (열렸을 때 목록) */
    [data-baseweb="popover"],
    [data-baseweb="menu"],
    [data-baseweb="popover"] ul,
    [data-baseweb="menu"] ul {
        background-color: #1a1a2e !important;
    }
    [data-baseweb="popover"] li,
    [data-baseweb="menu"] li,
    [data-baseweb="popover"] li *,
    [data-baseweb="menu"] li * {
        color: #e0e0e0 !important;
        background-color: #1a1a2e !important;
    }
    [data-baseweb="popover"] li:hover,
    [data-baseweb="menu"] li:hover {
        background-color: #2a2a4e !important;
    }

    /* Radio 버튼 */
    .stRadio > div[role="radiogroup"] label,
    .stRadio > div[role="radiogroup"] label div {
        color: #e0e0e0 !important;
    }

    /* Checkbox 텍스트 */
    .stCheckbox label span[data-testid="stMarkdownContainer"],
    .stCheckbox label span[data-testid="stMarkdownContainer"] p {
        color: #e0e0e0 !important;
    }

    /* 슬라이더 값 표시 */
    .stSlider [data-testid="stTickBarMin"],
    .stSlider [data-testid="stTickBarMax"],
    .stSlider [data-baseweb="slider"] div,
    .stSlider > div > div > div > div {
        color: #e0e0e0 !important;
    }

    /* Expander 헤더 */
    .streamlit-expanderHeader,
    details summary,
    details summary span,
    [data-testid="stExpander"] summary span {
        color: #e0e0e0 !important;
    }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] button {
        color: #aaa !important;
    }
    .stTabs [data-baseweb="tab-list"] button[aria-selected="true"] {
        color: #e94560 !important;
    }

    /* 버튼 기본 스타일 */
    .stButton > button {
        color: #fff !important;
    }
    .stButton > button[kind="primary"] {
        background-color: #e94560 !important;
        border: none !important;
    }
    .stButton > button[kind="primary"]:hover {
        background-color: #d63a55 !important;
    }

    /* st.warning / st.error / st.success / st.info 텍스트 */
    .stAlert p, .stAlert span {
        color: #1a1a2e !important;
    }

    /* download 버튼 */
    .stDownloadButton > button {
        color: #e0e0e0 !important;
        border: 1px solid #333 !important;
    }

    /* st.caption */
    .stCaption, [data-testid="stCaptionContainer"] {
        color: #888 !important;
    }

    /* ── 모바일 반응형 ── */
    @media (max-width: 768px) {
        /* 사이드바 패딩 줄이기 */
        .stSidebar .stSidebarContent { padding: 0.5rem !important; }

        /* 메인 영역 패딩 줄이기 */
        .stMainBlockContainer { padding: 0.5rem !important; }
        section.main > div { padding: 0.5rem !important; }
        .block-container { padding: 0.5rem 0.5rem !important; max-width: 100% !important; }

        /* 버튼 터치 영역 키우기 */
        .stButton > button {
            min-height: 48px !important;
            font-size: 16px !important;
            padding: 12px 16px !important;
            width: 100% !important;
        }

        /* expander 터치 영역 */
        .streamlit-expanderHeader {
            font-size: 14px !important;
            padding: 12px 8px !important;
            min-height: 48px !important;
        }

        /* 입력 필드 */
        .stTextInput input, .stSelectbox select {
            font-size: 16px !important;  /* iOS 줌 방지 */
            min-height: 44px !important;
        }

        /* 컬럼 스택 */
        [data-testid="column"] {
            width: 100% !important;
            flex: 100% !important;
        }

        /* X 미리보기 */
        .x-preview {
            max-width: 100% !important;
            font-size: 14px !important;
            padding: 12px !important;
        }

        /* 텍스트 영역 */
        .stTextArea textarea {
            font-size: 14px !important;
        }

        /* 코드 블록 복사용 */
        .stCode {
            font-size: 13px !important;
        }

        /* 헤더 크기 조정 */
        h1 { font-size: 1.5rem !important; }
        h2 { font-size: 1.2rem !important; }
        h3 { font-size: 1.1rem !important; }

        /* 슬라이더 터치 영역 */
        .stSlider > div { padding: 8px 0 !important; }

        /* 통계 카드 */
        .stat-card { padding: 10px !important; }
        .stat-number { font-size: 22px !important; }
    }

    /* ── 공통 스타일 ── */

    /* 포스트 카드 */
    .post-card {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border-radius: 16px;
        padding: 16px;
        margin: 8px 0;
        border-left: 4px solid #e94560;
        color: #eee;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    .post-card-hot {
        border-left: 4px solid #ff6b35;
        background: linear-gradient(135deg, #1a1a2e 0%, #2a1a3e 100%);
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
        word-break: keep-all;
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

    /* 미디어 태그 */
    .media-tag {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 6px;
        font-size: 11px;
        font-weight: bold;
        margin-left: 4px;
    }
    .media-video { background: #ff4444; color: white; }
    .media-image { background: #4488ff; color: white; }

    /* 복사 버튼 강조 */
    .copy-hint {
        background: #1a3a5c;
        border: 1px dashed #4488ff;
        border-radius: 8px;
        padding: 8px 12px;
        color: #88bbff;
        font-size: 13px;
        text-align: center;
        margin: 8px 0;
    }
</style>
""", unsafe_allow_html=True)


# ── 타이틀 ──
st.title("🪙 크립토 X 포스트 생성기")
st.caption("뉴스 수집 → 기사 선택 → Claude AI가 한국어 포스트 생성")

# 모바일 힌트
st.markdown('<p style="color:#666; font-size:12px;">💡 모바일: 좌측 상단 ☰ 아이콘으로 설정 열기</p>', unsafe_allow_html=True)

# ── 사이드바 설정 ──
with st.sidebar:
    st.header("⚙️ 설정")

    st.markdown("### 🔑 Claude API")
    # secrets > 환경변수 > 직접 입력 순으로 API 키 확인
    _default_key = ""
    try:
        _default_key = st.secrets.get("ANTHROPIC_API_KEY", "")
    except Exception:
        pass
    if not _default_key:
        _default_key = os.environ.get("ANTHROPIC_API_KEY", "")
    claude_api_key = st.text_input(
        "API Key",
        type="password",
        help="Anthropic Console에서 발급받은 API 키. Streamlit Cloud는 Secrets에 등록하면 자동 적용됩니다.",
        value=_default_key,
    )
    claude_model = st.selectbox(
        "모델",
        ["claude-sonnet-4-20250514", "claude-haiku-4-5-20251001", "claude-opus-4-0-20250115"],
        index=0,
        help="Sonnet: 빠르고 저렴 / Haiku: 더 빠름 / Opus: 최고 품질"
    )

    st.markdown("---")
    output_dir = DEFAULT_OUTPUT_DIR

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
        ["⭐ 추천 소스", "📋 전체 선택", "🛠 수동 선택", "❌ 전체 해제 (직접 선택)"],
        index=0,
        help="추천: 품질 높은 대표 소스만. 전체 해제: 원하는 것만 직접 골라서 사용"
    )

    selected_feeds = []
    feed_categories = {
        "🔴 메이저 (추천)": ["🟠 CoinDesk", "📰 Cointelegraph", "🟣 Decrypt",
                              "📈 Blockworks", "📊 The Block"],
        "⚡ 속보/뉴스": ["🔵 CryptoNews", "⚡ Bitcoin Magazine", "🌏 Wu Blockchain",
                          "🪨 CryptoSlate", "📡 BeInCrypto", "📰 CoinJournal",
                          "🌐 NewsBTC", "📈 Bitcoinist", "🔶 U.Today", "📰 AMBCrypto",
                          "🔔 Watcher.Guru", "🦅 CryptoPanic"],
        "📊 온체인/데이터": ["🐋 Whale Alert Blog", "📉 Glassnode Blog", "🦎 CoinGecko Blog",
                             "🔗 Chainalysis Blog", "📊 Santiment Blog", "🔎 CryptoQuant Blog"],
        "🏦 기관/월스트리트": ["🏦 DL News", "💹 CNBC Crypto"],
        "🔬 리서치/DeFi": ["🔬 Messari", "🛡️ The Defiant", "📚 Coin Bureau"],
        "🇰🇷 한국 미디어": ["🇰🇷 블록미디어", "🇰🇷 디지털투데이", "🇰🇷 코인리더스"],
    }

    if feed_mode == "⭐ 추천 소스":
        selected_feeds = [f for f in RECOMMENDED_FEEDS if f in RSS_FEEDS]
    elif feed_mode == "📋 전체 선택":
        selected_feeds = list(RSS_FEEDS.keys())
    elif feed_mode == "❌ 전체 해제 (직접 선택)":
        for cat_name, feeds in feed_categories.items():
            valid_feeds = [f for f in feeds if f in RSS_FEEDS]
            if not valid_feeds:
                continue
            cat_key = f"feed_cat_{cat_name}"
            prev_key = f"_prev_{cat_key}"
            cat_checked = st.checkbox(f"**{cat_name}** ({len(valid_feeds)}개)", value=False, key=cat_key)
            # 카테고리 값이 변경될 때만 하위 항목 동기화
            prev_val = st.session_state.get(prev_key, None)
            if prev_val is not None and prev_val != cat_checked:
                for feed in valid_feeds:
                    st.session_state[f"feed_{feed}"] = cat_checked
            st.session_state[prev_key] = cat_checked
            with st.expander(cat_name, expanded=cat_checked):
                for feed in valid_feeds:
                    checked = st.checkbox(feed, value=False, key=f"feed_{feed}")
                    if checked:
                        selected_feeds.append(feed)
    else:  # 🛠 수동 선택
        for cat_name, feeds in feed_categories.items():
            valid_feeds = [f for f in feeds if f in RSS_FEEDS]
            if not valid_feeds:
                continue
            cat_key = f"manual_feed_cat_{cat_name}"
            prev_key = f"_prev_{cat_key}"
            cat_checked = st.checkbox(f"**{cat_name}** ({len(valid_feeds)}개)", value=True, key=cat_key)
            prev_val = st.session_state.get(prev_key, None)
            if prev_val is not None and prev_val != cat_checked:
                for feed in valid_feeds:
                    st.session_state[f"feed_{feed}"] = cat_checked
            st.session_state[prev_key] = cat_checked
            with st.expander(cat_name, expanded=False):
                for feed in valid_feeds:
                    default_on = feed in RECOMMENDED_FEEDS if cat_checked else False
                    checked = st.checkbox(feed, value=default_on, key=f"feed_{feed}")
                    if checked:
                        selected_feeds.append(feed)

    st.markdown("---")
    st.markdown("### 🐦 X 인플루언서 소스")

    # ── 추천 인플루언서 (가장 뉴스 가치 높은 계정) ──
    RECOMMENDED_INFLUENCERS = {
        # VIP 핵심 인물
        "⭐ Michael Saylor", "⭐ Elon Musk", "⭐ Donald Trump",
        "⭐ Jim Cramer", "⭐ CZ (Binance)", "⭐ Larry Fink",
        # 1차 소스
        "🎙️ James Seyffart", "🎙️ Eric Balchunas",
        # 속보/뉴스
        "🔔 BTC 속보", "🔔 ETF 자금흐름", "🔔 고래/온체인",
        # 온체인/데이터
        "📊 Glassnode", "📊 Lookonchain",
        # 한국
        "🇰🇷 한국 크립토",
    }

    inf_mode = st.radio(
        "인플루언서 모드",
        ["⭐ 추천 계정 (14개)", "📋 전체 계정", "🛠 수동 선택", "❌ 전체 해제 (직접 선택)"],
        index=0,
        help="추천: VIP 인물 + 핵심 속보 + 한국 계정"
    )

    selected_influencers = []
    influencer_categories = {
        "⭐ VIP 인물": ["⭐ Michael Saylor", "⭐ Elon Musk", "⭐ Donald Trump",
                        "⭐ Jim Cramer", "⭐ CZ (Binance)", "⭐ Larry Fink",
                        "⭐ Cathie Wood", "⭐ Arthur Hayes", "⭐ Vitalik Buterin",
                        "⭐ Justin Sun", "⭐ Brian Armstrong", "⭐ Jack Dorsey",
                        "⭐ Robert Kiyosaki"],
        "🎙️ 1차 소스 (Bloomberg/기관)": ["🎙️ James Seyffart", "🎙️ Eric Balchunas",
                                        "🎙️ Nate Geraci", "🎙️ Scott Melker",
                                        "🎙️ The Kobeissi Letter"],
        "🏛️ 거래소/기관 공식": ["🏛️ Binance", "🏛️ Coinbase", "🏛️ Grayscale",
                                "🏛️ BlackRock ETF", "🏛️ Fidelity Crypto"],
        "🌍 글로벌 대형 인플루언서": ["🌍 Miles Deutscher", "🌍 Ben Cowen",
                                     "🌍 Lark Davis", "🌍 Rekt Capital",
                                     "🌍 Ali Martinez", "🌍 Crypto Banter"],
        "📈 트레이더/분석가": ["📈 Raoul Pal", "📈 Pompliano",
                              "📈 Peter Schiff", "📈 Willy Woo",
                              "📈 PlanB", "📈 Tom Lee"],
        "📊 온체인/데이터": ["📊 Glassnode", "📊 CryptoQuant",
                             "📊 Santiment", "📊 Lookonchain"],
        "🔔 속보/뉴스": ["🔔 BTC 속보", "🔔 ETH 속보", "🔔 고래/온체인",
                         "🔔 ETF 자금흐름", "🔔 규제/SEC"],
        "🇰🇷 한국": ["🇰🇷 한국 크립토"],
    }

    if inf_mode == "⭐ 추천 계정 (14개)":
        selected_influencers = [inf for inf in RECOMMENDED_INFLUENCERS if inf in X_INFLUENCERS]
    elif inf_mode == "📋 전체 계정":
        selected_influencers = list(X_INFLUENCERS.keys())
    elif inf_mode == "❌ 전체 해제 (직접 선택)":
        for cat_name, influencers in influencer_categories.items():
            valid_infs = [inf for inf in influencers if inf in X_INFLUENCERS]
            if not valid_infs:
                continue
            cat_key = f"inf_cat_{cat_name}"
            prev_key = f"_prev_{cat_key}"
            cat_checked = st.checkbox(f"**{cat_name}** ({len(valid_infs)}개)", value=False, key=cat_key)
            # 카테고리 값이 변경될 때만 하위 항목 동기화
            prev_val = st.session_state.get(prev_key, None)
            if prev_val is not None and prev_val != cat_checked:
                for inf in valid_infs:
                    st.session_state[f"inf_{inf}"] = cat_checked
            st.session_state[prev_key] = cat_checked
            with st.expander(cat_name, expanded=cat_checked):
                for inf in valid_infs:
                    checked = st.checkbox(inf, value=False, key=f"inf_{inf}")
                    if checked:
                        selected_influencers.append(inf)
    else:  # 🛠 수동 선택
        for cat_name, influencers in influencer_categories.items():
            valid_infs = [inf for inf in influencers if inf in X_INFLUENCERS]
            if not valid_infs:
                continue
            cat_key = f"manual_inf_cat_{cat_name}"
            prev_key = f"_prev_{cat_key}"
            cat_checked = st.checkbox(f"**{cat_name}** ({len(valid_infs)}개)", value=True, key=cat_key)
            prev_val = st.session_state.get(prev_key, None)
            if prev_val is not None and prev_val != cat_checked:
                for inf in valid_infs:
                    st.session_state[f"inf_{inf}"] = cat_checked
            st.session_state[prev_key] = cat_checked
            with st.expander(cat_name, expanded=False):
                for inf in valid_infs:
                    default_on = inf in RECOMMENDED_INFLUENCERS if cat_checked else False
                    checked = st.checkbox(inf, value=default_on, key=f"inf_{inf}")
                    if checked:
                        selected_influencers.append(inf)

    st.markdown("---")
    st.markdown("### 🎯 생성 설정")
    post_style = st.radio(
        "✍️ 글쓰기 스타일",
        ["🧵 스레드형 (메인+답글)", "📌 CryptoYuna형 (불릿)"],
        index=0,
        help="스레드형: 메인 훅 트윗 + 답글 3개 / CryptoYuna형: 이모지+불릿 단일 포스트"
    )
    selected_style = "thread" if "스레드" in post_style else "yuna"
    num_posts = st.slider("생성할 기사 수", 5, 50, 25)
    max_news_days = st.slider("📅 최신 뉴스 필터 (일)", 1, 7, 3, help="이 기간 이내의 뉴스만 수집")
    news_per_feed = st.slider("소스당 수집 수", 3, 15, 8)
    inf_per_account = st.slider("인플루언서당 수집 수", 1, 10, 5)
    min_score = st.slider("최소 이슈성 점수", 0, 50, 5)

    st.markdown("---")
    st.markdown("### 📊 점수 기준")
    st.markdown("""
    - **최신성** (40점): 최근 기사일수록 높음
    - **⭐ VIP 보너스** (40점): VIP 인물 + 코인 발언
    - **핫키워드** (30점): Trump, ETF, Musk 등
    - **복수 매체** (20점): 여러 매체 보도
    - **미디어** (10점): 이미지/영상 포함
    """)
    st.markdown("---")
    st.markdown(f"📰 RSS: **{len(selected_feeds)}**개 | 🐦 X: **{len(selected_influencers)}**개")

    st.markdown("---")
    st.caption("📱 Streamlit Cloud 배포 → 핸드폰 어디서나 접속 가능")


# ── 메인 영역 ──

# ════════════════════════════════════
#  STEP 1: 뉴스 수집 (크립토 / 테슬라 탭)
# ════════════════════════════════════
st.markdown("## 📡 STEP 1: 뉴스 수집")

news_tab_crypto, news_tab_tesla = st.tabs(["🪙 크립토 뉴스", "🚗 테슬라 뉴스"])

with news_tab_crypto:
    collect_btn = st.button("📡 크립토 뉴스 수집", type="primary", use_container_width=True, key="collect_crypto")

    if collect_btn:
        if not selected_feeds and not selected_influencers:
            st.error("최소 1개 이상의 뉴스 소스 또는 인플루언서를 선택하세요!")
        else:
            progress_bar = st.progress(0)
            status_text = st.empty()

            def update_progress(pct, msg):
                progress_bar.progress(pct)
                status_text.text(msg)

            all_news = fetch_all_news(
                selected_feeds, news_per_feed, update_progress,
                influencer_names=selected_influencers,
                count_per_influencer=inf_per_account,
                feed_dict=RSS_FEEDS,
                max_days=max_news_days,
            )
            rss_count = sum(1 for n in all_news if not n["source"].startswith("🐦"))
            x_count = sum(1 for n in all_news if n["source"].startswith("🐦"))
            status_text.text(f"총 {len(all_news)}개 수집 (RSS: {rss_count} / X: {x_count})")

            filtered = [n for n in all_news if n["score"]["total"] >= min_score]
            unique_news = deduplicate_news(filtered)
            top_news = unique_news[:num_posts]

            st.session_state["collected_news"] = top_news
            st.session_state["news_mode"] = "crypto"
            st.session_state["generated_posts"] = {}
            st.success(f"🪙 크립토 뉴스 수집 완료! 상위 {len(top_news)}개 기사 준비됨")

with news_tab_tesla:
    st.markdown("**테슬라/EV 전문 RSS + 유튜브 + 인플루언서에서 최신 뉴스를 수집합니다.**")

    # ── 테슬라 소스 카테고리 선택 ──
    tesla_feed_categories = {
        "🚗 전문 미디어": [f for f in TESLA_RSS_FEEDS if not f.startswith("🎬") and not f.startswith("💹") and not f.startswith("📊 Seeking") and not f.startswith("💰") and not f.startswith("🖥") and not f.startswith("🔧") and not f.startswith("📡")],
        "💰 금융/투자": [f for f in TESLA_RSS_FEEDS if any(f.startswith(p) for p in ["💹", "📊 Seeking", "💰"])],
        "🖥️ 테크 미디어": [f for f in TESLA_RSS_FEEDS if any(f.startswith(p) for p in ["🖥", "🔧", "📡"])],
        "🎬 유튜브 채널": [f for f in TESLA_RSS_FEEDS if f.startswith("🎬")],
    }

    tesla_source_mode = st.radio(
        "테슬라 소스 모드",
        ["⭐ 전체 선택 (추천)", "🎬 유튜브만", "🛠 수동 선택"],
        index=0,
        key="tesla_source_mode",
        help="전체: 모든 RSS + 유튜브. 유튜브만: 영상 콘텐츠 위주"
    )

    tesla_feeds_list = []
    if tesla_source_mode == "⭐ 전체 선택 (추천)":
        tesla_feeds_list = list(TESLA_RSS_FEEDS.keys())
    elif tesla_source_mode == "🎬 유튜브만":
        tesla_feeds_list = [f for f in TESLA_RSS_FEEDS if f.startswith("🎬")]
    else:  # 🛠 수동 선택
        for cat_name, feeds in tesla_feed_categories.items():
            if not feeds:
                continue
            cat_key = f"tesla_feed_cat_{cat_name}"
            prev_key = f"_prev_{cat_key}"
            cat_checked = st.checkbox(f"**{cat_name}** ({len(feeds)}개)", value=True, key=cat_key)
            prev_val = st.session_state.get(prev_key, None)
            if prev_val is not None and prev_val != cat_checked:
                for feed in feeds:
                    st.session_state[f"tesla_feed_{feed}"] = cat_checked
            st.session_state[prev_key] = cat_checked
            with st.expander(cat_name, expanded=False):
                for feed in feeds:
                    if st.checkbox(feed, value=True, key=f"tesla_feed_{feed}"):
                        tesla_feeds_list.append(feed)

    # ── 테슬라 인플루언서 선택 ──
    st.markdown("---")
    tesla_inf_categories = {
        "⭐ VIP 인물": [inf for inf in TESLA_X_INFLUENCERS if inf.startswith("⭐")],
        "📊 월스트리트 애널리스트": [inf for inf in TESLA_X_INFLUENCERS if inf.startswith("📊")],
        "🔥 테슬라 인플루언서": [inf for inf in TESLA_X_INFLUENCERS if inf.startswith("🔥")],
        "🚨 속보/키워드": [inf for inf in TESLA_X_INFLUENCERS if inf.startswith("🚨")],
    }

    tesla_inf_mode = st.radio(
        "테슬라 인플루언서",
        ["⭐ 전체 (추천)", "❌ 사용 안 함", "🛠 수동 선택"],
        index=0,
        key="tesla_inf_mode",
        help="VIP 인물 + 애널리스트 + 속보 키워드"
    )

    tesla_inf_selected = []
    if tesla_inf_mode == "⭐ 전체 (추천)":
        tesla_inf_selected = list(TESLA_X_INFLUENCERS.keys())
    elif tesla_inf_mode == "🛠 수동 선택":
        for cat_name, infs in tesla_inf_categories.items():
            if not infs:
                continue
            cat_key = f"tesla_inf_cat_{cat_name}"
            prev_key = f"_prev_{cat_key}"
            cat_checked = st.checkbox(f"**{cat_name}** ({len(infs)}개)", value=True, key=cat_key)
            prev_val = st.session_state.get(prev_key, None)
            if prev_val is not None and prev_val != cat_checked:
                for inf in infs:
                    st.session_state[f"tesla_inf_{inf}"] = cat_checked
            st.session_state[prev_key] = cat_checked
            with st.expander(cat_name, expanded=False):
                for inf in infs:
                    if st.checkbox(inf, value=True, key=f"tesla_inf_{inf}"):
                        tesla_inf_selected.append(inf)

    st.markdown("---")
    tesla_per_feed = st.slider("소스당 수집 수 (테슬라)", 3, 15, 8, key="tesla_per_feed")
    tesla_inf_per = st.slider("인플루언서당 수집 수", 1, 10, 5, key="tesla_inf_per")

    st.caption(f"📰 RSS/유튜브: **{len(tesla_feeds_list)}**개 | 🐦 인플루언서: **{len(tesla_inf_selected)}**개")

    collect_tesla_btn = st.button("🚗 테슬라 뉴스 수집", type="primary", use_container_width=True, key="collect_tesla")

    if collect_tesla_btn:
        if not tesla_feeds_list and not tesla_inf_selected:
            st.error("최소 1개 이상의 소스를 선택하세요!")
        else:
            progress_bar_t = st.progress(0)
            status_text_t = st.empty()

            def update_progress_t(pct, msg):
                progress_bar_t.progress(pct)
                status_text_t.text(msg)

            all_tesla = fetch_all_news(
                tesla_feeds_list, tesla_per_feed, update_progress_t,
                influencer_names=tesla_inf_selected,
                count_per_influencer=tesla_inf_per,
                feed_dict=TESLA_RSS_FEEDS,
                influencer_dict=TESLA_X_INFLUENCERS,
            )
            rss_count_t = sum(1 for n in all_tesla if not n["source"].startswith("🐦"))
            x_count_t = sum(1 for n in all_tesla if n["source"].startswith("🐦"))
            yt_count_t = sum(1 for n in all_tesla if "youtube" in n.get("link", "").lower())
            status_text_t.text(f"총 {len(all_tesla)}개 수집 (RSS: {rss_count_t} / 인플루언서: {x_count_t} / 유튜브: {yt_count_t})")

            filtered_t = [n for n in all_tesla if n["score"]["total"] >= 0]
            unique_tesla = deduplicate_news(filtered_t)
            top_tesla = unique_tesla[:num_posts]

            st.session_state["collected_news"] = top_tesla
            st.session_state["news_mode"] = "tesla"
            st.session_state["generated_posts"] = {}
        st.success(f"🚗 테슬라 뉴스 수집 완료! {len(top_tesla)}개 기사 준비됨")


# ════════════════════════════════════
#  STEP 2: 기사 선택 → Claude가 포스트 생성
# ════════════════════════════════════
if "collected_news" in st.session_state and st.session_state["collected_news"]:
    news_list = st.session_state["collected_news"]

    st.markdown("---")
    st.markdown("## ✍️ STEP 2: 기사 선택 → Claude AI 포스트 생성")

    if not claude_api_key:
        st.warning("사이드바에서 Claude API 키를 입력해주세요.")
    else:
        # ── 스레드 모드: 여러 기사 묶기 ──
        with st.expander("🧵 스레드 모드 (여러 기사 묶어서 스레드 생성)", expanded=False):
            thread_selections = []
            for i, news in enumerate(news_list):
                score = news["score"]["total"]
                pub_display = format_pub_date(news.get("published", ""))
                title_kr = news.get("title_ko", news["title_en"])
                checked = st.checkbox(
                    f"[{score:.0f}점] {title_kr[:60]} — {news['source']}",
                    key=f"thread_{i}"
                )
                if checked:
                    thread_selections.append(i)

            thread_topic = st.text_input("스레드 주제/각도 (선택사항)", placeholder="예: BTC $73K 돌파와 테슬라의 관계")

            if st.button("🧵 스레드 생성", disabled=len(thread_selections) < 2):
                if len(thread_selections) < 2:
                    st.warning("스레드를 만들려면 2개 이상 기사를 선택하세요.")
                else:
                    selected_articles = [news_list[i] for i in thread_selections]
                    with st.spinner("Claude가 스레드를 작성하고 있습니다..."):
                        try:
                            thread_text = generate_thread_with_claude(
                                api_key=claude_api_key,
                                articles=selected_articles,
                                thread_topic=thread_topic,
                                model=claude_model,
                            )
                            st.session_state["thread_result"] = thread_text
                        except Exception as e:
                            st.error(f"Claude API 오류: {e}")

            if st.session_state.get("thread_result"):
                st.markdown("### 🧵 생성된 스레드")
                st.markdown(f"""<div class="x-preview">{st.session_state['thread_result']}</div>""", unsafe_allow_html=True)
                st.code(st.session_state["thread_result"], language=None)

                # 스레드 다운로드
                st.download_button(
                    label="💾 스레드 다운로드",
                    data=st.session_state["thread_result"],
                    file_name="스레드.txt",
                    mime="text/plain",
                    key="dl_thread",
                )

        st.markdown("---")

        # ── 개별 기사 → 단일 포스트 생성 ──
        st.markdown("### 📰 개별 기사 → 포스트 생성")

        for i, news in enumerate(news_list):
            score = news["score"]["total"]
            vip_score = news["score"].get("vip", 0)
            emoji = get_category_emoji(news["title_en"], news.get("summary_en", ""))
            category = get_post_category(news["title_en"], news.get("summary_en", ""))
            pub_display = format_pub_date(news.get("published", ""))
            score_color = "🔴" if score >= 50 else "🟠" if score >= 30 else "🔵"
            vip_tag = " ⭐VIP" if vip_score > 0 else ""

            # 한글 제목 표시 (1차 번역)
            title_display = news.get("title_ko", news["title_en"])
            has_video = bool(news.get("video_url"))
            has_image = bool(news.get("image_url"))
            media_tag = ""
            if has_video:
                media_tag = " 🎬"
            elif has_image:
                media_tag = " 🖼️"

            with st.expander(
                f"{score_color} [{score:.0f}점]{vip_tag} {emoji} {title_display[:60]}{media_tag}  |  {news['source']}  |  {pub_display}",
                expanded=(i < 3)
            ):
                # ── 기사 정보 ──
                st.markdown(f"**🇰🇷 {title_display}**")
                st.caption(f"🇺🇸 {news['title_en']}")
                st.markdown(f"**출처:** {news['source']}  |  **카테고리:** {category}")
                if news.get("link"):
                    st.markdown(f"[원문 보기]({news['link']})")

                # ── 미디어 (이미지 + 동영상) ──
                if has_image:
                    try:
                        st.image(news["image_url"], use_container_width=True)
                    except Exception:
                        st.caption(f"이미지: {news['image_url'][:60]}...")

                if has_video:
                    video_url = news["video_url"]
                    st.markdown(f"**🎬 동영상 발견!**")
                    st.code(video_url, language=None)

                    # YouTube 미리보기
                    yt_match = re.search(r'(?:youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]{11})', video_url)
                    if yt_match:
                        st.image(f"https://img.youtube.com/vi/{yt_match.group(1)}/hqdefault.jpg", use_container_width=True)

                    # X/Twitter 영상인지 확인
                    is_twitter = any(d in video_url for d in ["twitter.com", "x.com", "t.co"])
                    is_youtube = bool(yt_match)
                    is_direct_mp4 = video_url.lower().endswith(".mp4")

                    if is_twitter:
                        # X/Twitter 영상 → 앱에서 직접 저장 안내
                        tweet_url = video_url.split("?")[0]
                        st.markdown("**📱 X 영상 저장 방법:**")
                        st.markdown(f"**1.** 아래 링크를 X 앱에서 열기")
                        st.markdown(f"**2.** 영상 길게 누르기 → **동영상 저장**")
                        st.link_button("🔗 X 앱에서 열기", tweet_url)
                        st.caption("또는: X 앱 → 공유 → 링크 복사 → 핸드폰 브라우저에 붙여넣기")
                    else:
                        # YouTube / 직접 mp4 → yt-dlp 다운로드 시도
                        if st.button(f"⬇️ 동영상 다운로드", key=f"dl_vid_{i}"):
                            with st.spinner("동영상 다운로드 중..."):
                                dl_dir = os.path.join(output_dir, "다운로드_영상")
                                os.makedirs(dl_dir, exist_ok=True)
                                safe_name = re.sub(r'[^\w]', '', news["title_en"])[:30]

                                # 직접 mp4면 requests로 바로 다운로드
                                saved_path = ""
                                if is_direct_mp4:
                                    try:
                                        resp = requests.get(video_url, timeout=60, stream=True)
                                        if resp.status_code == 200:
                                            mp4_path = os.path.join(dl_dir, f"{safe_name}.mp4")
                                            with open(mp4_path, "wb") as f:
                                                for chunk in resp.iter_content(chunk_size=8192):
                                                    f.write(chunk)
                                            saved_path = mp4_path
                                    except Exception:
                                        pass

                                if not saved_path:
                                    saved_path = download_video_ytdlp(video_url, dl_dir, safe_name)

                                if saved_path and os.path.exists(saved_path):
                                    with open(saved_path, "rb") as vf:
                                        video_bytes = vf.read()
                                    fname = os.path.basename(saved_path)
                                    st.download_button(
                                        label=f"📱 핸드폰에 저장: {fname}",
                                        data=video_bytes,
                                        file_name=fname,
                                        mime="video/mp4",
                                        key=f"save_vid_{i}"
                                    )
                                    st.success("다운로드 준비 완료! 위 버튼을 눌러 저장하세요.")
                                else:
                                    st.warning("다운로드 실패. 영상 URL을 직접 복사해서 사용하세요.")

                # ── 본문 미리보기 ──
                full_text = news.get("full_text", news.get("summary_en", ""))
                if full_text:
                    preview = full_text[:500] + ("..." if len(full_text) > 500 else "")
                    with st.expander("📄 기사 원문 (영어)", expanded=False):
                        st.text(preview)

                st.markdown("---")

                # ── 포스트 생성 ──
                type_options = ["single", "quote_post", "data_post", "breaking", "whale_alert", "analysis", "opinion"]
                auto_type = detect_post_type(news["title_en"], news.get("summary_en", ""), news.get("source", ""))
                default_idx = type_options.index(auto_type) if auto_type in type_options else 0
                post_type = st.selectbox(
                    "포스트 유형",
                    type_options,
                    index=default_idx,
                    format_func=lambda x: {
                        "single": "📝 단일 포스트",
                        "quote_post": "📌 인물 발언 포스트",
                        "data_post": "💥 온체인/데이터 포스트",
                        "breaking": "🚨 속보 포스트",
                        "whale_alert": "🐋 고래 추적 포스트",
                        "analysis": "📊 심층 분석형",
                        "opinion": "💬 뉴스 + 내 의견",
                    }[x],
                    key=f"type_{i}"
                )
                extra_note = st.text_input(
                    "추가 지시 (선택)",
                    placeholder="예: 테슬라와의 연관성 강조",
                    key=f"extra_{i}"
                )

                if st.button(f"✨ Claude로 포스트 생성", key=f"gen_{i}", type="primary"):
                    with st.spinner("Claude가 포스트를 작성 중..."):
                        try:
                            result = generate_post_with_claude(
                                api_key=claude_api_key,
                                title_en=news["title_en"],
                                article_text=news.get("full_text", news.get("summary_en", "")),
                                source_name=re.sub(r'^[^\s]*\s*', '', news["source"]).strip(),
                                post_type=post_type,
                                extra_instruction=extra_note,
                                model=claude_model,
                                style=selected_style,
                            )
                            st.session_state["generated_posts"][i] = result
                        except Exception as e:
                            st.error(f"Claude API 오류: {e}")

                # ── 생성된 포스트 표시 ──
                if i in st.session_state.get("generated_posts", {}):
                    post_text = st.session_state["generated_posts"][i]
                    st.markdown("#### ✅ 생성된 포스트")
                    st.markdown(f"""<div class="x-preview">{post_text}</div>""", unsafe_allow_html=True)
                    st.code(post_text, language=None)

                    # 다운로드 버튼 (클라우드 + 모바일 호환)
                    download_content = post_text
                    download_content += f"\n\n─────────────────\n"
                    download_content += f"원문 제목: {news['title_en']}\n"
                    download_content += f"출처: {news['source']}\n"
                    download_content += f"원문: {news.get('link', '')}\n"
                    if news.get("video_url"):
                        download_content += f"동영상: {news['video_url']}\n"

                    st.download_button(
                        label="💾 포스트 텍스트 다운로드",
                        data=download_content,
                        file_name=f"포스트_{i+1}.txt",
                        mime="text/plain",
                        key=f"dl_{i}",
                    )
                    st.markdown('<div class="copy-hint">💡 포스트 텍스트를 길게 눌러 복사 → X 앱에 붙여넣기</div>', unsafe_allow_html=True)


# ── 일괄 생성 모드 ──
if "collected_news" in st.session_state and st.session_state["collected_news"] and claude_api_key:
    st.markdown("---")
    st.markdown("## 🚀 일괄 생성 모드")
    st.caption("수집된 모든 기사를 한번에 Claude로 포스트 생성 (기존 v1 방식과 비슷하지만 Claude 품질)")

    batch_type = st.selectbox(
        "일괄 생성 포스트 유형",
        ["single", "quote_post", "data_post", "breaking", "whale_alert", "analysis", "opinion"],
        format_func=lambda x: {
            "single": "📝 단일 포스트",
            "quote_post": "📌 인물 발언 포스트",
            "data_post": "💥 온체인/데이터 포스트",
            "breaking": "🚨 속보 포스트",
            "whale_alert": "🐋 고래 추적 포스트",
            "analysis": "📊 심층 분석형",
            "opinion": "💬 뉴스 + 내 의견",
        }[x],
        key="batch_type"
    )

    if st.button("🚀 전체 일괄 생성", type="primary"):
        news_list = st.session_state["collected_news"]

        gen_progress = st.progress(0)
        all_posts = []

        for idx, news in enumerate(news_list):
            gen_progress.progress((idx + 1) / len(news_list))
            try:
                post_text = generate_post_with_claude(
                    api_key=claude_api_key,
                    title_en=news["title_en"],
                    article_text=news.get("full_text", news.get("summary_en", "")),
                    source_name=re.sub(r'^[^\s]*\s*', '', news["source"]).strip(),
                    post_type=batch_type,
                    model=claude_model,
                    style=selected_style,
                )
                all_posts.append({"news": news, "text": post_text})
            except Exception as e:
                st.warning(f"[{idx+1}] 생성 실패: {e}")
                continue

        gen_progress.progress(1.0)
        st.success(f"일괄 생성 완료! {len(all_posts)}개 포스트")

        # 전체 텍스트 미리보기 + 다운로드
        if all_posts:
            st.markdown("### 📋 전체 포스트 (복사용)")
            separator = "\n\n" + "═" * 40 + "\n\n"
            all_text = separator.join([
                f"[{i+1}/{len(all_posts)}] {p['news']['source']}\n{'─' * 30}\n{p['text']}"
                for i, p in enumerate(all_posts)
            ])
            st.text_area("전체 포스트", value=all_text, height=400, key="batch_all_text")
            st.download_button(
                label="💾 전체 포스트 다운로드",
                data=all_text,
                file_name=f"전체포스트_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
                mime="text/plain",
                key="dl_batch_all",
            )
