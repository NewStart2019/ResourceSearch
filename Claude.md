
# 任务说明

你需要完成两个任务：
1. 编写一个 Python 爬虫脚本（scraper.py），爬取音乐网站数据并启动 Flask 接口
2. 编写一个前端页面（index.html），展示和检索音乐专辑数据

---

## 任务一：Python 爬虫 + Flask 接口（scraper.py）

### 目标网站
https://www.1lou.me/forum-8-1.htm?orderby=tid&digest=0

### 步骤 1：获取总页数
- 请求目标网站首页
- 找到 class 属性中包含 `pagination` 的标签
- 获取该标签下**倒数第二个**子元素的文本内容
- 去除文本中开头的 `...` 前缀，将剩余部分转换为整数，保存为变量 `totalPage`

### 步骤 2：遍历所有页面，爬取专辑数据
- 从第 1 页到第 `totalPage` 页，依次请求以下 URL：
  `https://www.1lou.me/forum-8-{currentPage}.htm?orderby=tid&digest=0`
- 在每个页面中，找到所有 class 属性**同时包含**以下关键词的标签：
  `media`、`thread`、`tap`、`top_1`、`hidden-sm`
- 对每个匹配标签，提取其子元素中 class 包含 `subject break-all` 的标签
- 在该标签内，按顺序提取以下 `` 标签内容：
  - 第 2 个 ``：年份（year）
  - 第 3 个 ``：地区（region）
  - 第 4 个 ``：类型（type）
  - 第 5 个 ``：分类（category）
  - 第 6 个 ``：专辑名称（album），取其文本内容

### 步骤 3：保存数据
- 将所有专辑数据整理为 JSON 数组，每条记录包含字段：
  `year`、`region`、`type`、`category`、`album`
- 保存至当前目录下的 `audio.json` 文件

### 步骤 4：Flask 接口
- 使用 Flask 启动 HTTP 服务
- 提供接口 `GET /data`，读取 `audio.json` 并以 JSON 格式返回全部数据
- 启用 CORS，允许跨域访问（便于前端直接调用）
- 服务端口：`5000`

---

## 任务二：前端查询页面（index.html）

### 数据加载
- 页面加载时，通过 `fetch` 请求 `http://localhost:5000/data` 获取专辑数据

### 筛选区域（页面顶部）
- 提供 4 个下拉筛选器，分别对应：**年份**、**地区**、**类型**、**分类**
- 下拉选项根据数据动态生成，包含"全部"默认选项
- 多个筛选条件同时生效（AND 逻辑）

### 搜索框
- 提供一个文本输入框，支持按**专辑名称**进行模糊搜索
- 搜索与筛选条件联动，实时过滤表格数据

### 数据表格
- 以表格展示过滤后的专辑列表
- 表格列：**年份**、**地区**、**类型**、**分类**、**专辑名称**
- 表格需支持基本样式（斑马纹或行悬停高亮）

---

## 输出要求
- 输出两个完整、可直接运行的文件：`scraper.py` 和 `index.html`
- Python 依赖：`requests`、`beautifulsoup4`、`flask`、`flask-cors`
- 前端使用纯 HTML + CSS + JavaScript，不依赖外部框架
- 添加必要的错误处理和注释
