# WeChatArticleAutoGen

微信公众号文章自动生成工具 —— 抓取指定 URL 内容或读取本地 Markdown 文件，调用大模型润色优化，输出微信公众号编辑器可直接粘贴的 HTML 文件。

## 核心流程

```
URL 输入 / 本地 Markdown → 爬虫抓取或文件读取 → LLM 润色+逻辑检查 → 微信 HTML 输出
```

## 功能特性

- **双输入源**：支持 URL 爬虫抓取和本地 Markdown 文件读取
- **多级正文提取**：trafilatura → readability → newspaper → BeautifulSoup 四级回退，覆盖新闻、博客、自媒体等各类站点
- **反爬策略**：UA 伪装、随机间隔、Cookie 携带、代理支持
- **OpenAI 兼容协议**：基于 OpenAI Chat Completions 协议，一键切换豆包/DeepSeek/OpenAI 等任意兼容模型
- **多模态 LLM**：支持图文理解，图片限量控制（默认前 5 张）
- **去AI味润色**：10年经验程序员人设，语气自然有锋芒，小标题抓眼球
- **逻辑检查 + 事实核查**：LLM 不仅润色文字，还会检查逻辑漏洞、事实错误，发现问题时用编辑注标注
- **自定义渲染器**：基于 mistune 的微信内联样式渲染器，一步到位输出，无需后处理
- **三套排版风格**：formal（正式）/ light（轻快）/ tech（科技），CLI 一键切换
- **批量处理**：支持 URL 列表文件导入，asyncio + Semaphore 并发控制
- **完善日志**：全流程记录，Token 用量统计，API Key 脱敏

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置 API Key

```bash
cp .env .env.local
# 编辑 .env.local，填入你的 API Key 和 base_url
```

或直接设置环境变量：

```bash
# 豆包/ARK
export LLM_API_KEY="your-ark-api-key"
export LLM_BASE_URL="https://ark.cn-beijing.volces.com/api/v3"
export LLM_MODEL="doubao-seed-2-0-pro-260215"

# DeepSeek
export LLM_API_KEY="your-deepseek-api-key"
export LLM_BASE_URL="https://api.deepseek.com"
export LLM_MODEL="deepseek-chat"

# OpenAI
export LLM_API_KEY="your-openai-api-key"
export LLM_BASE_URL="https://api.openai.com/v1"
export LLM_MODEL="gpt-4o"
```

### 3. 运行

```bash
# 单 URL 生成
python main.py --url "https://example.com/article"

# 本地 Markdown 文件
python main.py --md /path/to/article.md

# 批量 URL（从文件读取）
python main.py --file urls.txt

# 不发送图片给 LLM（节省 Token）
python main.py --url "https://example.com/article" --no-images

# 自定义传图数量
python main.py --url "https://example.com/article" --max-images 5

# 切换排版风格
python main.py --url "https://example.com/article" --style light

# 切换模型
python main.py --url "https://example.com/article" --model "deepseek-chat"
```

### 4. 查看输出

文件保存至 `result/{日期}/{文章标题}.html`，用浏览器打开后：

1. 全选复制（Ctrl+A → Ctrl+C）
2. 在微信公众号后台编辑器中粘贴（Ctrl+V）
3. 手动替换视频占位符

## 输入源说明

### URL 模式（`--url` / `--file`）

抓取网页内容，自动提取正文、标题、作者、图片和视频。四级提取器回退确保覆盖率。

### 本地 Markdown 模式（`--md`）

直接读取本地 `.md` 文件，跳过爬虫环节，进入 LLM 优化流程。适合：

- 已有 Markdown 草稿，需要 LLM 润色优化
- 从其他工具导出的 Markdown 文件
- 不方便爬取的付费/登录页面内容

功能特点：
- 自动从 `# 标题` 行提取文章标题，无标题时使用文件名
- 自动提取 Markdown 中的图片（`![alt](url)` 格式）
- 跳过 data URI 图片（base64 内嵌图片）

## 批量 URL 文件格式

`urls.txt` 每行一个 URL，`#` 开头为注释：

```
# 科技类
https://example.com/article1
https://example.com/article2

# 财经类
https://example.com/article3
```

## 项目结构

```
├── main.py              # 主入口，CLI 交互
├── config.py            # 配置文件（环境变量管理）
├── crawler.py           # 爬虫模块（多级提取 + 图片/视频收集 + 本地 MD 读取）
├── llm_processor.py     # LLM 模块（OpenAI 兼容协议，内容润色+逻辑检查）
├── formatter.py         # 格式化模块（自定义 mistune 渲染器）
├── wechat_style.py      # 微信内联样式常量（三套风格）
├── logger.py            # 日志模块
├── utils.py             # 工具函数（文件名清理等）
├── example_payload.json # OpenAI Chat Completions 请求示例
├── .env                 # 环境变量模板
├── .gitignore
├── requirements.txt
├── tests/
│   └── test_all.py      # 单元测试 + Mock 测试
└── 方案文档.md           # 完整技术方案
```

## 配置项

| 环境变量 | 默认值 | 说明 |
|---------|--------|------|
| `LLM_API_KEY` | 无（必填） | LLM API Key |
| `LLM_BASE_URL` | `https://ark.cn-beijing.volces.com/api/v3` | API 基础地址（兼容 OpenAI 协议即可） |
| `LLM_MODEL` | `doubao-seed-2-0-pro-260215` | 默认模型 |
| `LLM_TEMPERATURE` | `0.7` | LLM 温度参数 |
| `LLM_TOP_P` | `0.9` | LLM top_p 参数 |
| `MAX_SEND_IMG_NUM` | `3` | 发送给 LLM 的最大图片数量 |
| `OUTPUT_DIR` | `result` | 输出根目录 |
| `STYLE_THEME` | `formal` | 排版风格：formal / light / tech |
| `MAX_CONCURRENT` | `3` | 批量处理最大并发数 |
| `HTTP_PROXY` | 无 | HTTP 代理地址 |
| `CRAWL_TIMEOUT` | `30.0` | 爬虫超时时间（秒） |
| `CHECK_IMAGE_URLS` | `false` | 是否校验图片 URL 有效性 |

## 运行测试

```bash
python -m pytest tests/ -v
```

## 注意事项

- 微信公众号编辑器**不支持外部 CSS**，所有样式均为内联
- 图片粘贴后微信会**自动转存**到 CDN
- 视频需**手动上传**，工具仅输出占位符和原始链接
- 本项目基于 **OpenAI Chat Completions 兼容协议**，支持豆包/ARK、DeepSeek、OpenAI 等任意兼容模型
- 首次使用前请确认 API Key 有效，建议先用 `example_payload.json` 做一次真实调用验证
- LLM 会自动检查原文逻辑漏洞和事实错误，发现问题时会在文中插入 `⚠️ 编辑注` 标注

## License

MIT
