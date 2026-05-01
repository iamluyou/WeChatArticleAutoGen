"""
微信公众号文章自动生成工具 - 主入口
"""
import argparse
import asyncio
import os
import sys

from config import (
    LLM_MODEL,
    CHECK_IMAGE_URLS,
    CRAWL_TIMEOUT,
    HTTP_PROXY,
    MAX_SEND_IMG_NUM,
    OUTPUT_DIR,
    STYLE_THEME,
)
from crawler import crawl, read_local_markdown, ArticleData
from formatter import format_article
from logger import setup_logger
from llm_processor import process, process_sync
from utils import get_output_dir, get_unique_filepath, sanitize_filename

logger = setup_logger("main")


def load_urls_from_file(filepath: str) -> list:
    """从文件加载 URL 列表"""
    urls = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                urls.append(line)
    return urls


async def process_single_url(
    url: str,
    model: str = "",
    send_images: bool = True,
    max_images: int = 0,
    style: str = "",
    output: str = "",
    check_images: bool = False,
) -> tuple[bool, str]:
    """
    处理单个 URL：抓取 → LLM 优化 → 格式化 → 保存

    Returns:
        (success, message)
    """
    try:
        # 1. 爬虫抓取
        logger.info(f"开始处理: {url}")
        article = crawl(url, timeout=CRAWL_TIMEOUT, proxy=HTTP_PROXY)

        if not article.title:
            article.title = "untitled"
            logger.warning(f"文章无标题，使用默认标题: {url}")

        # 2. LLM 优化
        if max_images > 0:
            import config
            config.MAX_SEND_IMG_NUM = max_images

        if not send_images:
            import config
            config.MAX_SEND_IMG_NUM = 0

        md_text = await process(article, model=model, send_images=send_images)

        if not md_text:
            logger.error(f"LLM 输出为空: {url}")
            return False, f"LLM 输出为空: {url}"

        # 3. 格式化
        html = format_article(md_text, article)

        # 4. 保存文件
        out_dir = output or OUTPUT_DIR
        date_dir = get_output_dir(out_dir)
        safe_title = sanitize_filename(article.title)

        html_path = get_unique_filepath(date_dir, safe_title, ".html")
        md_path = get_unique_filepath(date_dir, safe_title, ".md")

        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)

        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_text)

        logger.info(f"文件保存成功: {html_path}")
        return True, html_path

    except Exception as e:
        logger.error(f"处理失败 [{url}]: {e}")
        return False, str(e)


async def process_local_md(
    filepath: str,
    model: str = "",
    send_images: bool = True,
    max_images: int = 0,
    style: str = "",
    output: str = "",
) -> tuple[bool, str]:
    """
    处理本地 Markdown 文件：读取 → LLM 优化 → 格式化 → 保存

    Returns:
        (success, message)
    """
    try:
        logger.info(f"开始处理本地文件: {filepath}")
        article = read_local_markdown(filepath)

        if not article.title:
            article.title = "untitled"
            logger.warning(f"文章无标题，使用默认标题: {filepath}")

        # LLM 优化
        if max_images > 0:
            import config
            config.MAX_SEND_IMG_NUM = max_images

        if not send_images:
            import config
            config.MAX_SEND_IMG_NUM = 0

        md_text = await process(article, model=model, send_images=send_images)

        if not md_text:
            logger.error(f"LLM 输出为空: {filepath}")
            return False, f"LLM 输出为空: {filepath}"

        # 格式化
        html = format_article(md_text, article)

        # 保存文件
        out_dir = output or OUTPUT_DIR
        date_dir = get_output_dir(out_dir)
        safe_title = sanitize_filename(article.title)

        html_path = get_unique_filepath(date_dir, safe_title, ".html")
        md_path = get_unique_filepath(date_dir, safe_title, ".md")

        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)

        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_text)

        logger.info(f"文件保存成功: {html_path}")
        return True, html_path

    except Exception as e:
        logger.error(f"处理失败 [{filepath}]: {e}")
        return False, str(e)


async def process_urls(
    urls: list,
    model: str = "",
    send_images: bool = True,
    max_images: int = 0,
    style: str = "",
    output: str = "",
    check_images: bool = False,
    max_concurrent: int = 3,
):
    """批量处理 URL，控制并发"""
    from config import MAX_CONCURRENT
    max_concurrent = max_concurrent or MAX_CONCURRENT
    semaphore = asyncio.Semaphore(max_concurrent)

    results = []

    async def process_with_semaphore(url: str):
        async with semaphore:
            success, msg = await process_single_url(
                url, model=model, send_images=send_images,
                max_images=max_images, style=style,
                output=output, check_images=check_images,
            )
            results.append((url, success, msg))

    tasks = [process_with_semaphore(url) for url in urls]
    await asyncio.gather(*tasks, return_exceptions=True)

    # 输出汇总
    print("\n" + "=" * 60)
    print("处理结果汇总")
    print("=" * 60)
    success_count = 0
    for url, success, msg in results:
        status = "✅ 成功" if success else "❌ 失败"
        print(f"{status} | {url}")
        if success:
            success_count += 1
            print(f"       → {msg}")
        else:
            print(f"       → 错误: {msg}")
    print(f"\n总计: {len(results)} 篇，成功: {success_count} 篇，失败: {len(results) - success_count} 篇")


def main():
    parser = argparse.ArgumentParser(description="微信公众号文章自动生成工具")
    parser.add_argument("--url", help="目标文章 URL")
    parser.add_argument("--md", help="本地 Markdown 文件路径")
    parser.add_argument("--file", help="批量 URL 列表文件路径")
    parser.add_argument("--model", default="", help="LLM 模型名称")
    parser.add_argument("--no-images", action="store_true", help="不发送图片给 LLM")
    parser.add_argument("--max-images", type=int, default=0, help="发送给 LLM 的最大图片数量")
    parser.add_argument("--style", choices=["formal", "light", "tech"], default="", help="排版风格")
    parser.add_argument("--output", default="", help="输出目录")
    parser.add_argument("--check-images", action="store_true", help="校验图片 URL 有效性")

    args = parser.parse_args()

    # 设置风格
    if args.style:
        import wechat_style
        wechat_style.STYLE_THEME = args.style

    send_images = not args.no_images

    # 处理本地 Markdown 文件
    if args.md:
        success, msg = asyncio.run(process_local_md(
            args.md,
            model=args.model,
            send_images=send_images,
            max_images=args.max_images,
            style=args.style,
            output=args.output,
        ))
        if success:
            print(f"\n✅ 生成成功: {msg}")
        else:
            print(f"\n❌ 生成失败: {msg}")
            sys.exit(1)
        return

    # 收集 URL
    urls = []
    if args.url:
        urls.append(args.url)
    if args.file:
        urls.extend(load_urls_from_file(args.file))

    if not urls:
        parser.print_help()
        print("\n错误: 请提供 --url、--md 或 --file 参数")
        sys.exit(1)

    if len(urls) == 1:
        success, msg = asyncio.run(process_single_url(
            urls[0],
            model=args.model,
            send_images=send_images,
            max_images=args.max_images,
            style=args.style,
            output=args.output,
            check_images=args.check_images,
        ))
        if success:
            print(f"\n✅ 生成成功: {msg}")
        else:
            print(f"\n❌ 生成失败: {msg}")
            sys.exit(1)
    else:
        asyncio.run(process_urls(
            urls,
            model=args.model,
            send_images=send_images,
            max_images=args.max_images,
            style=args.style,
            output=args.output,
            check_images=args.check_images,
        ))


if __name__ == "__main__":
    main()
