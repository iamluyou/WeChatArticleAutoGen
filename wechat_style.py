"""
微信公众号内联样式常量
通过 STYLE_THEME 环境变量切换风格：formal / light / tech
"""
import os

STYLE_THEME = os.getenv("STYLE_THEME", "formal")

# ==================== 通用样式（所有主题共享） ====================
PARAGRAPH = "font-size:16px;color:#333;line-height:1.8;margin:15px 0;text-align:justify;"
IMAGE_WRAPPER = "text-align:center;margin:15px 0;"
IMAGE = "max-width:100%;height:auto;border-radius:4px;"
LINK = "color:#07c160;text-decoration:none;border-bottom:1px solid #07c160;"
CODE_INLINE = "background-color:#f0f0f0;color:#e83e8c;padding:2px 4px;border-radius:3px;font-size:14px;"
CODE_BLOCK = "background-color:#f6f8fa;border-radius:4px;padding:16px;overflow-x:auto;font-size:14px;line-height:1.6;"
LIST = "margin:15px 0;padding-left:2em;"
LIST_ITEM = "margin:5px 0;font-size:16px;color:#333;line-height:1.8;"
EMPHASIS = "color:#333;"
STRONG = "color:#1a1a1a;"
HR = "border:none;border-top:1px solid #eee;margin:25px 0;"
TABLE = "width:100%;border-collapse:collapse;margin:15px 0;font-size:14px;"
TABLE_HEAD = "background-color:#f6f8fa;font-weight:bold;"
TABLE_CELL = "border:1px solid #ddd;padding:8px 12px;text-align:left;"

# 视频占位符样式
VIDEO_PLACEHOLDER = (
    "text-align:center;margin:15px 0;padding:30px;"
    "background-color:#f0f0f0;border-radius:8px;border:1px dashed #ccc;"
)
VIDEO_TEXT = "font-size:16px;color:#666;"
VIDEO_HINT = "font-size:12px;color:#999;"

# 外层包裹
SECTION_WRAPPER = "max-width:100%;margin:0 auto;padding:0 10px;"

# ==================== 主题差异化样式 ====================

if STYLE_THEME == "formal":
    # 正式风格：绿色边框 + 灰色背景
    H1 = "font-size:24px;font-weight:bold;color:#1a1a1a;text-align:center;margin:20px 0 10px;line-height:1.4;"
    H2 = "font-size:20px;font-weight:bold;color:#1a1a1a;margin:25px 0 10px;padding-left:10px;border-left:4px solid #07c160;"
    H3 = "font-size:18px;font-weight:bold;color:#1a1a1a;margin:20px 0 10px;"
    HEADING_DEFAULT = "font-size:17px;font-weight:bold;color:#1a1a1a;margin:15px 0 8px;"
    BLOCKQUOTE = "margin:15px 0;padding:10px 15px;border-left:3px solid #07c160;background-color:#f7f7f7;color:#666;font-size:14px;"

elif STYLE_THEME == "light":
    # 轻快风格：圆角背景 + 暖色调
    H1 = "font-size:24px;font-weight:bold;color:#ff6b6b;text-align:center;margin:20px 0 10px;line-height:1.4;"
    H2 = "font-size:20px;font-weight:bold;color:#ff6b6b;margin:25px 0 10px;padding:4px 12px;background-color:#fff0f0;border-radius:4px;display:inline-block;"
    H3 = "font-size:18px;font-weight:bold;color:#e55555;margin:20px 0 10px;"
    HEADING_DEFAULT = "font-size:17px;font-weight:bold;color:#e55555;margin:15px 0 8px;"
    BLOCKQUOTE = "margin:15px 0;padding:10px 15px;border-left:3px solid #ffb347;background-color:#fffbf0;color:#8b6914;font-size:14px;"

elif STYLE_THEME == "tech":
    # 科技风格：蓝色调 + 极简
    H1 = "font-size:24px;font-weight:bold;color:#1a1a2e;text-align:center;margin:20px 0 10px;line-height:1.4;letter-spacing:1px;"
    H2 = "font-size:20px;font-weight:bold;color:#16213e;margin:25px 0 10px;padding-left:10px;border-left:4px solid #0f3460;"
    H3 = "font-size:18px;font-weight:bold;color:#16213e;margin:20px 0 10px;"
    HEADING_DEFAULT = "font-size:17px;font-weight:bold;color:#16213e;margin:15px 0 8px;"
    BLOCKQUOTE = "margin:15px 0;padding:10px 15px;border-left:3px solid #0f3460;background-color:#f0f4f8;color:#4a6785;font-size:14px;"

else:
    # 未知主题回退到 formal
    H1 = "font-size:24px;font-weight:bold;color:#1a1a1a;text-align:center;margin:20px 0 10px;line-height:1.4;"
    H2 = "font-size:20px;font-weight:bold;color:#1a1a1a;margin:25px 0 10px;padding-left:10px;border-left:4px solid #07c160;"
    H3 = "font-size:18px;font-weight:bold;color:#1a1a1a;margin:20px 0 10px;"
    HEADING_DEFAULT = "font-size:17px;font-weight:bold;color:#1a1a1a;margin:15px 0 8px;"
    BLOCKQUOTE = "margin:15px 0;padding:10px 15px;border-left:3px solid #07c160;background-color:#f7f7f7;color:#666;font-size:14px;"
