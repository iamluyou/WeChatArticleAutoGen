"""
爬虫模块：抓取 URL 内容，多级正文提取，收集图片/视频
"""
import json
import os
import random
import re
import time
from dataclasses import dataclass, field

import httpx
from bs4 import BeautifulSoup
from logger import setup_logger

logger = setup_logger("crawler")

# 请求头伪装
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}


@dataclass
class ImageData:
    url: str
    alt: str = ""
    index: int = 0


@dataclass
class VideoData:
    url: str
    poster: str = ""
    index: int = 0


@dataclass
class ArticleData:
    title: str = ""
    author: str = ""
    publish_time: str = ""
    content_html: str = ""
    content_text: str = ""
    images: list = field(default_factory=list)
    videos: list = field(default_factory=list)
    source_url: str = ""


def _fetch_html(url: str, timeout: float = 30.0, proxy: str = "", cookies: dict = None) -> str:
    """抓取页面 HTML"""
    client_kwargs = {
        "timeout": httpx.Timeout(connect=10.0, read=timeout, write=10.0, pool=10.0),
        "follow_redirects": True,
    }
    if proxy:
        client_kwargs["proxy"] = proxy

    with httpx.Client(**client_kwargs) as client:
        response = client.get(url, headers=HEADERS, cookies=cookies or {})
        response.raise_for_status()
        return response.text


def _extract_with_trafilatura(html: str, url: str) -> tuple[str, str, dict]:
    """第一级：trafilatura 提取"""
    try:
        import trafilatura
        metadata = trafilatura.extract(html, output_format="json")
        if metadata:
            meta = json.loads(metadata)
            text = meta.get("text", "")
            if text and len(text) > 100:
                content_html = trafilatura.extract(html, output_format="html") or ""
                return text, content_html, meta
    except Exception as e:
        logger.debug(f"trafilatura 提取失败: {e}")
    return "", "", {}


def _extract_with_readability(html: str) -> tuple[str, str, str]:
    """第二级：readability-lxml 提取"""
    try:
        from readability import Document
        doc = Document(html)
        content_html = doc.summary()
        title = doc.title()
        # 从 HTML 提取纯文本
        soup = BeautifulSoup(content_html, "html.parser")
        text = soup.get_text(separator="\n", strip=True)
        if text and len(text) > 100:
            return text, content_html, title
    except Exception as e:
        logger.debug(f"readability 提取失败: {e}")
    return "", "", ""


def _extract_with_newspaper(html: str, url: str) -> tuple[str, str, str, str]:
    """第三级：newspaper4k 提取"""
    try:
        from newspaper import Article
        article = Article(url)
        article.set_html(html)
        article.parse()
        if article.text and len(article.text) > 100:
            return article.text, article.html or "", article.title, article.authors
    except Exception as e:
        logger.debug(f"newspaper 提取失败: {e}")
    return "", "", "", []


def _extract_with_bs4(html: str) -> tuple[str, str, str]:
    """第四级：BeautifulSoup 手动提取"""
    soup = BeautifulSoup(html, "html.parser")

    # 去除噪音标签
    for tag in soup.find_all(["script", "style", "nav", "footer", "aside", "header"]):
        tag.decompose()

    # 查找正文区域
    content_area = (
        soup.find("article")
        or soup.find("div", class_=lambda c: c and any(k in str(c).lower() for k in ["content", "article", "body", "post"]))
        or soup.find("main")
        or soup.find("body")
    )
    if not content_area:
        return "", "", ""

    text = content_area.get_text(separator="\n", strip=True)
    title_tag = soup.find("h1")
    title = title_tag.get_text(strip=True) if title_tag else ""
    return text, str(content_area), title


def _extract_images(html: str, content_area_html: str = "") -> list:
    """从 HTML 中提取图片"""
    soup = BeautifulSoup(content_area_html or html, "html.parser")

    # 微信公众号：优先从 js_content 区域提取
    wx_content = soup.find("div", id="js_content")
    if wx_content:
        search_area = wx_content
    else:
        search_area = soup

    images = []
    idx = 1

    for img in search_area.find_all("img"):
        src = img.get("data-src") or img.get("src") or ""
        if not src:
            continue
        # 补全协议头（微信图片可能以 // 开头）
        if src.startswith("//"):
            src = "https:" + src
        # 过滤 data URI 和 base64
        if src.startswith("data:"):
            continue
        # 过滤小图片（追踪图、图标等）
        width = img.get("width", "")
        height = img.get("height", "")
        if width and height:
            try:
                if int(width) < 50 or int(height) < 50:
                    continue
            except ValueError:
                pass
        # 过滤非正文图片（头像、二维码等）
        css_class = " ".join(img.get("class", []))
        if any(skip in css_class for skip in [
            "avatar", "qrcode", "qr_code", "follow", "profile", "icon",
        ]):
            continue
        alt = img.get("alt", "")
        images.append(ImageData(url=src, alt=alt, index=idx))
        idx += 1

    return images


def _extract_videos(html: str, content_area_html: str = "") -> list:
    """从 HTML 中提取视频"""
    soup = BeautifulSoup(content_area_html or html, "html.parser")
    videos = []

    idx = 1
    # <video> 标签
    for video in soup.find_all("video"):
        src = video.get("src", "")
        poster = video.get("poster", "")
        if not src:
            source = video.find("source")
            if source:
                src = source.get("src", "")
        if src:
            videos.append(VideoData(url=src, poster=poster, index=idx))
            idx += 1

    # <iframe> 视频
    for iframe in soup.find_all("iframe"):
        src = iframe.get("src", "")
        if src and any(k in src for k in ["video", "player", "bilibili", "youtube", "v.qq"]):
            videos.append(VideoData(url=src, index=idx))
            idx += 1

    return videos


def _insert_media_markers(
    content_html: str, content_text: str, images: list, videos: list
) -> str:
    """
    利用 content_html 中的图片/视频标签位置，在 content_text 中插入 [图片N]/[视频N] 标记

    策略：解析 content_html，遍历所有元素，遇到 <img> 或 <video>/<iframe> 时
    找到其在文本流中的大致位置，将标记插入到 content_text 的最近段落边界处。

    Args:
        content_html: 正文 HTML
        content_text: 正文纯文本
        images: 已提取的图片列表
        videos: 已提取的视频列表

    Returns:
        带有媒体标记的正文文本
    """
    if not content_html or not images + videos:
        return content_text

    # 构建 URL → 标记 的映射（同时存储原始和补全协议头的版本）
    img_marker_map = {}
    for img in images:
        marker = f"[图片{img.index}]"
        img_marker_map[img.url] = marker
        # 补全协议头的版本也加入映射
        if img.url.startswith("https://"):
            img_marker_map[img.url.replace("https://", "//")] = marker

    vid_marker_map = {}
    for vid in videos:
        marker = f"[视频{vid.index}]"
        vid_marker_map[vid.url] = marker
        if vid.url.startswith("https://"):
            vid_marker_map[vid.url.replace("https://", "//")] = marker

    # 从 content_html 中按顺序提取媒体标记
    soup = BeautifulSoup(content_html, "html.parser")

    # 收集文本段落和媒体标记，保持原文顺序
    segments = []  # [(type, content/markers)]
    for element in soup.descendants:
        if element.name == "img":
            src = element.get("data-src") or element.get("src") or ""
            if src.startswith("//"):
                src = "https:" + src
            if src in img_marker_map:
                segments.append(("media", img_marker_map[src]))
        elif element.name == "video":
            src = element.get("src", "")
            if not src:
                source = element.find("source")
                if source:
                    src = source.get("src", "")
            if src in vid_marker_map:
                segments.append(("media", vid_marker_map[src]))
        elif element.name == "iframe":
            src = element.get("src", "")
            if src in vid_marker_map:
                segments.append(("media", vid_marker_map[src]))

    if not segments:
        return content_text

    # 在 content_text 中的段落边界处插入标记
    # 将文本按段落拆分
    paragraphs = re.split(r"\n{2,}", content_text)

    # 策略：均匀分配标记到段落中
    # 如果有 N 个标记和 M 个段落，每 ceil(M/(N+1)) 个段落插入一个标记
    num_markers = len(segments)
    num_paragraphs = len(paragraphs)

    if num_paragraphs == 0:
        return content_text

    # 计算每个标记应插入的段落索引
    marker_positions = []
    for i in range(num_markers):
        # 均匀分布：在第 round((i+1) * num_paragraphs / (num_markers+1)) 段之后插入
        pos = round((i + 1) * num_paragraphs / (num_markers + 1))
        marker_positions.append(min(pos, num_paragraphs))

    # 从后往前插入，避免索引偏移
    result_paragraphs = list(paragraphs)
    for i in range(num_markers - 1, -1, -1):
        pos = marker_positions[i]
        marker_text = segments[i][1]
        # 插入到段落之后
        if pos < len(result_paragraphs):
            result_paragraphs.insert(pos, marker_text)
        else:
            result_paragraphs.append(marker_text)

    return "\n\n".join(result_paragraphs)


def read_local_markdown(filepath: str) -> ArticleData:
    """
    读取本地 Markdown 文件，返回结构化数据

    Args:
        filepath: 本地 .md 文件路径

    Returns:
        ArticleData 结构化文章数据
    """
    logger.info(f"读取本地文件: {filepath}")

    if not os.path.exists(filepath):
        raise FileNotFoundError(f"文件不存在: {filepath}")

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    if not content.strip():
        raise ValueError(f"文件内容为空: {filepath}")

    # 从文件名提取标题（兜底）
    filename_title = os.path.splitext(os.path.basename(filepath))[0]

    # 尝试从内容提取标题（第一行 # 标题）
    title = filename_title
    lines = content.strip().split("\n")
    for line in lines:
        line_stripped = line.strip()
        if line_stripped.startswith("#"):
            title = line_stripped.lstrip("#").strip()
            break

    # 从 Markdown 中提取图片 ![alt](url)
    images = []
    img_pattern = re.compile(r'!\[([^\]]*)\]\(([^)]+)\)')
    for idx, match in enumerate(img_pattern.finditer(content), 1):
        alt, url = match.group(1), match.group(2)
        if not url.startswith("data:"):
            images.append(ImageData(url=url, alt=alt, index=idx))

    return ArticleData(
        title=title,
        author="",
        publish_time="",
        content_html="",
        content_text=content,
        images=images,
        videos=[],
        source_url=f"file://{os.path.abspath(filepath)}",
    )


def crawl(url: str, timeout: float = 30.0, proxy: str = "", cookies: dict = None) -> ArticleData:
    """
    抓取 URL 并返回结构化数据

    Args:
        url: 目标 URL
        timeout: 请求超时时间
        proxy: HTTP 代理地址
        cookies: 请求携带的 cookie

    Returns:
        ArticleData 结构化文章数据
    """
    logger.info(f"开始抓取: {url}")

    # 随机间隔，防风控
    time.sleep(random.uniform(0.5, 1.5))

    # 抓取 HTML
    try:
        html = _fetch_html(url, timeout=timeout, proxy=proxy, cookies=cookies)
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP 错误 [{url}]: {e.response.status_code}")
        raise
    except httpx.RequestError as e:
        logger.error(f"请求失败 [{url}]: {e}")
        raise

    if not html or len(html) < 200:
        logger.error(f"页面内容过短 [{url}]")
        raise ValueError(f"页面内容过短，可能不是有效文章: {url}")

    # 多级正文提取
    title = ""
    author = ""
    publish_time = ""
    content_text = ""
    content_html = ""
    extractor_used = ""

    # 第一级：trafilatura
    text, c_html, meta = _extract_with_trafilatura(html, url)
    if text:
        content_text = text
        content_html = c_html
        title = meta.get("title", "")
        author = meta.get("author", "")
        publish_time = meta.get("date", "")
        extractor_used = "trafilatura"
        logger.info(f"trafilatura 提取成功，正文长度: {len(text)}")

    # 第二级：readability
    if not content_text:
        text, c_html, t = _extract_with_readability(html)
        if text:
            content_text = text
            content_html = c_html
            title = t
            extractor_used = "readability"
            logger.info(f"readability 提取成功，正文长度: {len(text)}")

    # 第三级：newspaper
    if not content_text:
        text, c_html, t, authors = _extract_with_newspaper(html, url)
        if text:
            content_text = text
            content_html = c_html
            title = t
            author = ", ".join(authors) if isinstance(authors, list) else str(authors)
            extractor_used = "newspaper"
            logger.info(f"newspaper 提取成功，正文长度: {len(text)}")

    # 第四级：BS4 手动
    if not content_text:
        text, c_html, t = _extract_with_bs4(html)
        if text:
            content_text = text
            content_html = c_html
            title = t
            extractor_used = "bs4"
            logger.info(f"BS4 手动提取成功，正文长度: {len(text)}")

    if not content_text:
        logger.error(f"所有提取器均失败 [{url}]")
        raise ValueError(f"无法提取正文，请检查 URL 是否为文章页面: {url}")

    # 从 HTML title 兜底标题
    if not title:
        soup = BeautifulSoup(html, "html.parser")
        # 微信公众号标题在 h1#activity-name
        wx_title = soup.find("h1", id="activity-name")
        if wx_title:
            title = wx_title.get_text(strip=True)
        elif soup.title:
            title = soup.title.get_text(strip=True)

    # 提取图片和视频（优先从原始 HTML 提取，因为 content_html 可能丢失懒加载图片）
    # 提取图片和视频（始终用原始 HTML，因为 content_html 可能丢失懒加载图片）
    images = _extract_images(html, html)
    videos = _extract_videos(html, html)

    # 在正文文本中插入图片/视频位置标记
    # 使用原始 HTML 插入标记，因为 content_html 可能不完整（如微信 data-src 图片丢失）
    content_text = _insert_media_markers(html, content_text, images, videos)

    logger.info(
        f"抓取完成 [{url}] - 提取器: {extractor_used}, "
        f"标题: {title[:30]}, 图片: {len(images)}, 视频: {len(videos)}"
    )

    return ArticleData(
        title=title,
        author=author,
        publish_time=publish_time,
        content_html=content_html,
        content_text=content_text,
        images=images,
        videos=videos,
        source_url=url,
    )
