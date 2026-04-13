"""
EXIF 解析模块 - PhotoManager

从图片文件中提取 EXIF 元数据
"""

import os
import io
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
from PIL import Image
from .logger import get_logger

log = get_logger(__name__)

# 支持的图片格式
SUPPORTED_FORMATS = {'.jpg', '.jpeg', '.png', '.tiff', '.tif', '.webp', '.heic', '.heif'}

# 支持的视频格式
VIDEO_FORMATS = {'.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv', '.wmv', '.m4v'}


class ExifParser:
    """EXIF 解析器"""
    
    def __init__(self, file_path: str):
        """初始化解析器
        
        Args:
            file_path: 图片文件路径
        """
        self.file_path = Path(file_path)
        self._exif_data: Optional[Dict[str, Any]] = None
    
    @property
    def exists(self) -> bool:
        """文件是否存在"""
        return self.file_path.exists()
    
    @property
    def is_supported(self) -> bool:
        """文件格式是否支持"""
        return self.file_path.suffix.lower() in SUPPORTED_FORMATS
    
    def parse(self) -> Dict[str, Any]:
        """解析 EXIF 数据
        
        Returns:
            包含 EXIF 信息的字典
        """
        if not self.exists:
            log.warning(f"File not found: {self.file_path}")
            return {}
        
        if not self.is_supported:
            log.warning(f"Unsupported format: {self.file_path}")
            return {}
        
        try:
            with Image.open(self.file_path) as img:
                self._exif_data = self._extract_exif(img)
                return self._exif_data
        except Exception as e:
            log.error(f"Failed to parse EXIF: {self.file_path}", exc_info=e)
            return {}
    
    def _extract_exif(self, img: Image.Image) -> Dict[str, Any]:
        """从 PIL Image 中提取 EXIF
        
        Args:
            img: PIL Image 对象
            
        Returns:
            EXIF 数据字典
        """
        result = {
            'camera_make': None,
            'camera_model': None,
            'lens_model': None,
            'iso': None,
            'aperture': None,
            'shutter_speed': None,
            'focal_length': None,
            'latitude': None,
            'longitude': None,
            'taken_at': None,
            'taken_at_local': None,
            'exif_json': {}
        }
        
        # 尝试获取 EXIF 数据
        exif = img.getexif()
        if not exif:
            log.debug(f"No EXIF data: {self.file_path}")
            return result
        
        # 遍历所有 EXIF 标签
        for tag_id, value in exif.items():
            tag_name = self._get_tag_name(tag_id)
            result['exif_json'][tag_name] = str(value)
            
            # 提取关键字段
            if tag_id == 0x010F:  # Make (厂商)
                result['camera_make'] = str(value).strip()
            elif tag_id == 0x0110:  # Model (型号)
                result['camera_model'] = str(value).strip()
            elif tag_id == 0x829A:  # ExposureTime (快门速度)
                result['shutter_speed'] = self._format_shutter_speed(value)
            elif tag_id == 0x829D:  # FNumber (光圈)
                result['aperture'] = float(value)
            elif tag_id == 0x8827:  # ISOSpeedRatings
                result['iso'] = int(value) if value else None
            elif tag_id == 0x920A:  # FocalLength (焦距)
                result['focal_length'] = self._format_focal_length(value)
            elif tag_id == 0x9003:  # DateTimeOriginal (拍摄时间)
                result['taken_at'] = self._parse_datetime(str(value))
            elif tag_id == 0x9004:  # DateTimeDigitized (数字化时间)
                if result['taken_at'] is None:
                    result['taken_at'] = self._parse_datetime(str(value))
            elif tag_id == 0x8769:  # EXIF IFD
                result.update(self._extract_sub_exif(value, img))
        
        return result
    
    def _extract_sub_exif(self, tag_data: int, img: Image.Image) -> Dict[str, Any]:
        """提取子 EXIF 数据（GPS 等）"""
        result = {}
        
        try:
            exif_data = img.getexif()
            if tag_data in exif_data:
                sub_exif = exif_data.get(tag_data)
                if sub_exif:
                    for sub_tag_id, sub_value in sub_exif.items():
                        # GPS 信息
                        if sub_tag_id == 0x0002:  # GPSLatitude
                            result['latitude'] = self._convert_gps(sub_value)
                        elif sub_tag_id == 0x0004:  # GPSLongitude
                            result['longitude'] = self._convert_gps(sub_value)
                        # 镜头信息
                        elif sub_tag_id == 0xA434:  # LensModel
                            result['lens_model'] = str(sub_value).strip()
        except Exception as e:
            log.debug(f"Failed to extract sub EXIF: {e}")
        
        return result
    
    def _get_tag_name(self, tag_id: int) -> str:
        """获取 EXIF 标签名称"""
        # 常用 EXIF 标签
        tag_names = {
            0x010F: 'Make',
            0x0110: 'Model',
            0x0112: 'Orientation',
            0x011A: 'XResolution',
            0x011B: 'YResolution',
            0x0131: 'Software',
            0x0132: 'DateTime',
            0x013B: 'Artist',
            0x8298: 'Copyright',
            0x8769: 'ExifIFDPointer',
            0x8825: 'GPSInfoIFDPointer',
            0x9000: 'ExifVersion',
            0x9003: 'DateTimeOriginal',
            0x9004: 'DateTimeDigitized',
            0x9201: 'ShutterSpeedValue',
            0x9202: 'ApertureValue',
            0x9203: 'BrightnessValue',
            0x9204: 'ExposureBiasValue',
            0x9205: 'MaxApertureValue',
            0x9206: 'SubjectDistance',
            0x9207: 'MeteringMode',
            0x9208: 'LightSource',
            0x9209: 'Flash',
            0x920A: 'FocalLength',
            0x927C: 'MakerNote',
            0x9286: 'UserComment',
            0x829A: 'ExposureTime',
            0x829D: 'FNumber',
            0x8822: 'ExposureProgram',
            0x8827: 'ISOSpeedRatings',
        }
        return tag_names.get(tag_id, f'Tag_{tag_id}')
    
    def _parse_datetime(self, date_str: str) -> Optional[str]:
        """解析 EXIF 日期时间字符串
        
        EXIF 格式: "YYYY:MM:DD HH:MM:SS"
        """
        try:
            dt = datetime.strptime(date_str, "%Y:%m:%d %H:%M:%S")
            return dt.isoformat()
        except (ValueError, TypeError):
            return None
    
    def _format_shutter_speed(self, value) -> str:
        """格式化快门速度"""
        try:
            if isinstance(value, tuple):
                # 格式: (分子, 分母)
                num, denom = value
                if num == 1:
                    return f"1/{denom}s"
                else:
                    return f"{num}/{denom}s"
            return str(value)
        except:
            return str(value)
    
    def _format_focal_length(self, value) -> Optional[float]:
        """格式化焦距"""
        try:
            if isinstance(value, tuple):
                num, denom = value
                return float(num) / float(denom)
            return float(value)
        except:
            return None
    
    def _convert_gps(self, coord: tuple) -> Optional[float]:
        """转换 GPS 坐标为十进制度数"""
        try:
            if len(coord) >= 3:
                degrees = float(coord[0])
                minutes = float(coord[1])
                seconds = float(coord[2])
                return degrees + minutes / 60 + seconds / 3600
            return None
        except:
            return None


def parse_exif(file_path: str) -> Dict[str, Any]:
    """快捷函数：解析单个文件的 EXIF
    
    Args:
        file_path: 文件路径
        
    Returns:
        EXIF 数据字典
    """
    parser = ExifParser(file_path)
    return parser.parse()


def get_file_info(file_path: str) -> Dict[str, Any]:
    """获取文件基本信息
    
    Args:
        file_path: 文件路径
        
    Returns:
        文件信息字典
    """
    path = Path(file_path)
    
    if not path.exists():
        return {}
    
    stat = path.stat()
    
    return {
        'file_size': stat.st_size,
        'file_name': path.name,
        'created_at_file': datetime.fromtimestamp(stat.st_ctime).isoformat(),
        'modified_at_file': datetime.fromtimestamp(stat.st_mtime).isoformat()
    }


def resolve_taken_time(exif_data: Dict[str, Any], file_info: Dict[str, Any]) -> Optional[str]:
    """解析拍摄时间（带 fallback）
    
    时间优先级:
    1. EXIF DateTimeOriginal
    2. EXIF DateTimeDigitized
    3. 文件创建时间
    4. 文件修改时间（较早者）
    
    Args:
        exif_data: EXIF 数据
        file_info: 文件信息
        
    Returns:
        拍摄时间 ISO 格式字符串
    """
    # 优先使用 EXIF 时间
    if exif_data.get('taken_at'):
        log.debug(f"Using EXIF time: {exif_data['taken_at']}")
        return exif_data['taken_at']
    
    # Fallback 到文件时间
    created = file_info.get('created_at_file')
    modified = file_info.get('modified_at_file')
    
    # 使用较早的时间
    if created and modified:
        taken_time = min(created, modified)
    elif created:
        taken_time = created
    elif modified:
        taken_time = modified
    else:
        taken_time = None
    
    if taken_time:
        log.debug(f"Using file time: {taken_time}")
    
    return taken_time


def get_video_creation_time(file_path: str) -> Optional[str]:
    """使用 ffprobe 获取视频创建时间
    
    Args:
        file_path: 视频文件路径
        
    Returns:
        ISO 格式时间字符串，失败返回 None
    """
    import subprocess
    import json
    
    try:
        result = subprocess.run([
            'ffprobe', '-v', 'error',
            '-select_streams', 'v:0',
            '-show_entries', 'stream=tags',
            '-of', 'json', file_path
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode != 0:
            return None
        
        data = json.loads(result.stdout)
        tags = data.get('streams', [{}])[0].get('tags', {})
        
        # 尝试多种时间字段
        for key in ['creation_time', 'DateTimeOriginal', 'date']:
            if key in tags:
                time_str = tags[key]
                # 转换为 ISO 格式
                try:
                    # 格式: 2021:10:30 09:43:08
                    dt = datetime.strptime(time_str, '%Y:%m:%d %H:%M:%S')
                    return dt.isoformat()
                except ValueError:
                    try:
                        # 格式: 2021-10-30T09:43:08Z
                        dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
                        return dt.isoformat()
                    except ValueError:
                        pass
        
        return None
        
    except FileNotFoundError:
        log.warning('ffprobe not found, video time extraction disabled')
        return None
    except Exception as e:
        log.debug(f'Failed to extract video time: {e}')
        return None


def is_video_file(file_path: str) -> bool:
    """检查是否为视频文件
    
    Args:
        file_path: 文件路径
        
    Returns:
        是否为视频文件
    """
    return Path(file_path).suffix.lower() in VIDEO_FORMATS
