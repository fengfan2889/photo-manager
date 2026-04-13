"""
日志模块 - PhotoManager

使用 loguru 实现统一日志管理
"""

import sys
from pathlib import Path
from loguru import logger


class Logger:
    """日志管理器"""
    
    _instance = None
    _log_level = "INFO"
    
    @classmethod
    def init(cls, log_dir: str = None, level: str = "INFO"):
        """初始化日志器
        
        Args:
            log_dir: 日志文件目录，默认为当前目录下的 logs
            level: 日志级别 (TRACE/DEBUG/INFO/SUCCESS/WARNING/ERROR)
        """
        cls._log_level = level.upper()
        
        # 移除默认 handler
        logger.remove()
        
        # 日志格式（包含异常信息）
        format_info = (
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level:^8}</level> | "
            "<cyan>{name}</cyan>.<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>\n{exception}"
        )
        
        # 日志输出到 stderr（供 Electron 捕获）
        logger.add(
            sys.stderr,
            level=cls._log_level,
            format=format_info,
            colorize=True,
            backtrace=True,
            diagnose=True
        )
        
        # 如果指定了日志目录，则输出到文件
        if log_dir:
            log_path = Path(log_dir)
            log_path.mkdir(parents=True, exist_ok=True)
            
            # 完整日志文件
            log_file = log_path / "photo-manager.log"
            logger.add(
                log_file,
                level="TRACE",
                rotation="10 MB",
                retention="7 days",
                format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level:^8} | {name}:{function}:{line} | {message}",
                encoding="utf-8"
            )
            
            # 错误日志单独文件
            error_file = log_path / "error.log"
            logger.add(
                error_file,
                level="ERROR",
                format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level:^8} | {name}:{function}:{line} | {message}\n{exception}",
                encoding="utf-8"
            )
    
    @classmethod
    def set_level(cls, level: str):
        """动态设置日志级别"""
        cls._log_level = level.upper()
    
    @classmethod
    def get_logger(cls, module: str = None):
        """获取模块日志器
        
        Args:
            module: 模块名称
            
        Returns:
            logger实例，绑定了模块名
        """
        if module:
            return logger.bind(name=module)
        return logger


def get_logger(name: str = None) -> "logger":
    """快捷获取日志器"""
    return Logger.get_logger(name)
