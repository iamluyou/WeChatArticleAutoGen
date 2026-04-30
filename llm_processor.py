"""
LLM 处理模块：httpx 直调 ARK Responses API，限量图文理解
"""
import time

import httpx

from config import (
    ARK_API_KEY,
    ARK_BASE_URL,
    ARK_MODEL,
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


def _build_input_content(article: ArticleData, send_images: bool = True) -> list:
    """
    构建 LLM 输入内容（多模态格式）

    正文 content_text 中已包含 [图片N]/[视频N] 位置标记（由爬虫插入），
    此处不再额外追加标记，而是将前 N 张图片以多模态方式发送给 LLM。

    Args:
        article: 文章数据
        send_images: 是否发送图片给 LLM

    Returns:
        content 数组
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

        content.append({"type": "input_text", "text": full_text})

        # 插入图片（多模态）
        for img in images_to_send:
            content.append({
                "type": "input_image",
                "image_url": img.url,
            })
            content.append({
                "type": "input_text",
                "text": f"↑ 以上为 [图片{img.index}] {img.alt}".strip(),
            })
    else:
        content.append({"type": "input_text", "text": full_text})

    return content


def _build_payload(article: ArticleData, model: str = "", send_images: bool = True) -> dict:
    """构建 ARK Responses API 请求 payload"""
    model = model or ARK_MODEL

    input_content = _build_input_content(article, send_images)

    payload = {
        "model": model,
        "input": [
            {
                "role": "system",
                "content": [{"type": "input_text", "text": SYSTEM_PROMPT}],
            },
            {
                "role": "user",
                "content": input_content,
            },
        ],
    }

    # 可选参数
    if LLM_TEMPERATURE != 0.7:
        payload["temperature"] = LLM_TEMPERATURE
    if LLM_TOP_P != 0.9:
        payload["top_p"] = LLM_TOP_P

    return payload


def _parse_response(response_data: dict) -> str:
    """
    解析 ARK Responses API 响应，提取文本内容

    兼容多种可能的响应格式：
    - Responses API: { "output": [ { "type": "message", "content": [ { "type": "output_text", "text": "..." } ] } ] }
    - Chat Completions: { "choices": [ { "message": { "content": "..." } } ] }

    Returns:
        LLM 输出的 Markdown 文本
    """
    texts = []

    # 方式1：Responses API 格式 - output 数组
    output = response_data.get("output", [])
    if output:
        for item in output:
            # output 中的 item 可能是 message 类型
            if item.get("type") == "message":
                for content_item in item.get("content", []):
                    # 兼容多种 type 命名：output_text / input_text / text
                    if content_item.get("type") in ("output_text", "input_text", "text"):
                        texts.append(content_item.get("text", ""))
            # output 中的 item 可能直接是 content 类型
            elif item.get("type") in ("output_text", "input_text", "text"):
                texts.append(item.get("text", ""))

    # 方式2：Chat Completions 格式 - choices 数组
    choices = response_data.get("choices", [])
    if not texts and choices:
        for choice in choices:
            msg = choice.get("message", {})
            content = msg.get("content", "")
            if content:
                texts.append(content)

    # 方式3：直接有 content 字段（兜底）
    if not texts:
        content = response_data.get("content", "")
        if content:
            texts.append(content)

    result = "\n".join(texts).strip()

    # 调试：如果解析为空，记录原始响应结构
    if not result:
        logger.warning(
            f"LLM 响应解析为空，原始响应结构: "
            f"keys={list(response_data.keys())}, "
            f"output_len={len(output)}, "
            f"output_types={[item.get('type') for item in output] if output else []}"
        )
        # 尝试遍历 output 的第一个元素看详细结构
        if output and len(output) > 0:
            first = output[0]
            logger.warning(f"output[0] keys={list(first.keys())}, type={first.get('type')}")
            if first.get("content"):
                logger.warning(
                    f"output[0].content types={[c.get('type') for c in first['content']]}"
                )

    # 去除可能的 ```markdown 包裹
    if result.startswith("```markdown"):
        result = result[len("```markdown"):]
    if result.startswith("```"):
        result = result[len("```"):]
    if result.endswith("```"):
        result = result[:-len("```")]
    result = result.strip()

    return result


async def call_ark_api(payload: dict) -> dict:
    """
    直接调用 ARK Responses API

    Args:
        payload: 请求 payload

    Returns:
        API 响应 dict
    """
    url = f"{ARK_BASE_URL}/responses"
    headers = {
        "Authorization": f"Bearer {ARK_API_KEY}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()


def call_ark_api_sync(payload: dict) -> dict:
    """同步版本：调用 ARK Responses API"""
    url = f"{ARK_BASE_URL}/responses"
    headers = {
        "Authorization": f"Bearer {ARK_API_KEY}",
        "Content-Type": "application/json",
    }

    with httpx.Client(timeout=120.0) as client:
        response = client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()


async def process(article: ArticleData, model: str = "", send_images: bool = True) -> str:
    """
    调用 LLM 优化文章内容（异步）

    Args:
        article: 爬虫抓取的文章数据
        model: 可选模型名称
        send_images: 是否发送图片给 LLM

    Returns:
        优化后的 Markdown 文本
    """
    payload = _build_payload(article, model=model, send_images=send_images)
    logger.info(f"LLM 请求构建完成，模型: {model or ARK_MODEL}, API Key: {mask_api_key(ARK_API_KEY)}")

    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            start_time = time.time()
            response_data = await call_ark_api(payload)
            elapsed = time.time() - start_time

            # 记录 Token 用量
            usage = response_data.get("usage", {})
            logger.info(
                f"LLM 调用成功 - 耗时: {elapsed:.2f}s, "
                f"input_tokens: {usage.get('input_tokens', 'N/A')}, "
                f"output_tokens: {usage.get('output_tokens', 'N/A')}, "
                f"total_tokens: {usage.get('total_tokens', 'N/A')}"
            )

            return _parse_response(response_data)

        except Exception as e:
            last_error = e
            if attempt < MAX_RETRIES - 1:
                delay = RETRY_DELAYS[attempt] if attempt < len(RETRY_DELAYS) else 8
                logger.warning(f"LLM 调用失败（第 {attempt + 1} 次），{delay}s 后重试: {e}")
                time.sleep(delay)
            else:
                logger.error(f"LLM 调用失败，已重试 {MAX_RETRIES} 次: {e}")

    raise RuntimeError(f"LLM 调用失败，已重试 {MAX_RETRIES} 次: {last_error}")


def process_sync(article: ArticleData, model: str = "", send_images: bool = True) -> str:
    """
    调用 LLM 优化文章内容（同步）

    Args:
        article: 爬虫抓取的文章数据
        model: 可选模型名称
        send_images: 是否发送图片给 LLM

    Returns:
        优化后的 Markdown 文本
    """
    payload = _build_payload(article, model=model, send_images=send_images)
    logger.info(f"LLM 请求构建完成，模型: {model or ARK_MODEL}, API Key: {mask_api_key(ARK_API_KEY)}")

    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            start_time = time.time()
            response_data = call_ark_api_sync(payload)
            elapsed = time.time() - start_time

            usage = response_data.get("usage", {})
            logger.info(
                f"LLM 调用成功 - 耗时: {elapsed:.2f}s, "
                f"input_tokens: {usage.get('input_tokens', 'N/A')}, "
                f"output_tokens: {usage.get('output_tokens', 'N/A')}, "
                f"total_tokens: {usage.get('total_tokens', 'N/A')}"
            )

            return _parse_response(response_data)

        except Exception as e:
            last_error = e
            if attempt < MAX_RETRIES - 1:
                delay = RETRY_DELAYS[attempt] if attempt < len(RETRY_DELAYS) else 8
                logger.warning(f"LLM 调用失败（第 {attempt + 1} 次），{delay}s 后重试: {e}")
                time.sleep(delay)
            else:
                logger.error(f"LLM 调用失败，已重试 {MAX_RETRIES} 次: {e}")

    raise RuntimeError(f"LLM 调用失败，已重试 {MAX_RETRIES} 次: {last_error}")
