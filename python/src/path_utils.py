"""
路径工具模块 - PhotoManager

提供从文件路径提取标签的工具函数
支持混合格式目录名（如 2025青岛、青岛2025）的标签提取
"""

import re
from datetime import datetime
from pathlib import Path
from typing import List, Optional


def extract_text_from_mixed_dir(name: str) -> Optional[str]:
    """从混合格式目录名中提取文字部分
    
    处理场景：
    - 20250414_青岛 → 青岛
    - 2025-青岛 → 青岛
    - 2025_01_青岛 → 青岛
    - 2025年青岛 → 青岛
    - 青岛_2025 → 青岛
    - 2025青岛 → 青岛（数字+汉字直接相连）
    - 青岛2025 → 青岛（汉字+数字直接相连）
    - 2025旅游 → 旅游（数字+汉字）
    - 旅游2025 → 旅游（汉字+数字）
    
    Args:
        name: 目录名
        
    Returns:
        提取的文字标签，如果没有文字部分则返回 None
    """
    if not name:
        return None
    
    # 模式1：日期前缀 + 分隔符 + 文字（如 20250414_青岛、2025-青岛）
    # 匹配：8位数字 + [_-] + 文字，或 4位数字 + [_-] + 文字
    patterns_prefix = [
        r'^\d{8}[_\\-](.+)$',       # 20250414_青岛
        r'^\d{4}[_\\-](.+)$',         # 2025_青岛
        r'^\d{4}年(.+)$',            # 2025年青岛
        r'^\d{4}-\d{2}[_\\-](.+)$',   # 2025-01_青岛
    ]
    
    for pattern in patterns_prefix:
        match = re.match(pattern, name)
        if match:
            text = match.group(1).strip()
            if text:
                return sanitize_tag(text)
    
    # 模式2：日期前缀 + 汉字/文字（直接相连，无分隔符）
    # 如：2025青岛、20250414青岛
    # 匹配：4位数字或8位数字 + 汉字开头的内容
    pattern_digit_prefix = r'^(\d{4}|\d{8})([\u4e00-\u9fff].*)$'
    match = re.match(pattern_digit_prefix, name)
    if match:
        text = match.group(2).strip()
        if text:
            return sanitize_tag(text)
    
    # 模式3：文字前缀 + 分隔符 + 日期（如 青岛_2025）
    patterns_suffix = [
        r'^(.+?)[_\\-]\d{4}.*$',    # 青岛_2025、青岛-202504
        r'^(.+?)\d{4}.*$',           # 青岛2025（文字开头后接4位数字）
    ]
    
    for pattern in patterns_suffix:
        match = re.match(pattern, name)
        if match:
            text = match.group(1).strip()
            if text and not text.isdigit():
                return sanitize_tag(text)
    
    # 模式4：文字前缀 + 日期（直接相连，无分隔符）
    # 如：青岛2025、旅游2025
    # 匹配：汉字开头 + 4位数字或8位数字结尾
    pattern_text_prefix = r'^(.*?[\u4e00-\u9fff]+?)(\d{4}|\d{8})$'
    match = re.match(pattern_text_prefix, name)
    if match:
        text = match.group(1).strip()
        if text and not text.isdigit():
            return sanitize_tag(text)
    
    return None


def is_pure_date_dir(name: str) -> bool:
    """判断目录名是否为纯日期格式（排除混合格式）
    
    Args:
        name: 目录名
        
    Returns:
        True if 是纯日期格式，否则 False
    """
    # 纯日期格式
    date_patterns = [
        r'^\d{4}-\d{2}-\d{2}$',   # YYYY-MM-DD
        r'^\d{8}$',               # YYYYMMDD
        r'^\d{2}-\d{2}-\d{4}$',   # MM-DD-YYYY
    ]
    
    for pattern in date_patterns:
        if re.match(pattern, name):
            # 验证是否为有效日期
            try:
                if len(name) == 10 and '-' in name:  # YYYY-MM-DD
                    datetime.strptime(name, '%Y-%m-%d')
                elif len(name) == 8 and name.isdigit():  # YYYYMMDD
                    datetime.strptime(name, '%Y%m%d')
                return True
            except ValueError:
                pass
    return False


def process_dir_as_tag(name: str) -> Optional[str]:
    """处理目录名，返回标签或 None
    
    逻辑：
    1. 如果是纯日期目录 → 返回 None（排除）
    2. 如果是混合格式（日期+文字）→ 提取文字部分作为标签
    3. 其他情况 → 整个目录名作为标签
    
    Args:
        name: 目录名
        
    Returns:
        标签名或 None
    """
    # 1. 排除隐藏目录
    if name.startswith('.'):
        return None
    
    # 2. 排除系统目录
    if name in ('__pycache__', 'node_modules', '.git'):
        return None
    
    # 3. 检查是否为纯日期目录
    if is_pure_date_dir(name):
        return None
    
    # 4. 检查是否为混合格式（日期+文字），提取文字部分
    text_from_mixed = extract_text_from_mixed_dir(name)
    if text_from_mixed:
        return text_from_mixed
    
    # 5. 普通目录名，直接作为标签
    return sanitize_tag(name)


def extract_tags_from_path(file_path: str, import_root: str = None) -> List[str]:
    """从文件路径提取标签（智能处理混合格式目录名）
    
    Args:
        file_path: 照片文件路径
        import_root: 导入根目录（可选，用于计算相对路径）
        
    Returns:
        标签列表，如 ['青岛', 'vacation', 'beach']
    """
    p = Path(file_path)
    
    # 如果提供了 import_root，计算相对路径
    if import_root:
        try:
            rel_path = p.relative_to(import_root)
            dir_parts = list(rel_path.parent.parts)
        except ValueError:
            # 不在 import_root 下，使用绝对路径的目录
            dir_parts = list(p.parent.parts)
    else:
        dir_parts = list(p.parent.parts)
    
    # 处理每个目录部分
    tags = []
    seen = set()  # 去重
    
    for part in dir_parts:
        tag = process_dir_as_tag(part)
        if tag and tag not in seen:
            tags.append(tag)
            seen.add(tag)
    
    return tags


def sanitize_tag(name: str) -> Optional[str]:
    """清理标签名，转为合适格式
    
    Args:
        name: 原始标签名
        
    Returns:
        清理后的标签名
    """
    if not name:
        return None
    
    # 转小写（中文保持不变）
    tag = name.lower()
    # 替换空格和特殊字符为下划线
    tag = re.sub(r'[^\w\u4e00-\u9fff]', '_', tag)
    # 合并多个下划线
    tag = re.sub(r'_+', '_', tag)
    # 去除首尾下划线
    tag = tag.strip('_')
    return tag if tag else None
