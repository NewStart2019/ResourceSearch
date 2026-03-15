"""
scraper.py
功能：爬取 1lou.me 音乐论坛的专辑数据，保存为 audio.json，并启动 Flask API 服务
依赖：requests, beautifulsoup4, flask, flask-cors
"""

import json
import time
import os
import requests
from bs4 import BeautifulSoup
from flask import Flask, jsonify
from flask_cors import CORS

# ── 配置 ──────────────────────────────────────────────────────────────
BASE_URL   = "https://www.1lou.me/forum-8-{page}.htm?orderby=tid&digest=0"
OUTPUT     = "audio.json"
HEADERS    = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}
DELAY      = 1.0   # 每页请求间隔（秒），避免过于频繁
# ──────────────────────────────────────────────────────────────────────


def get_total_pages(session: requests.Session) -> int:
    """
    步骤 1：请求首页，从 pagination 标签获取总页数。
    倒数第二个子元素的文本可能带有 '...' 前缀，去除后转为 int。
    """
    url = BASE_URL.format(page=1)
    resp = session.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")

    # 找到 class 包含 pagination 的标签
    pagination = soup.find(class_=lambda c: c and "pagination" in c)
    if pagination is None:
        raise RuntimeError("未找到 pagination 标签，请检查页面结构")

    children = [c for c in pagination.children if c != "\n" and str(c).strip()]
    # 倒数第二个子元素
    second_last = children[-2]
    raw_text = second_last.get_text(strip=True)
    # 去除可能存在的 '...' 前缀
    page_text = raw_text.lstrip(".").strip()
    total = int(page_text)
    print(f"[INFO] 总页数：{total}")
    return total


def parse_page(session: requests.Session, page: int) -> list[dict]:
    """
    步骤 2：爬取单页专辑数据。
    返回当前页所有专辑的列表，每条记录为 dict。
    """
    url = BASE_URL.format(page=page)
    resp = session.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    albums = []

    # 找到同时包含 media / thread / tap / top_1 / hidden-sm 的标签 media thread tap hidden-sm
    required_classes = {"media", "thread", "tap", "hidden-sm"}
    threads = soup.find_all(
        lambda tag: required_classes.issubset(set(tag.get("class", [])))
    )

    for thread in threads:
        # 找到 class 包含 'subject break-all' 的子元素
        subject = thread.find(class_=lambda c: c and "subject" in c and "break-all" in c)
        if subject is None:
            continue

        # 提取该标签内所有 <span> 标签
        spans = subject.find_all("span")
        # 至少需要 6 个 span（索引 0-5）
        if len(spans) < 6:
            continue

        # 按位置取值（下标从 0 开始，需要第 2~6 个，即索引 1~5）
        year     = spans[1].get_text(strip=True)
        region   = spans[2].get_text(strip=True)
        typ      = spans[3].get_text(strip=True)
        category = spans[4].get_text(strip=True)
        album    = spans[5].get_text(strip=True)

        albums.append({
            "year":     year,
            "region":   region,
            "type":     typ,
            "category": category,
            "album":    album,
        })

    return albums


def scrape_all() -> list[dict]:
    """
    步骤 2-3：遍历全部页面，汇总并保存数据到 audio.json。
    """
    session = requests.Session()
    total_pages = get_total_pages(session)
    all_albums: list[dict] = []

    for page in range(1, total_pages + 1):
        print(f"[INFO] 正在爬取第 {page}/{total_pages} 页 ...", end=" ")
        try:
            albums = parse_page(session, page)
            all_albums.extend(albums)
            print(f"本页获取 {len(albums)} 条，累计 {len(all_albums)} 条")
        except Exception as e:
            print(f"[WARN] 第 {page} 页爬取失败：{e}")

        # 礼貌性延迟，避免给服务器带来过大压力
        if page < total_pages:
            time.sleep(DELAY)

    # 步骤 3：保存 JSON
    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(all_albums, f, ensure_ascii=False, indent=2)
    print(f"\n[INFO] 数据已保存至 {OUTPUT}，共 {len(all_albums)} 条记录")
    return all_albums


# ── Flask 应用 ─────────────────────────────────────────────────────────
app = Flask(__name__)
CORS(app)  # 允许所有域跨域访问


@app.route("/data", methods=["GET"])
def get_data():
    """步骤 4：读取 audio.json 并以 JSON 格式返回全部数据"""
    if not os.path.exists(OUTPUT):
        return jsonify({"error": f"{OUTPUT} 不存在，请先运行爬虫"}), 404
    with open(OUTPUT, "r", encoding="utf-8") as f:
        data = json.load(f)
    return jsonify(data)


# ── 入口 ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # 如果 audio.json 不存在则先爬取
    if not os.path.exists(OUTPUT):
        print("[INFO] audio.json 不存在，开始爬取数据 ...\n")
        scrape_all()
    else:
        print(f"[INFO] 检测到已有 {OUTPUT}，跳过爬虫，直接启动 Flask 服务")
        print("[INFO] 如需重新爬取，请删除 audio.json 后再运行本脚本")

    print("\n[INFO] 启动 Flask 服务，监听 http://localhost:5000\n")
    app.run(host="0.0.0.0", port=5000, debug=False)