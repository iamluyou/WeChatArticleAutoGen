import os
from dotenv import load_dotenv

load_dotenv()

# LLM API 配置（兼容 OpenAI Chat Completions 协议）
# 豆包/ARK:   base_url=https://ark.cn-beijing.volces.com/api/v3
# DeepSeek:   base_url=https://api.deepseek.com
# OpenAI:     base_url=https://api.openai.com/v1
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3")
LLM_MODEL = os.getenv("LLM_MODEL", "doubao-seed-2-0-pro-260215")

# LLM 参数
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.7"))
LLM_TOP_P = float(os.getenv("LLM_TOP_P", "0.9"))

# 图片策略
MAX_SEND_IMG_NUM = int(os.getenv("MAX_SEND_IMG_NUM", "3"))

# 输出配置
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "result")
STYLE_THEME = os.getenv("STYLE_THEME", "formal")

# 并发配置
MAX_CONCURRENT = int(os.getenv("MAX_CONCURRENT", "3"))

# 爬虫配置
HTTP_PROXY = os.getenv("HTTP_PROXY", "")
CRAWL_TIMEOUT = float(os.getenv("CRAWL_TIMEOUT", "30.0"))
COOKIES = os.getenv("COOKIES", "{}")

# 图片校验
CHECK_IMAGE_URLS = os.getenv("CHECK_IMAGE_URLS", "false").lower() == "true"

# 重试策略
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
RETRY_DELAYS = [2, 4, 8]
