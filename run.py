import requests
from bs4 import BeautifulSoup
import os
import sqlite3
from datetime import datetime, timedelta
from urllib.parse import urljoin
import re
from dateutil import parser

FEISHU_WEBHOOK = os.getenv("FEISHU_WEBHOOK")


# ===== 中文企业列表，可扩展 =====
COMPANIES = {
    "万华化学": "https://www.whchem.com/investor/news",
    "中国石化": "http://www.sinopecgroup.com/group/xwzx/xwdt/",
    "中国石油": "http://www.cnpc.com.cn/cnpc/xwzx/news.shtml",
    "恒力石化": "http://www.hengli.com/xinwen/",
    "荣盛石化": "http://www.rong-sheng.com/news/",
    "中化集团": "http://www.sinochem.com/xwzx/xwdt/",
    "美瑞新材":"http://www.miracll.com/news/",
    "中国石化":"http://www.sinopec.com.cn/list/channel_8/",
    "恒力石化":"http://www.hengli.com/news/",
    "荣盛石化":"http://www.cnrsgf.com/news/",
    "恒逸石化":"http://www.hengyishiye.com/news/",
    "桐昆股份":"http://www.tongkun.com.cn/news/",
    "新凤鸣":"http://www.xinfengming.com/news/",
    "东方盛虹":"http://www.ecc.com.cn/news/",
    "华鲁恒升":"http://www.hlhs.com.cn/news/", 
    "扬农化工":"http://www.yangnong.com.cn/news/",
    "巨化股份":"http://www.juhua.com.cn/news/",
    "中化国际":"http://www.sinochemint.com/news/",
    "中国化学":"http://www.cnce.com.cn/news/",
    "卫星化学":"http://www.satellite-chem.com/news/",
    "龙佰集团":"http://www.lb-group.com/news/",
    "天赐材料":"http://www.tinci.com/news/",
    "当升科技":"http://www.easpring.com.cn/news/",
    "新宙邦":"http://www.capchem.com/news/"
    
}

HEADERS = {"User-Agent": "Mozilla/5.0"}

# SQLite 数据库，用于去重和历史存储
conn = sqlite3.connect("news.db")
cur = conn.cursor()
cur.execute("""
CREATE TABLE IF NOT EXISTS news (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company TEXT,
    title TEXT,
    link TEXT,
    date TEXT,
    UNIQUE(title, link)
)
""")
conn.commit()

DAYS_LIMIT = 7
date_limit = datetime.now() - timedelta(days=DAYS_LIMIT)

def parse_date(text):
    match = re.search(r'(\d{4}[-/年]\d{1,2}[-/月]\d{1,2})', text)
    if match:
        try:
            return parser.parse(match.group().replace("年","-").replace("月","-").replace("日",""))
        except:
            return None
    return None

def get_news(company, url):
    news_items = []
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        r.encoding = r.apparent_encoding
        soup = BeautifulSoup(r.text, "lxml")
        for a in soup.find_all("a", href=True):
            title = a.get_text(strip=True)
            link = a["href"]
            if len(title) < 10:
                continue
            if not link.startswith("http"):
                link = urljoin(url, link)
            text_block = a.parent.get_text()
            news_date = parse_date(text_block)
            if not news_date:
                news_date = datetime.now()
            if news_date < date_limit:
                continue
            news_items.append((company, title, link, news_date.strftime("%Y-%m-%d")))
    except Exception as e:
        print(f"抓取 {company} 出错:", e)
    return news_items

def save_news(news_list):
    saved = []
    for item in news_list:
        try:
            cur.execute("INSERT OR IGNORE INTO news (company,title,link,date) VALUES (?,?,?,?)", item)
            saved.append(item)
        except:
            continue
    conn.commit()
    return saved

def send_to_feishu(news_list):
    if not news_list:
        text = "化工原材料企业最近7天没有新新闻。"
    else:
        text = "【化工原材料企业官网最近7天新闻】\n\n"
        for company, title, link, date in news_list:
            text += f"【{company}】{date}\n{title}\n{link}\n\n"
    payload = {"msg_type":"text", "content":{"text":text}}
    try:
        requests.post(FEISHU_WEBHOOK, json=payload)
    except Exception as e:
        print("飞书推送失败:", e)

def main():
    all_news = []
    for company, url in COMPANIES.items():
        items = get_news(company, url)
        all_news.extend(items)
    saved_news = save_news(all_news)
    send_to_feishu(saved_news)

if __name__ == "__main__":
    main()
