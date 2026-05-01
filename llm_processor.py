"""
LLM 处理模块：基于 OpenAI 兼容协议，支持任意兼容 Chat Completions 的 API 服务

支持的服务商：
- 豆包/ARK:   base_url=https://ark.cn-beijing.volces.com/api/v3
- DeepSeek:   base_url=https://api.deepseek.com
- OpenAI:     base_url=https://api.openai.com/v1
- 其他兼容 OpenAI Chat Completions 协议的 API 服务
"""
import asyncio
import time

from openai import OpenAI, AsyncOpenAI

from config import (
    LLM_API_KEY,
    LLM_BASE_URL,
    LLM_MODEL,
    LLM_TEMPERATURE,
    LLM_TOP_P,
    MAX_RETRIES,
    MAX_SEND_IMG_NUM,
    RETRY_DELAYS,
)
from crawler import ArticleData
from logger import mask_api_key, setup_logger

logger = setup_logger("llm")

SYSTEM_PROMPT = """你现在是一个有10年经验、文字功底很好的资深程序员，同时也是公众号作者。

任务：对文章进行高质量润色和优化，使其适合微信公众号阅读，同时确保内容准确、逻辑严密。

一、去AI味 & 内容润色
1. 大幅去除AI味，让语言自然、真实、有温度，像一个老程序员在认真分享经验
2. 语气可以稍带锋芒和真实感，避免过于温和或模板化的表达，但也不要刻薄
3. 优化逻辑流畅度和阅读节奏，长短句结合，段落不要太长（每段不超过5行）
4. 保留所有核心事实和观点，不要删减重要信息
5. 小标题要更抓眼球且自然，不要那种四平八稳的官方标题
6. 整体要简洁有力，口语化但不低俗
7. 统一术语和表述风格，保持全文一致性
8. 消除冗余描述和重复内容，但不牺牲信息密度

二、逻辑检查与事实核查
9. 检查文章是否存在逻辑漏洞：因果倒置、以偏概全、偷换概念、循环论证等
10. 检查关键数据、引用、时间节点是否自洽，前后矛盾之处须修正
11. 检查论点是否有充分论据支撑，无支撑的断言须补充说明或标注存疑
12. 如发现原文存在明显事实错误或逻辑问题，在对应段落后用引用块标注：
    > ⚠️ 编辑注：原文此处存在XXX问题，已做XXX调整

三、结构优化
13. 在文章开头添加摘要（80字以内），格式为 > 摘要：xxx
14. 保留原文核心观点，不添加虚构内容
15. 在图片对应位置用 [图片N] 标记保留图片位置
16. 在视频对应位置用 [视频N] 标记保留视频位置
17. 如有图片描述信息，为图片撰写简短 alt 描述

输出要求：
- 必须输出纯 Markdown，不要用 ```markdown 包裹
- 一级标题为文章标题
- 摘要使用引用块格式
- 不要输出 HTML 标签
- 不要输出任何额外说明文字，只输出优化后的文章"""


def _get_sync_client() -> OpenAI:
    """获取同步 OpenAI 客户端"""
    return OpenAI(base_url=LLM_BASE_URL, api_key=LLM_API_KEY)


def _get_async_client() -> AsyncOpenAI:
    """获取异步 OpenAI 客户端"""
    return AsyncOpenAI(base_url=LLM_BASE_URL, api_key=LLM_API_KEY)


def _build_user_content(article: ArticleData, send_images: bool = True) -> list:
    """
    构建 user message 的 content（OpenAI Chat Completions 多模态格式）

    正文 content_text 中已包含 [图片N]/[视频N] 位置标记（由爬虫插入），
    此处将前 N 张图片以多模态方式发送给 LLM，帮助 LLM 理解图片内容。

    Args:
        article: 文章数据
        send_images: 是否发送图片给 LLM

    Returns:
        content 数组，元素为 OpenAI Chat Completions 格式的 dict
    """
    content = []

    # 文章标题和正文（正文已包含 [图片N]/[视频N] 标记）
    full_text = f"请按系统指令要求润色以下文章：\n\n# {article.title}\n\n{article.content_text}"

    if send_images and article.images:
        images_to_send = article.images[:MAX_SEND_IMG_NUM]
        # 在文本末尾附注图片说明
        img_info = f"\n\n---\n文中包含 {len(article.images)} 张图片"
        if len(article.images) > MAX_SEND_IMG_NUM:
            img_info += f"，以下发送前 {MAX_SEND_IMG_NUM} 张供参考："
        else:
            img_info += "："
        full_text += img_info

        content.append({"type": "text", "text": full_text})

        # 插入图片（多模态）
        for img in images_to_send:
            content.append({
                "type": "image_url",
                "image_url": {"url": img.url},
            })
            content.append({
                "type": "text",
                "text": f"↑ 以上为 [图片{img.index}] {img.alt}".strip(),
            })
    else:
        content.append({"type": "text", "text": full_text})

    return content


def _strip_markdown_wrapper(text: str) -> str:
    """去除可能的 ```markdown 包裹"""
    if text.startswith("```markdown"):
        text = text[len("```markdown"):]
    if text.startswith("```"):
        text = text[len("```"):]
    if text.endswith("```"):
        text = text[:-len("```")]
    return text.strip()


def _build_create_kwargs(model: str, user_content: list) -> dict:
    """构建 chat.completions.create 调用参数"""
    kwargs = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
    }
    if LLM_TEMPERATURE != 0.7:
        kwargs["temperature"] = LLM_TEMPERATURE
    if LLM_TOP_P != 0.9:
        kwargs["top_p"] = LLM_TOP_P
    return kwargs


async def process(article: ArticleData, model: str = "", send_images: bool = True) -> str:
    """
    调用 LLM 优化文章内容（异步）

    使用 OpenAI Chat Completions 兼容协议，支持任意兼容 OpenAI 协议的 API 服务。

    Args:
        article: 爬虫抓取的文章数据
        model: 可选模型名称（覆盖默认配置）
        send_images: 是否发送图片给 LLM

    Returns:
        优化后的 Markdown 文本
    """
    model = model or LLM_MODEL
    user_content = _build_user_content(article, send_images)
    logger.info(f"LLM 请求构建完成，模型: {model}, API Key: {mask_api_key(LLM_API_KEY)}")

    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            start_time = time.time()
            client = _get_async_client()

            kwargs = _build_create_kwargs(model, user_content)
            response = await client.chat.completions.create(**kwargs)
            elapsed = time.time() - start_time

            result = response.choices[0].message.content or ""
            result = _strip_markdown_wrapper(result)

            usage = response.usage
            if usage:
                logger.info(
                    f"LLM 调用成功 - 耗时: {elapsed:.2f}s, "
                    f"input_tokens: {usage.prompt_tokens}, "
                    f"output_tokens: {usage.completion_tokens}, "
                    f"total_tokens: {usage.total_tokens}"
                )
            else:
                logger.info(f"LLM 调用成功 - 耗时: {elapsed:.2f}s")

            return result

        except Exception as e:
            last_error = e
            if attempt < MAX_RETRIES - 1:
                delay = RETRY_DELAYS[attempt] if attempt < len(RETRY_DELAYS) else 8
                logger.warning(f"LLM 调用失败（第 {attempt + 1} 次），{delay}s 后重试: {e}")
                await asyncio.sleep(delay)
            else:
                logger.error(f"LLM 调用失败，已重试 {MAX_RETRIES} 次: {e}")

    raise RuntimeError(f"LLM 调用失败，已重试 {MAX_RETRIES} 次: {last_error}")


def process_sync(article: ArticleData, model: str = "", send_images: bool = True) -> str:
    """
    调用 LLM 优化文章内容（同步）

    Args:
        article: 爬虫抓取的文章数据
        model: 可选模型名称（覆盖默认配置）
        send_images: 是否发送图片给 LLM

    Returns:
        优化后的 Markdown 文本
    """
    model = model or LLM_MODEL
    user_content = _build_user_content(article, send_images)
    logger.info(f"LLM 请求构建完成，模型: {model}, API Key: {mask_api_key(LLM_API_KEY)}")

    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            start_time = time.time()
            client = _get_sync_client()

            kwargs = _build_create_kwargs(model, user_content)
            response = client.chat.completions.create(**kwargs)
            elapsed = time.time() - start_time

            result = response.choices[0].message.content or ""
            result = _strip_markdown_wrapper(result)

            usage = response.usage
            if usage:
                logger.info(
                    f"LLM 调用成功 - 耗时: {elapsed:.2f}s, "
                    f"input_tokens: {usage.prompt_tokens}, "
                    f"output_tokens: {usage.completion_tokens}, "
                    f"total_tokens: {usage.total_tokens}"
                )
            else:
                logger.info(f"LLM 调用成功 - 耗时: {elapsed:.2f}s")

            return result

        except Exception as e:
            last_error = e
            if attempt < MAX_RETRIES - 1:
                delay = RETRY_DELAYS[attempt] if attempt < len(RETRY_DELAYS) else 8
                logger.warning(f"LLM 调用失败（第 {attempt + 1} 次），{delay}s 后重试: {e}")
                time.sleep(delay)
            else:
                logger.error(f"LLM 调用失败，已重试 {MAX_RETRIES} 次: {e}")

    raise RuntimeError(f"LLM 调用失败，已重试 {MAX_RETRIES} 次: {last_error}")
