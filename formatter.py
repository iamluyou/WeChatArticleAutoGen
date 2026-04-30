"""
格式化模块：自定义 mistune 渲染器，一步到位输出带内联样式的微信 HTML
"""
import mistune

from crawler import ArticleData, ImageData, VideoData
import wechat_style
from logger import setup_logger

logger = setup_logger("formatter")


class WeChatRenderer(mistune.HTMLRenderer):
    """微信公众号内联样式渲染器，继承 HTMLRenderer 保留默认行为"""

    NAME = "wechat"

    def paragraph(self, text):
        return f'<p style="{wechat_style.PARAGRAPH}">{text}</p>\n'

    def heading(self, text, level, **attrs):
        if level == 1:
            style = wechat_style.H1
        elif level == 2:
            style = wechat_style.H2
        elif level == 3:
            style = wechat_style.H3
        else:
            style = wechat_style.HEADING_DEFAULT
        return f'<h{level} style="{style}">{text}</h{level}>\n'

    def block_quote(self, text):
        return f'<blockquote style="{wechat_style.BLOCKQUOTE}">{text}</blockquote>\n'

    def image(self, text, url, title=None):
        return (
            f'<p style="{wechat_style.IMAGE_WRAPPER}">'
            f'<img src="{url}" alt="{text}" style="{wechat_style.IMAGE}" />'
            f'</p>\n'
        )

    def link(self, text, url, title=None):
        return f'<a href="{url}" style="{wechat_style.LINK}">{text}</a>'

    def list(self, text, ordered, **attrs):
        tag = "ol" if ordered else "ul"
        return f'<{tag} style="{wechat_style.LIST}">\n{text}</{tag}>\n'

    def list_item(self, text, **attrs):
        return f'<li style="{wechat_style.LIST_ITEM}">{text}</li>\n'

    def codespan(self, text):
        return f'<code style="{wechat_style.CODE_INLINE}">{text}</code>'

    def block_code(self, code, info=None):
        escaped = mistune.escape(code)
        return f'<pre style="{wechat_style.CODE_BLOCK}"><code>{escaped}</code></pre>\n'

    def emphasis(self, text):
        return f'<em style="{wechat_style.EMPHASIS}">{text}</em>'

    def strong(self, text):
        return f'<strong style="{wechat_style.STRONG}">{text}</strong>'

    def thematic_break(self):
        return f'<hr style="{wechat_style.HR}" />\n'

    def table(self, text):
        return f'<table style="{wechat_style.TABLE}">\n{text}</table>\n'

    def table_head(self, text):
        return f"<thead>\n{text}</thead>\n"

    def table_body(self, text):
        return f"<tbody>\n{text}</tbody>\n"

    def table_row(self, text):
        return f"<tr>\n{text}</tr>\n"

    def table_cell(self, text, align=None, head=False):
        style = wechat_style.TABLE_CELL
        if head:
            style += wechat_style.TABLE_HEAD
        return f'<td style="{style}">{text}</td>\n'


def preprocess_markdown(md_text: str, images: list, videos: list) -> str:
    """
    将 [图片N] 和 [视频N] 标记替换为标准 MD 图片语法或 HTML 占位符

    Args:
        md_text: LLM 输出的 Markdown 文本
        images: 图片列表
        videos: 视频列表

    Returns:
        处理后的 Markdown 文本
    """
    # 替换图片标记
    for img in images:
        placeholder = f"[图片{img.index}]"
        replacement = f"![{img.alt}]({img.url})"
        md_text = md_text.replace(placeholder, replacement)

    # 替换视频标记（直接插入 HTML 占位符，不经过 MD 渲染）
    for video in videos:
        placeholder = f"[视频{video.index}]"
        replacement = (
            f'<div style="{wechat_style.VIDEO_PLACEHOLDER}">'
            f'<p style="{wechat_style.VIDEO_TEXT}">📹 视频位置</p>'
            f'<p style="{wechat_style.VIDEO_HINT}">请在微信公众号编辑器中手动插入视频</p>'
            f'<p style="{wechat_style.VIDEO_HINT}">原始链接：{video.url}</p>'
            f'</div>'
        )
        md_text = md_text.replace(placeholder, replacement)

    return md_text


def format_article(
    md_text: str,
    article: ArticleData,
    source_url: str = "",
    gen_time: str = "",
) -> str:
    """
    将 Markdown 转换为微信公众号兼容 HTML

    Args:
        md_text: LLM 输出的 Markdown 文本
        article: 原始文章数据（图片/视频信息）
        source_url: 原始链接
        gen_time: 生成时间

    Returns:
        完整的 HTML 字符串
    """
    from datetime import datetime
    gen_time = gen_time or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    source_url = source_url or article.source_url

    # 1. 预处理：替换 [图片N] 和 [视频N] 标记
    processed_md = preprocess_markdown(md_text, article.images, article.videos)

    # 2. 使用自定义渲染器渲染
    renderer = WeChatRenderer()
    markdown = mistune.create_markdown(renderer=renderer)
    html_body = markdown(processed_md)

    # 3. 包裹外层 section + 头部注释
    html = (
        f'<!--\n'
        f'  微信公众号文章 - 由 WeChatArticleAutoGen 自动生成\n'
        f'  原始链接：{source_url}\n'
        f'  生成时间：{gen_time}\n'
        f'  排版风格：{wechat_style.STYLE_THEME}\n'
        f'\n'
        f'  使用方式：\n'
        f'  1. 用浏览器打开此文件\n'
        f'  2. 全选复制（Ctrl+A → Ctrl+C）\n'
        f'  3. 在微信公众号后台编辑器中粘贴（Ctrl+V）\n'
        f'  4. 手动替换 [视频] 占位符\n'
        f'\n'
        f'  注意事项：\n'
        f'  - 图片粘贴后微信会自动转存\n'
        f'  - 视频需手动上传\n'
        f'  - 建议在手机端预览确认排版效果\n'
        f'-->\n'
        f'<section style="{wechat_style.SECTION_WRAPPER}">\n'
        f'{html_body}'
        f'</section>\n'
    )

    logger.info(
        f"格式化完成 - HTML 长度: {len(html)}, "
        f"图片替换: {len(article.images)}, 视频替换: {len(article.videos)}"
    )

    return html
