"""
单元测试 + Mock 测试
运行方式: python -m pytest tests/ -v
"""
import json
import os
import sys
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# 确保项目根目录在 sys.path 中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ==================== utils.py 测试 ====================

class TestSanitizeFilename:
    """文件名清理函数测试"""

    def test_normal_title(self):
        from utils import sanitize_filename
        assert sanitize_filename("深度解读AI发展趋势") == "深度解读AI发展趋势"

    def test_special_chars(self):
        from utils import sanitize_filename
        result = sanitize_filename('测试：什么是AI？')
        assert '?' not in result
        assert '：' not in result

    def test_windows_unsafe_chars(self):
        from utils import sanitize_filename
        result = sanitize_filename('file\\/:*?"<>|name')
        assert '\\' not in result
        assert '/' not in result
        assert ':' not in result
        assert '*' not in result
        assert '?' not in result
        assert '"' not in result
        assert '<' not in result
        assert '>' not in result
        assert '|' not in result

    def test_chinese_punctuation(self):
        from utils import sanitize_filename
        result = sanitize_filename('测试？！：、""《》【】（）文章')
        assert '？' not in result
        assert '！' not in result
        assert '：' not in result
        assert '、' not in result

    def test_length_limit(self):
        from utils import sanitize_filename
        long_title = "a" * 200
        result = sanitize_filename(long_title, max_length=80)
        assert len(result) <= 80

    def test_empty_title(self):
        from utils import sanitize_filename
        assert sanitize_filename("") == "untitled"
        assert sanitize_filename(None) == "untitled"

    def test_only_special_chars(self):
        from utils import sanitize_filename
        result = sanitize_filename('???')
        assert result == "untitled"

    def test_dots_and_spaces(self):
        from utils import sanitize_filename
        result = sanitize_filename('  ...测试...  ')
        assert not result.startswith('.')
        assert not result.endswith('.')
        assert not result.startswith(' ')

    def test_consecutive_underscores(self):
        from utils import sanitize_filename
        result = sanitize_filename('测试???文章')
        assert '___' not in result


class TestGetUniqueFilepath:
    """文件路径去重测试"""

    def test_new_file(self):
        from utils import get_unique_filepath
        with tempfile.TemporaryDirectory() as tmpdir:
            path = get_unique_filepath(tmpdir, "test", ".html")
            assert path == os.path.join(tmpdir, "test.html")

    def test_duplicate_file(self):
        from utils import get_unique_filepath
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建同名文件
            with open(os.path.join(tmpdir, "test.html"), "w") as f:
                f.write("existing")
            path = get_unique_filepath(tmpdir, "test", ".html")
            assert path == os.path.join(tmpdir, "test_2.html")

    def test_multiple_duplicates(self):
        from utils import get_unique_filepath
        with tempfile.TemporaryDirectory() as tmpdir:
            for name in ["test.html", "test_2.html", "test_3.html"]:
                with open(os.path.join(tmpdir, name), "w") as f:
                    f.write("existing")
            path = get_unique_filepath(tmpdir, "test", ".html")
            assert path == os.path.join(tmpdir, "test_4.html")


class TestGetOutputDir:
    """输出目录测试"""

    def test_creates_directory(self):
        from utils import get_output_dir
        with tempfile.TemporaryDirectory() as tmpdir:
            out_dir = get_output_dir(tmpdir)
            assert os.path.exists(out_dir)
            # 目录名包含日期
            from datetime import datetime
            date_str = datetime.now().strftime("%Y-%m-%d")
            assert date_str in out_dir


# ==================== logger.py 测试 ====================

class TestMaskApiKey:
    """API Key 脱敏测试"""

    def test_normal_key(self):
        from logger import mask_api_key
        result = mask_api_key("sk-abcdef1234")
        assert result == "****1234"

    def test_short_key(self):
        from logger import mask_api_key
        result = mask_api_key("ab")
        assert result == "****"

    def test_empty_key(self):
        from logger import mask_api_key
        result = mask_api_key("")
        assert result == "****"

    def test_none_key(self):
        from logger import mask_api_key
        result = mask_api_key(None)
        assert result == "****"


# ==================== wechat_style.py 测试 ====================

class TestWeChatStyle:
    """微信样式常量测试"""

    def test_default_theme_is_formal(self):
        import wechat_style
        # 默认主题应有绿色 #07c160
        assert "#07c160" in wechat_style.H2 or "#07c160" in wechat_style.BLOCKQUOTE

    def test_common_styles_exist(self):
        import wechat_style
        assert wechat_style.PARAGRAPH
        assert wechat_style.IMAGE_WRAPPER
        assert wechat_style.IMAGE
        assert wechat_style.LINK
        assert wechat_style.CODE_INLINE
        assert wechat_style.CODE_BLOCK
        assert wechat_style.BLOCKQUOTE
        assert wechat_style.H1
        assert wechat_style.H2
        assert wechat_style.H3

    def test_video_placeholder_styles_exist(self):
        import wechat_style
        assert wechat_style.VIDEO_PLACEHOLDER
        assert wechat_style.VIDEO_TEXT
        assert wechat_style.VIDEO_HINT


# ==================== crawler.py 测试（Mock HTTP） ====================

class TestCrawlerDataClasses:
    """爬虫数据类测试"""

    def test_article_data_defaults(self):
        from crawler import ArticleData
        article = ArticleData()
        assert article.title == ""
        assert article.images == []
        assert article.videos == []

    def test_image_data(self):
        from crawler import ImageData
        img = ImageData(url="https://example.com/1.jpg", alt="测试图片", index=1)
        assert img.url == "https://example.com/1.jpg"
        assert img.index == 1

    def test_video_data(self):
        from crawler import VideoData
        vid = VideoData(url="https://example.com/video.mp4", poster="https://example.com/poster.jpg", index=1)
        assert vid.url == "https://example.com/video.mp4"
        assert vid.poster == "https://example.com/poster.jpg"


class TestExtractImages:
    """图片提取测试"""

    def test_extract_images_from_html(self):
        from crawler import _extract_images
        html = '''
        <div>
            <img src="https://example.com/1.jpg" alt="图片1">
            <img src="https://example.com/2.png" alt="图片2">
        </div>
        '''
        images = _extract_images(html)
        assert len(images) == 2
        assert images[0].url == "https://example.com/1.jpg"
        assert images[0].alt == "图片1"
        assert images[1].index == 2

    def test_filter_small_images(self):
        from crawler import _extract_images
        html = '''
        <div>
            <img src="https://example.com/tracker.gif" width="1" height="1">
            <img src="https://example.com/real.jpg" alt="真实图片">
        </div>
        '''
        images = _extract_images(html)
        assert len(images) == 1
        assert images[0].url == "https://example.com/real.jpg"

    def test_filter_data_uri(self):
        from crawler import _extract_images
        html = '''
        <div>
            <img src="data:image/png;base64,abc123">
            <img src="https://example.com/real.jpg" alt="真实图片">
        </div>
        '''
        images = _extract_images(html)
        assert len(images) == 1

    def test_lazy_load_images(self):
        from crawler import _extract_images
        html = '''
        <div>
            <img data-src="https://example.com/lazy.jpg" alt="懒加载图片">
        </div>
        '''
        images = _extract_images(html)
        assert len(images) == 1
        assert images[0].url == "https://example.com/lazy.jpg"

    def test_no_src_skipped(self):
        from crawler import _extract_images
        html = '<div><img alt="无src图片"></div>'
        images = _extract_images(html)
        assert len(images) == 0


class TestExtractVideos:
    """视频提取测试"""

    def test_extract_video_tags(self):
        from crawler import _extract_videos
        html = '''
        <div>
            <video src="https://example.com/video1.mp4" poster="https://example.com/poster1.jpg"></video>
            <video><source src="https://example.com/video2.mp4"></video>
        </div>
        '''
        videos = _extract_videos(html)
        assert len(videos) == 2
        assert videos[0].url == "https://example.com/video1.mp4"
        assert videos[0].poster == "https://example.com/poster1.jpg"
        assert videos[1].url == "https://example.com/video2.mp4"

    def test_extract_iframe_videos(self):
        from crawler import _extract_videos
        html = '''
        <div>
            <iframe src="https://player.bilibili.com/player.html?bvid=xxx"></iframe>
        </div>
        '''
        videos = _extract_videos(html)
        assert len(videos) == 1
        assert "bilibili" in videos[0].url

    def test_non_video_iframe_ignored(self):
        from crawler import _extract_videos
        html = '''
        <div>
            <iframe src="https://example.com/ads.html"></iframe>
        </div>
        '''
        videos = _extract_videos(html)
        assert len(videos) == 0


class TestInsertMediaMarkers:
    """媒体标记插入测试"""

    def test_insert_image_markers(self):
        from crawler import _insert_media_markers, ImageData

        content_html = '<p>段落一</p><img src="https://example.com/1.jpg" alt="图1"/><p>段落二</p><img src="https://example.com/2.jpg" alt="图2"/><p>段落三</p>'
        content_text = "段落一\n\n段落二\n\n段落三"
        images = [
            ImageData(url="https://example.com/1.jpg", alt="图1", index=1),
            ImageData(url="https://example.com/2.jpg", alt="图2", index=2),
        ]
        result = _insert_media_markers(content_html, content_text, images, [])
        assert "[图片1]" in result
        assert "[图片2]" in result

    def test_insert_video_markers(self):
        from crawler import _insert_media_markers, VideoData

        content_html = '<p>段落一</p><video src="https://example.com/v1.mp4"></video><p>段落二</p>'
        content_text = "段落一\n\n段落二"
        videos = [VideoData(url="https://example.com/v1.mp4", index=1)]
        result = _insert_media_markers(content_html, content_text, [], videos)
        assert "[视频1]" in result

    def test_no_media_no_change(self):
        from crawler import _insert_media_markers

        content_html = "<p>只有文字</p>"
        content_text = "只有文字"
        result = _insert_media_markers(content_html, content_text, [], [])
        assert result == "只有文字"

    def test_empty_html_no_change(self):
        from crawler import _insert_media_markers, ImageData

        content_text = "只有文字没有HTML"
        images = [ImageData(url="https://example.com/1.jpg", alt="图1", index=1)]
        result = _insert_media_markers("", content_text, images, [])
        assert result == "只有文字没有HTML"


class TestCrawlWithMock:
    """使用 Mock HTTP 测试爬虫完整流程"""

    def test_crawl_success(self):
        from crawler import crawl

        mock_html = '''
        <html>
        <head><title>测试文章</title></head>
        <body>
            <article>
                <h1>测试文章标题</h1>
                <p>这是一段测试正文内容，用于验证爬虫功能是否正常工作。需要足够长的文字才能通过提取验证。</p>
                <img src="https://example.com/img1.jpg" alt="测试图">
            </article>
        </body>
        </html>
        '''

        with patch('crawler._fetch_html', return_value=mock_html):
            article = crawl("https://example.com/test")
            assert article.source_url == "https://example.com/test"
            assert len(article.content_text) > 0
            assert len(article.images) >= 1

    def test_crawl_http_error(self):
        import httpx
        from crawler import crawl

        with patch('crawler._fetch_html', side_effect=httpx.HTTPStatusError(
            "404", request=MagicMock(), response=MagicMock(status_code=404)
        )):
            with pytest.raises(httpx.HTTPStatusError):
                crawl("https://example.com/notfound")

    def test_crawl_empty_page(self):
        from crawler import crawl

        with patch('crawler._fetch_html', return_value="<html><body></body></html>"):
            with pytest.raises(ValueError, match="页面内容过短"):
                crawl("https://example.com/empty")


class TestReadLocalMarkdown:
    """本地 Markdown 文件读取测试"""

    def test_read_normal_md(self):
        from crawler import read_local_markdown

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
            f.write("# 测试文章标题\n\n这是正文内容，用于测试本地MD文件读取功能。\n\n第二段内容。")
            f.flush()
            filepath = f.name

        try:
            article = read_local_markdown(filepath)
            assert article.title == "测试文章标题"
            assert "正文内容" in article.content_text
            assert article.source_url.startswith("file://")
        finally:
            os.unlink(filepath)

    def test_read_md_with_images(self):
        from crawler import read_local_markdown

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
            f.write("# 图文文章\n\n正文内容。\n\n![图片1](https://example.com/1.jpg)\n\n![图片2](https://example.com/2.png)")
            f.flush()
            filepath = f.name

        try:
            article = read_local_markdown(filepath)
            assert article.title == "图文文章"
            assert len(article.images) == 2
            assert article.images[0].alt == "图片1"
            assert article.images[1].url == "https://example.com/2.png"
        finally:
            os.unlink(filepath)

    def test_read_md_no_heading(self):
        """没有 # 标题时，使用文件名作为标题"""
        from crawler import read_local_markdown

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8", prefix="我的文件_") as f:
            f.write("这是一篇没有标题的Markdown文件内容。")
            f.flush()
            filepath = f.name

        try:
            article = read_local_markdown(filepath)
            # 标题应该从文件名提取
            assert article.title != ""
            assert "没有标题" in article.content_text or "Markdown" in article.content_text
        finally:
            os.unlink(filepath)

    def test_read_md_not_found(self):
        from crawler import read_local_markdown

        with pytest.raises(FileNotFoundError):
            read_local_markdown("/nonexistent/path/article.md")

    def test_read_md_empty_file(self):
        from crawler import read_local_markdown

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
            f.write("")
            filepath = f.name

        try:
            with pytest.raises(ValueError, match="文件内容为空"):
                read_local_markdown(filepath)
        finally:
            os.unlink(filepath)

    def test_read_md_skip_data_uri_images(self):
        """data URI 图片应被跳过"""
        from crawler import read_local_markdown

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
            f.write("# 文章\n\n![icon](data:image/png;base64,abc123)\n\n![real](https://example.com/real.jpg)")
            filepath = f.name

        try:
            article = read_local_markdown(filepath)
            assert len(article.images) == 1
            assert article.images[0].alt == "real"
        finally:
            os.unlink(filepath)


# ==================== llm_processor.py 测试（Mock API） ====================

class TestBuildUserContent:
    """LLM 输入构建测试（OpenAI Chat Completions 格式）"""

    def test_text_only(self):
        from llm_processor import _build_user_content
        from crawler import ArticleData, ImageData

        article = ArticleData(
            title="测试文章",
            content_text="正文内容",
            images=[],
            videos=[],
        )
        content = _build_user_content(article, send_images=False)
        assert len(content) == 1
        assert content[0]["type"] == "text"
        assert "测试文章" in content[0]["text"]

    def test_with_images_send(self):
        from llm_processor import _build_user_content
        from crawler import ArticleData, ImageData

        article = ArticleData(
            title="测试文章",
            content_text="正文内容",
            images=[
                ImageData(url="https://example.com/1.jpg", alt="图1", index=1),
                ImageData(url="https://example.com/2.jpg", alt="图2", index=2),
            ],
        )
        content = _build_user_content(article, send_images=True)
        # 应有文本 + 2张图片 + 2个图片说明
        image_items = [c for c in content if c["type"] == "image_url"]
        assert len(image_items) == 2
        # 验证 image_url 格式
        assert "url" in image_items[0]["image_url"]
        assert image_items[0]["image_url"]["url"] == "https://example.com/1.jpg"

    def test_image_limit(self):
        from llm_processor import _build_user_content
        from crawler import ArticleData, ImageData

        # 模拟 5 张图片，但只发 3 张
        with patch('llm_processor.MAX_SEND_IMG_NUM', 3):
            article = ArticleData(
                title="测试",
                content_text="正文",
                images=[
                    ImageData(url=f"https://example.com/{i}.jpg", alt=f"图{i}", index=i)
                    for i in range(1, 6)
                ],
            )
            content = _build_user_content(article, send_images=True)
            image_items = [c for c in content if c["type"] == "image_url"]
            assert len(image_items) == 3
            # 检查说明文本
            text_items = [c for c in content if c["type"] == "text"]
            all_text = " ".join(t["text"] for t in text_items)
            assert "5 张图片" in all_text
            assert "前 3 张" in all_text


class TestBuildCreateKwargs:
    """chat.completions.create 参数构建测试"""

    def test_kwargs_structure(self):
        from llm_processor import _build_create_kwargs

        kwargs = _build_create_kwargs("test-model", [{"type": "text", "text": "hello"}])

        assert kwargs["model"] == "test-model"
        assert len(kwargs["messages"]) == 2
        assert kwargs["messages"][0]["role"] == "system"
        assert kwargs["messages"][1]["role"] == "user"
        assert kwargs["messages"][1]["content"] == [{"type": "text", "text": "hello"}]


class TestStripMarkdownWrapper:
    """Markdown 包裹去除测试"""

    def test_strip_markdown_prefix(self):
        from llm_processor import _strip_markdown_wrapper

        result = _strip_markdown_wrapper("```markdown\n# 标题\n\n正文\n```")
        assert not result.startswith("```")
        assert not result.endswith("```")
        assert "# 标题" in result

    def test_strip_code_prefix(self):
        from llm_processor import _strip_markdown_wrapper

        result = _strip_markdown_wrapper("```\n# 标题\n\n正文\n```")
        assert not result.startswith("```")
        assert not result.endswith("```")

    def test_no_wrapper(self):
        from llm_processor import _strip_markdown_wrapper

        result = _strip_markdown_wrapper("# 标题\n\n正文")
        assert result == "# 标题\n\n正文"

    def test_empty_string(self):
        from llm_processor import _strip_markdown_wrapper

        result = _strip_markdown_wrapper("")
        assert result == ""


class TestProcessWithMock:
    """使用 Mock OpenAI Client 测试 LLM 处理流程"""

    def _mock_response(self, content_text, prompt_tokens=100, completion_tokens=50, total_tokens=150):
        """构造 Mock OpenAI 响应"""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = content_text
        mock_response.usage = MagicMock()
        mock_response.usage.prompt_tokens = prompt_tokens
        mock_response.usage.completion_tokens = completion_tokens
        mock_response.usage.total_tokens = total_tokens
        return mock_response

    def test_process_sync_success(self):
        from llm_processor import process_sync
        from crawler import ArticleData

        mock_response = self._mock_response("# 优化后的标题\n\n> 摘要：测试\n\n优化后的正文")
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response

        with patch('llm_processor._get_sync_client', return_value=mock_client):
            article = ArticleData(title="测试", content_text="原始正文内容比较长")
            result = process_sync(article, send_images=False)
            assert "# 优化后的标题" in result

    def test_process_sync_retry_on_failure(self):
        from llm_processor import process_sync
        from crawler import ArticleData

        mock_response = self._mock_response("# 成功")
        call_count = 0

        def mock_create(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("API Error")
            return mock_response

        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = mock_create

        with patch('llm_processor._get_sync_client', return_value=mock_client):
            with patch('llm_processor.time.sleep'):
                article = ArticleData(title="测试", content_text="正文")
                result = process_sync(article, send_images=False)
                assert "# 成功" in result
                assert call_count == 2

    def test_process_sync_all_retries_failed(self):
        from llm_processor import process_sync
        from crawler import ArticleData

        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("API Error")

        with patch('llm_processor._get_sync_client', return_value=mock_client):
            with patch('llm_processor.time.sleep'):
                article = ArticleData(title="测试", content_text="正文")
                with pytest.raises(RuntimeError, match="LLM 调用失败"):
                    process_sync(article, send_images=False)

    def test_process_sync_strip_markdown_wrapper(self):
        """LLM 返回 ```markdown 包裹时应自动去除"""
        from llm_processor import process_sync
        from crawler import ArticleData

        mock_response = self._mock_response("```markdown\n# 标题\n\n正文\n```")
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response

        with patch('llm_processor._get_sync_client', return_value=mock_client):
            article = ArticleData(title="测试", content_text="正文")
            result = process_sync(article, send_images=False)
            assert not result.startswith("```")
            assert "# 标题" in result

    def test_process_sync_none_content(self):
        """LLM 返回 None content 时应返回空字符串"""
        from llm_processor import process_sync
        from crawler import ArticleData

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = None
        mock_response.usage = MagicMock()
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 0
        mock_response.usage.total_tokens = 10

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response

        with patch('llm_processor._get_sync_client', return_value=mock_client):
            article = ArticleData(title="测试", content_text="正文")
            result = process_sync(article, send_images=False)
            assert result == ""


# ==================== formatter.py 测试 ====================

class TestPreprocessMarkdown:
    """Markdown 预处理测试"""

    def test_replace_image_markers(self):
        from formatter import preprocess_markdown
        from crawler import ImageData

        md_text = "前面文字 [图片1] 后面文字 [图片2] 结束"
        images = [
            ImageData(url="https://example.com/1.jpg", alt="描述1", index=1),
            ImageData(url="https://example.com/2.jpg", alt="描述2", index=2),
        ]
        result = preprocess_markdown(md_text, images, [])
        assert "![描述1](https://example.com/1.jpg)" in result
        assert "![描述2](https://example.com/2.jpg)" in result
        assert "[图片1]" not in result
        assert "[图片2]" not in result

    def test_replace_video_markers(self):
        from formatter import preprocess_markdown
        from crawler import VideoData

        md_text = "前面文字 [视频1] 后面文字"
        videos = [VideoData(url="https://example.com/video.mp4", index=1)]
        result = preprocess_markdown(md_text, [], videos)
        assert "📹 视频位置" in result
        assert "https://example.com/video.mp4" in result
        assert "[视频1]" not in result

    def test_no_markers_unchanged(self):
        from formatter import preprocess_markdown
        md_text = "没有标记的普通文本"
        result = preprocess_markdown(md_text, [], [])
        assert result == md_text


class TestWeChatRenderer:
    """自定义渲染器测试"""

    def test_render_paragraph(self):
        import mistune
        from formatter import WeChatRenderer

        renderer = WeChatRenderer()
        md = mistune.create_markdown(renderer=renderer)
        result = md("普通段落")
        assert '<p style="' in result
        assert 'font-size:16px' in result

    def test_render_heading(self):
        import mistune
        from formatter import WeChatRenderer

        renderer = WeChatRenderer()
        md = mistune.create_markdown(renderer=renderer)
        result = md("# 大标题")
        assert '<h1 style="' in result
        assert 'font-size:24px' in result

    def test_render_h2(self):
        import mistune
        from formatter import WeChatRenderer

        renderer = WeChatRenderer()
        md = mistune.create_markdown(renderer=renderer)
        result = md("## 小标题")
        assert '<h2 style="' in result
        assert 'border-left' in result

    def test_render_blockquote(self):
        import mistune
        from formatter import WeChatRenderer

        renderer = WeChatRenderer()
        md = mistune.create_markdown(renderer=renderer)
        result = md("> 引用内容")
        assert '<blockquote style="' in result
        assert 'border-left' in result

    def test_render_image(self):
        import mistune
        from formatter import WeChatRenderer

        renderer = WeChatRenderer()
        md = mistune.create_markdown(renderer=renderer)
        result = md("![描述](https://example.com/1.jpg)")
        assert '<img src="https://example.com/1.jpg"' in result
        assert 'max-width:100%' in result

    def test_render_link(self):
        import mistune
        from formatter import WeChatRenderer

        renderer = WeChatRenderer()
        md = mistune.create_markdown(renderer=renderer)
        result = md("[链接](https://example.com)")
        assert '<a href="https://example.com"' in result
        assert '#07c160' in result

    def test_render_code_inline(self):
        import mistune
        from formatter import WeChatRenderer

        renderer = WeChatRenderer()
        md = mistune.create_markdown(renderer=renderer)
        result = md("文字 `代码` 文字")
        assert '<code style="' in result

    def test_render_strong(self):
        import mistune
        from formatter import WeChatRenderer

        renderer = WeChatRenderer()
        md = mistune.create_markdown(renderer=renderer)
        result = md("**加粗**")
        assert '<strong style="' in result

    def test_render_emphasis(self):
        import mistune
        from formatter import WeChatRenderer

        renderer = WeChatRenderer()
        md = mistune.create_markdown(renderer=renderer)
        result = md("*斜体*")
        assert '<em style="' in result

    def test_render_hr(self):
        import mistune
        from formatter import WeChatRenderer

        renderer = WeChatRenderer()
        md = mistune.create_markdown(renderer=renderer)
        result = md("---")
        assert '<hr style="' in result

    def test_render_list(self):
        import mistune
        from formatter import WeChatRenderer

        renderer = WeChatRenderer()
        md = mistune.create_markdown(renderer=renderer)
        result = md("- 列表1\n- 列表2")
        assert '<ul style="' in result
        assert '<li style="' in result

    def test_render_code_block(self):
        import mistune
        from formatter import WeChatRenderer

        renderer = WeChatRenderer()
        md = mistune.create_markdown(renderer=renderer)
        result = md("```python\nprint('hello')\n```")
        assert '<pre style="' in result


class TestFormatArticle:
    """格式化完整流程测试"""

    def test_format_article_basic(self):
        from formatter import format_article
        from crawler import ArticleData

        article = ArticleData(
            title="测试文章",
            content_text="正文",
            source_url="https://example.com/test",
        )
        md_text = "# 测试文章\n\n> 摘要：这是测试\n\n正文内容"
        html = format_article(md_text, article)

        assert "<!--" in html
        assert "WeChatArticleAutoGen" in html
        assert "https://example.com/test" in html
        assert '<section style="' in html
        assert '<h1 style="' in html
        assert "正文内容" in html

    def test_format_article_with_images(self):
        from formatter import format_article
        from crawler import ArticleData, ImageData

        article = ArticleData(
            title="图文文章",
            content_text="正文",
            images=[ImageData(url="https://example.com/1.jpg", alt="配图", index=1)],
            source_url="https://example.com/test",
        )
        md_text = "# 图文文章\n\n文字 [图片1] 更多文字"
        html = format_article(md_text, article)

        assert 'src="https://example.com/1.jpg"' in html
        assert "[图片1]" not in html

    def test_format_article_with_videos(self):
        from formatter import format_article
        from crawler import ArticleData, VideoData

        article = ArticleData(
            title="视频文章",
            content_text="正文",
            videos=[VideoData(url="https://example.com/video.mp4", index=1)],
            source_url="https://example.com/test",
        )
        md_text = "# 视频文章\n\n文字 [视频1] 更多文字"
        html = format_article(md_text, article)

        assert "📹 视频位置" in html
        assert "https://example.com/video.mp4" in html
        assert "[视频1]" not in html


# ==================== 端到端 Mock 测试 ====================

class TestEndToEndMock:
    """端到端 Mock 测试：爬虫 → LLM → 格式化"""

    def test_full_pipeline(self):
        """模拟完整流程"""
        from crawler import ArticleData, ImageData, VideoData
        from formatter import format_article

        # 1. 模拟爬虫输出
        article = ArticleData(
            title="AI 技术深度解读",
            author="张三",
            content_text="人工智能技术正在快速发展，深度学习、大语言模型等技术不断突破...",
            images=[
                ImageData(url="https://example.com/ai1.jpg", alt="AI架构图", index=1),
                ImageData(url="https://example.com/ai2.jpg", alt="模型对比", index=2),
            ],
            videos=[
                VideoData(url="https://example.com/interview.mp4", index=1),
            ],
            source_url="https://example.com/ai-article",
        )

        # 2. 模拟 LLM 输出
        mock_llm_output = "# AI 技术深度解读\n\n> 摘要：人工智能技术正在快速发展\n\n近年来，AI 技术不断突破。\n\n[图片1]\n\n深度学习是核心技术。\n\n[图片2]\n\n大语言模型改变了行业。\n\n[视频1]\n\n未来充满期待。"

        # 3. 格式化
        html = format_article(mock_llm_output, article)

        # 4. 验证
        assert '<h1 style="' in html
        assert 'AI 技术深度解读' in html
        assert 'src="https://example.com/ai1.jpg"' in html
        assert 'src="https://example.com/ai2.jpg"' in html
        assert "📹 视频位置" in html
        assert "https://example.com/interview.mp4" in html
        assert "WeChatArticleAutoGen" in html
        assert "<!--" in html

    def test_save_files(self):
        """测试文件保存"""
        from crawler import ArticleData
        from formatter import format_article
        from utils import get_output_dir, get_unique_filepath, sanitize_filename

        article = ArticleData(
            title="测试文章",
            content_text="正文",
            source_url="https://example.com/test",
        )
        md_text = "# 测试文章\n\n正文内容"
        html = format_article(md_text, article)

        with tempfile.TemporaryDirectory() as tmpdir:
            date_dir = get_output_dir(tmpdir)
            safe_title = sanitize_filename(article.title)
            html_path = get_unique_filepath(date_dir, safe_title, ".html")
            md_path = get_unique_filepath(date_dir, safe_title, ".md")

            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html)
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(md_text)

            assert os.path.exists(html_path)
            assert os.path.exists(md_path)

            with open(html_path, "r", encoding="utf-8") as f:
                content = f.read()
            assert "测试文章" in content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
