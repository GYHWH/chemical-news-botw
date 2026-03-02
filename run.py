import requests
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS
from urllib.parse import urlparse
from datetime import datetime, timedelta
import os
import re
from dateutil import parser

FEISHU_WEBHOOK = os.getenv("FEISHU_WEBHOOK")

KEYWORDS = [
    "chemical raw material company press release",
    "化工 原材料 公司 新闻",
    "chemical materials manufacturer news"
]

MAX_RESULTS = 30
DAYS_LIMIT = 7

def extract_domain(url):
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"

def search_domains():
    domains = set()
    with DDGS() as ddgs:
        for kw in KEYWORDS:
            results = ddgs.text(kw, max_results=MAX_RESULTS)
            for r in results:
                domains.add(extract_domain(r["href"]))
    return list(domains)

def find_news_page(domain):
    paths = ["/news", "/press", "/media", "/newsroom"]
    for p in paths:
        url = domain + p
        try:
            r = requests.get(url, timeout=5)
            if r.status_code == 200:
                return url
        except:
            continue
    return None

def extract_recent_news(news_url):
    news_list = []
    try:
        r = requests.get(news_url, timeout=8)
        soup = BeautifulSoup(r.text, "lxml")

        for a in soup.find_all("a", href=True):
            title = a.get_text(strip=True)
            link = a["href"]

            if len(title) < 15:
                continue

            if not link.startswith("http"):
                link = news_url.rstrip("/") + "/" + link.lstrip("/")

            news_list.append((title, link))

    except:
        pass

    return news_list

def send_to_feishu(news_items):
    if not news_items:
        text = "化工新闻：最近7天没有发现新的企业官网新闻。"
    else:
        text = "化工新闻（最近7天）：\n\n"
        for title, link in news_items[:20]:
            text += f"{title}\n{link}\n\n"

    payload = {
        "msg_type": "text",
        "content": {
            "text": f"化工\n{text}"
        }
    }

    requests.post(FEISHU_WEBHOOK, json=payload)

def main():
    all_news = []
    domains = search_domains()

    for d in domains:
        news_page = find_news_page(d)
        if news_page:
            items = extract_recent_news(news_page)
            all_news.extend(items)

    send_to_feishu(all_news)

if __name__ == "__main__":
    main()
