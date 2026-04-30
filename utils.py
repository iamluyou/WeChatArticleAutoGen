import re
import os


def sanitize_filename(title: str, max_length: int = 80) -> str:
    """
    清理文件名中的特殊字符，限制长度
    - 替换 ``\\/:*?"<>|`` 为下划线
    - 替换常见中文标点
    - 去除首尾空白和点号
    - 截断超长标题
    """
    if not title:
        return "untitled"
    # 替换不安全字符
    name = re.sub(r'[\\/:*?"<>|]', '_', title)
    # 替换中文标点
    name = re.sub(r'[？！：、""''《》【】（）]', '_', name)
    # 去除首尾空白和点号
    name = name.strip('. ')
    # 去除连续下划线
    name = re.sub(r'_+', '_', name)
    # 去除首尾下划线
    name = name.strip('_')
    # 限制长度
    if len(name) > max_length:
        name = name[:max_length].rstrip('_ ')
    # 空标题兜底
    return name or "untitled"


def get_unique_filepath(directory: str, filename: str, ext: str) -> str:
    """获取不冲突的文件路径，同名文件自动追加序号"""
    os.makedirs(directory, exist_ok=True)
    filepath = os.path.join(directory, f"{filename}{ext}")
    if not os.path.exists(filepath):
        return filepath
    i = 2
    while os.path.exists(os.path.join(directory, f"{filename}_{i}{ext}")):
        i += 1
    return os.path.join(directory, f"{filename}_{i}{ext}")


def get_output_dir(base_dir: str) -> str:
    """获取按日期的输出目录"""
    from datetime import datetime
    date_str = datetime.now().strftime("%Y-%m-%d")
    output_dir = os.path.join(base_dir, date_str)
    os.makedirs(output_dir, exist_ok=True)
    return output_dir
