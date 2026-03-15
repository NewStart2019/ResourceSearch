"""
scraper.py
==========
步骤1 - 获取总页数（pagination 标签倒数第二个子元素，去除 '...' 前缀）
步骤2 - 遍历所有页面
        · 匹配 class 同时含 media / thread / tap / hidden-sm 的标签
        · 子元素取 class 含 'subject break-all' 的标签
        · 在该标签内按顺序提取 <a> 标签：
            a[1] → year（年份）
            a[2] → region（地区）
            a[3] → type（类型）
            a[4] → category（分类）
            a[5] → album（专辑名称，文本）+ href 拼接 albumUrl
步骤3 - 保存至 audio.json（字段：year/region/type/category/album/albumUrl）
步骤4 - Flask GET /data，CORS 开启，端口 5000

依赖：pip install requests beautifulsoup4 flask flask-cors
"""

import json
import os
import time

import requests
from bs4 import BeautifulSoup
from flask import Flask, jsonify
from flask_cors import CORS

# ── 全局配置 ────────────────────────────────────────────────────────────
BASE_URL      = "https://www.1lou.me/forum-8-{page}.htm?orderby=tid&digest=0"
SITE_ROOT     = "https://www.1lou.me"
JSON_FILE     = "audio.json"
REQUEST_DELAY = 1.0   # 每页请求间隔（秒）
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "zh-CN,zh;q=0.9",
}


# ════════════════════════════════════════════════════════════════════════
# 步骤 1：获取总页数
# ════════════════════════════════════════════════════════════════════════
def get_total_pages(session: requests.Session) -> int:
    """
    请求首页，找到 class 包含 'pagination' 的标签，
    取其倒数第二个子元素的文本，去除开头 '...' 后转为 int。
    """
    url = BASE_URL.format(page=1)
    resp = session.get(url, headers=HEADERS, timeout=20)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")

    pagination = soup.find(
        lambda tag: "pagination" in " ".join(tag.get("class", []))
    )
    if pagination is None:
        raise RuntimeError("未找到 pagination 标签，请检查页面结构")

    # 过滤纯空白文本节点
    children = [c for c in pagination.children if str(c).strip()]

    if len(children) < 2:
        raise RuntimeError(f"pagination 子元素不足，仅有 {len(children)} 个")

    raw = children[-2].get_text(strip=True)   # 倒数第二个子元素
    total = int(raw.lstrip("."))              # 去除 '...' 前缀
    print(f"[步骤1] 总页数 = {total}")
    return total


# ════════════════════════════════════════════════════════════════════════
# 步骤 2：解析单页专辑数据
# ════════════════════════════════════════════════════════════════════════
def parse_page(session: requests.Session, page: int) -> list:
    """
    匹配 class 同时包含 media / thread / tap / hidden-sm 的标签，
    在其子元素 class 含 'subject break-all' 的标签内，
    按顺序提取 <a> 标签（下标从 0 开始）：
      anchors[1] → year
      anchors[2] → region
      anchors[3] → type
      anchors[4] → category
      anchors[5] → album 文本 + href → albumUrl
    """
    url = BASE_URL.format(page=page)
    resp = session.get(url, headers=HEADERS, timeout=20)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")

    # class 需同时包含这 4 个关键词
    REQUIRED = {"media", "thread", "tap", "hidden-sm"}

    threads = soup.find_all(
        lambda tag: REQUIRED.issubset(set(tag.get("class", [])))
    )

    records = []
    for thread in threads:
        # 子元素：class 同时含 'subject' 和 'break-all'
        subject = thread.find(
            lambda tag: (
                "subject"   in tag.get("class", []) and
                "break-all" in tag.get("class", [])
            )
        )
        if subject is None:
            continue

        # 取该标签内所有 <a> 标签
        anchors = subject.find_all("a")
        if len(anchors) < 6:
            continue   # 数量不足，跳过

        # 按位置提取（索引 1~5，即第 2~6 个）
        year     = anchors[1].get_text(strip=True)
        region   = anchors[2].get_text(strip=True)
        typ      = anchors[3].get_text(strip=True)
        category = anchors[4].get_text(strip=True)
        album    = anchors[5].get_text(strip=True)

        # 第 6 个 <a> 的 href 拼接站点根域名
        href     = anchors[5].get("href", "")
        album_url = SITE_ROOT + "/" + href if href else ""

        records.append({
            "year":     year,
            "region":   region,
            "type":     typ,
            "category": category,
            "album":    album,
            "albumUrl": album_url,
        })

    return records


# ════════════════════════════════════════════════════════════════════════
# 步骤 2-3：爬取全部页面，保存 audio.json
# ════════════════════════════════════════════════════════════════════════
def scrape_and_save() -> list:
    """遍历所有页面，汇总记录，写入 audio.json。"""
    session = requests.Session()
    total_pages = get_total_pages(session)
    all_records = []

    for page in range(1, total_pages + 1):
        print(f"[步骤2] 第 {page:>4}/{total_pages} 页...", end=" ", flush=True)
        try:
            records = parse_page(session, page)
            all_records.extend(records)
            print(f"本页 {len(records):>3} 条 | 累计 {len(all_records)} 条")
        except Exception as exc:
            print(f"[WARN] 失败：{exc}")

        if page < total_pages:
            time.sleep(REQUEST_DELAY)

    # 步骤 3：保存
    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(all_records, f, ensure_ascii=False, indent=2)

    print(f"\n[步骤3] 已保存 {len(all_records)} 条记录 → {JSON_FILE}")
    return all_records


# ════════════════════════════════════════════════════════════════════════
# 步骤 4：Flask 接口
# ════════════════════════════════════════════════════════════════════════
app = Flask(__name__)
CORS(app)


@app.route("/data", methods=["GET"])
def get_data():
    """读取 audio.json，以 JSON 格式返回全部数据。"""
    if not os.path.exists(JSON_FILE):
        return jsonify({"error": f"{JSON_FILE} 不存在，请先运行爬虫"}), 404
    with open(JSON_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return jsonify(data)


# ════════════════════════════════════════════════════════════════════════
# 入口
# ════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    if not os.path.exists(JSON_FILE):
        print("=" * 60)
        print("  audio.json 不存在，开始爬取数据")
        print("=" * 60)
        scrape_and_save()
    else:
        print(f"[INFO] 检测到已有 {JSON_FILE}，跳过爬取")
        print("[INFO] 如需重新爬取，请删除 audio.json 后再运行")

    print("\n[步骤4] 启动 Flask 服务 → http://localhost:5000/data\n")
    app.run(host="0.0.0.0", port=5000, debug=False)