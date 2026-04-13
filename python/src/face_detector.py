"""
人脸检测模块 - PhotoManager

占位实现：人脸检测功能已禁用
如需启用，请安装 insightface 和 onnxruntime：
    pip install insightface onnxruntime

或使用前端方案 face-api.js
"""

import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from .logger import get_logger

log = get_logger(__name__)

# 人脸检测功能已禁用
FACE_DETECTION_ENABLED = False

log.warning("Face detection is disabled. Install 'insightface' and 'onnxruntime' to enable.")


class FaceDetector:
    """人脸检测器（占位实现）"""
    
    def __init__(self, file_path: str):
        """初始化检测器
        
        Args:
            file_path: 图片文件路径
        """
        self.file_path = Path(file_path)
        self._faces: List[Dict[str, Any]] = []
        log.debug(f"FaceDetector placeholder initialized for: {file_path}")
    
    @property
    def available(self) -> bool:
        """是否可用"""
        return FACE_DETECTION_ENABLED and self.file_path.exists()
    
    def detect(self) -> List[Dict[str, Any]]:
        """检测人脸
        
        Returns:
            空列表（功能已禁用）
        """
        log.debug(f"Face detection disabled, returning empty for: {self.file_path}")
        return []
    
    def get_face_thumbnail(self, face_index: int, size: int = 150) -> Optional[bytes]:
        """获取人脸缩略图
        
        Args:
            face_index: 人脸索引
            size: 缩略图大小
            
        Returns:
            None（功能已禁用）
        """
        return None


class FaceMatcher:
    """人脸匹配器（占位实现）"""
    
    def __init__(self):
        """初始化匹配器"""
        self.known_encodings: List[bytes] = []
        self.known_names: List[str] = []
    
    def add_known_face(self, encoding: bytes, name: str):
        """添加已知人脸"""
        self.known_encodings.append(encoding)
        self.known_names.append(name)
    
    def match(self, encoding: bytes, threshold: float = 0.6) -> Optional[str]:
        """匹配人脸"""
        return None
    
    def compare_faces(self, encoding1: bytes, encoding2: bytes) -> float:
        """比较两个人脸的相似度"""
        return 0.0


def detect_faces(file_path: str) -> List[Dict[str, Any]]:
    """快捷函数：检测单张图片的人脸
    
    Args:
        file_path: 图片路径
        
    Returns:
        空列表（功能已禁用）
    """
    detector = FaceDetector(file_path)
    return detector.detect()
