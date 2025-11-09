# monitor.py
# Jednoduchý scraper dotačních oznámení s filtrem a deduplikací (SQLite).
# Spouštění: python monitor.py

import re, json, time, sqlite3, pathlib
from datetime import datetime
from typing import List, Dict
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

# ========= Nastavení =========
KEYWORDS = [
    r"regiony", r"kabiny", r"dotace", r"výzva", r"irop", r"sfpi",
    r"npžp|npzp", r"přírodní\s*zahrady", r"sport", r"nsa"
]
SOURCES = [
    {
        "name": "NSA – aktuality",
        "url": "https://nsa.gov.cz/aktuality/",
        # Každá karta má <article> s <a> uvnitř
        "item_selector": "article a",
        "title_attr": None,   # vezmeme text <a>
        "href_attr": "href"
    },
    {
        "name": "NPŽP – novinky",
        "url": "https://www.sfzp.cz/novinky/",
        "item_selector": ".news-list a",
        "title_attr": None,
        "href_attr": "href"
    },
    {
        "name": "Královéhradecký kraj – dotace",
        "url": "https://dotace.khk.cz/",
        "item_selector": "a",  # fallback – chytáme všechny <a>, filtr klíčovými slovy
        "title_attr": None,
        "href_attr": "href"
    },
]

DB_PATH = pathlib.Path("data/seen.sqlite")
OUT_PATH = pathlib.Path("grants.json")
TIMEOUT = 20
# ============================

DB_PATH.parent.mkdir(parents=True, exist_ok=True)

def db_init():
    con = sqlite3.connect(DB_PATH)
    con.execute("""
        CREATE TABLE IF NOT EXISTS seen(
            id INTEGER PRIMARY KEY,
            source TEXT NOT NULL,
            url TEXT NOT NULL UNIQUE,
            title TEXT,
            created_at TEXT NOT NULL
        )
    """)
    con.commit()
    return con

def normalized_text(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()

def match_keywords(text: str) -> bool:
    t = text.lower()
    return any(re.search(p, t, re.IGNORECASE) for p in KEYWORDS)

def fetch(url: str) -> str:
    headers = {
        "User-Agent": "Mozilla/5.0 (GrantMonitor/1.0)"
    }
    r = requests.get(url, headers=headers, timeout=TIMEOUT)
    r.raise_for_status()
    return r.text

def parse_items(html: str, cfg: Dict) -> List[Dict]:
    soup = BeautifulSoup(html, "html.parser")
    items = []
    for a in soup.select(cfg["item_selector"]):
        href = a.get(cfg["href_attr"])
        if not href or not isinstance(href, str): 
            continue
        parsed = urlparse(href)
        if not parsed.scheme:
            href = urljoin(cfg["url"], href)
            parsed = urlparse(href)
        if parsed.scheme not in ("http", "https"):
            continue
        title = a.get(cfg["title_attr"]) if cfg["title_attr"] else a.get_text(" ")
        title = normalized_text(title)
        # Hrubý filtr – jen relevantní odkazy a texty s klíčovými slovy
        if not title:
            continue
        if match_keywords(title) or match_keywords(href):
            items.append({"title": title, "url": href})
    return items

def save_if_new(con, source: str, item: Dict) -> bool:
    try:
        con.execute(
            "INSERT INTO seen(source, url, title, created_at) VALUES(?,?,?,?)",
            (source, item["url"], item["title"], datetime.utcnow().isoformat())
        )
        con.commit()
        return True
    except sqlite3.IntegrityError:
        return False

def run():
    con = db_init()
    all_new = []
    for cfg in SOURCES:
        try:
            html = fetch(cfg["url"])
            items = parse_items(html, cfg)
            for it in items:
                if save_if_new(con, cfg["name"], it):
                    all_new.append({**it, "source": cfg["name"]})
        except Exception as e:
            print(f"[WARN] {cfg['name']}: {e}")

    # uložíme snapshot (poslední běh)
    snapshot = {
        "generated_at": datetime.utcnow().isoformat(),
        "items": all_new
    }
    OUT_PATH.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")

    if all_new:
        print("Nalezeny NOVÉ položky:")
        for it in all_new:
            print(f"- [{it['source']}] {it['title']} -> {it['url']}")
    else:
        print("Žádné nové položky (podle deduplikace v SQLite).")

if __name__ == "__main__":
    run()
