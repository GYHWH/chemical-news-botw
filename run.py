import requests
from bs4 import BeautifulSoup
import os

FEISHU_WEBHOOK = os.getenv("FEISHU_WEBHOOK")

COMPANIES = {
    "BASF": "https://www.basf.com/global/en/media/news-releases.html",
    "Dow": "https://corporate.dow.com/en-us/news.html",
    "DuPont": "https://www.dupont.com/news.html",
    "Covestro": "https://www.covestro.com/en/news",
    "SABIC": "https://www.sabic.com/en/news"
}

def get_news(url):
    news = []
    try:
        r = requests.get(url, timeout=10)
        soup = BeautifulSoup(r.text, "lxml")
        for a in soup.find_all("a", href=True):
            title = a.get_text(strip=True)
            link = a["href"]

            if len(title) < 20:
                continue

            if not link.startswith("http"):
                link = url.rstrip("/") + "/" + link.lstrip("/")

            news.append((title, link))
    except:
        pass
    return news[:5]

def send_to_feishu(all_news):
    if not all_news:
        text = "今日未抓到企业官网新闻。"
    else:
        text = "化工原材料企业官网最新新闻：\n\n"
        for company, items in all_news.items():
            text += f"【{company}】\n"
            for title, link in items:
                text += f"{title}\n{link}\n\n"

    payload = {
        "msg_type": "text",
        "content": {"text": text}
    }

    requests.post(FEISHU_WEBHOOK, json=payload)

def main():
    results = {}
    for name, url in COMPANIES.items():
        news = get_news(url)
        if news:
            results[name] = news

    send_to_feishu(results)

if __name__ == "__main__":
    main()
