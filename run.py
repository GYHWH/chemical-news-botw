import requests
from bs4 import BeautifulSoup
import os
import sqlite3
from datetime import datetime, timedelta
from urllib.parse import urljoin
from dateutil import parser

# 飞书 Webhook
FEISHU_WEBHOOK = os.getenv("FEISHU_WEBHOOK")
HEADERS = {"User-Agent": "Mozilla/5.0"}

# 最近7天
DAYS_LIMIT = 7
date_limit = datetime.now() - timedelta(days=DAYS_LIMIT)

# ===== SQLite 数据库 =====
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

# ===== 中文化工企业及抓取规则 =====
# 每家企业: (新闻页URL, li选择器, 日期选择器)
COMPANIES = {
    "万华化学": ("https://www.whchem.com/investor/news", "div.news-list li", "span.date"),
    "中国石化": ("http://www.sinopecgroup.com/group/xwzx/xwdt/", "div.news_list li", "span"),
    "中国石油": ("http://www.cnpc.com.cn/cnpc/xwzx/news.shtml", "ul.news_list li", "span"),
    "恒力石化": ("http://www.hengli.com/xinwen/", "ul.news_ul li", "span.date"),
    "荣盛石化": ("http://www.rong-sheng.com/news/", "div.news-list li", "span.date"),
    "中化集团": ("http://www.sinochem.com/xwzx/xwdt/", "ul.news_list li", "span"),
    "美瑞新材": ("http://www.miracll.com/news/", "div.newslist li", "span.date"),
    "恒逸石化": ("http://www.hengyishiye.com/news/", "ul.news_list li", "span"),
    "桐昆股份": ("http://www.tongkun.com.cn/news/", "div.newlist li", "span"),
    "新凤鸣": ("http://www.xinfengming.com/news/", "div.news-list li", "span.date"),
    "东方盛虹": ("http://www.ecc.com.cn/news/", "ul.news_list li", "span"),
    "华鲁恒升": ("http://www.hlhs.com.cn/news/", "ul.news_list li", "span"),
    "扬农化工": ("http://www.yangnong.com.cn/news/", "ul.news_list li", "span"),
    "巨化股份": ("http://www.juhua.com.cn/news/", "ul.news_list li", "span"),
    "中化国际": ("http://www.sinochemint.com/news/", "ul.news_list li", "span"),
    "中国化学": ("http://www.cnce.com.cn/news/", "ul.news_list li", "span"),
    "卫星化学": ("http://www.satellite-chem.com/news/", "ul.news_list li", "span"),
    "龙佰集团": ("http://www.lb-group.com/news/", "ul.news_list li", "span"),
    "天赐材料": ("http://www.tinci.com/news/", "ul.news_list li", "span"),
    "当升科技": ("http://www.easpring.com.cn/news/", "ul.news_list li", "span"),
    "新宙邦": ("http://www.capchem.com/news/", "ul.news_list li", "span")
}

def parse_date(text):
    try:
        return parser.parse(text)
    except:
        return None

def get_news(company, url, li_selector, date_selector):
    news_items = []
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        r.encoding = r.apparent_encoding
        soup = BeautifulSoup(r.text, "lxml")
        for li in soup.select(li_selector):
            a_tag = li.find("a")
            if not a_tag:
                continue
            title = a_tag.get_text(strip=True)
            link = a_tag.get("href")
            if not link.startswith("http"):
                link = urljoin(url, link)

            # 日期
            date_tag = li.select_one(date_selector)
            if date_tag:
                date_text = date_tag.get_text(strip=True)
                news_date = parse_date(date_text)
            else:
                news_date = None

            if not news_date or news_date < date_limit:
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
            if cur.rowcount > 0:  # 只记录新增新闻
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
    for company, (url, li_selector, date_selector) in COMPANIES.items():
        items = get_news(company, url, li_selector, date_selector)
        all_news.extend(items)

    # 只保存并推送新增新闻
    new_news = save_news(all_news)
    send_to_feishu(new_news)
    print(f"抓取完成，共新增 {len(new_news)} 条新闻。")

if __name__ == "__main__":
    main()
