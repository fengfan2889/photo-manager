"""
设置管理模块 - PhotoManager

处理系统设置的读取和保存
"""

from typing import Dict, Any, Optional
from .database import Database
from .logger import get_logger

log = get_logger(__name__)


class SettingRepo:
    """设置仓库"""
    
    def __init__(self, db: Database = None):
        """初始化
        
        Args:
            db: 数据库实例，默认使用全局实例
        """
        self.db = db or get_db()
    
    def get(self, key: str, default: str = None) -> Optional[str]:
        """获取单个配置
        
        Args:
            key: 配置键
            default: 默认值
            
        Returns:
            配置值，不存在返回默认值
        """
        try:
            row = self.db.execute(
                "SELECT value FROM sys_setting WHERE key = ?",
                (key,)
            ).fetchone()
            
            if row:
                return row[0]
            return default
            
        except Exception as e:
            log.error(f"Failed to get setting: {key}", exc_info=True)
            return default
    
    def set(self, key: str, value: str) -> bool:
        """设置单个配置
        
        Args:
            key: 配置键
            value: 配置值
            
        Returns:
            是否成功
        """
        try:
            self.db.execute(
                """
                INSERT INTO sys_setting (key, value, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(key) DO UPDATE SET value = ?, updated_at = CURRENT_TIMESTAMP
                """,
                (key, value, value)
            )
            self.db.commit()
            log.info(f"Setting saved: {key} = {value}")
            return True
            
        except Exception as e:
            log.error(f"Failed to save setting: {key}", exc_info=True)
            return False
    
    def get_group(self, group: str) -> Dict[str, str]:
        """获取配置组
        
        Args:
            group: 配置组名
            
        Returns:
            配置字典
        """
        try:
            rows = self.db.execute(
                "SELECT key, value FROM sys_setting WHERE group_name = ?",
                (group,)
            ).fetchall()
            
            return {row[0]: row[1] for row in rows}
            
        except Exception as e:
            log.error(f"Failed to get settings group: {group}", exc_info=True)
            return {}
    
    def set_group(self, settings: Dict[str, str]) -> bool:
        """批量保存配置
        
        Args:
            settings: 配置字典
            
        Returns:
            是否成功
        """
        try:
            for key, value in settings.items():
                self.db.execute(
                    """
                    INSERT INTO sys_setting (key, value, updated_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(key) DO UPDATE SET value = ?, updated_at = CURRENT_TIMESTAMP
                    """,
                    (key, value, value)
                )
            self.db.commit()
            log.info(f"Settings group saved: {list(settings.keys())}")
            return True
            
        except Exception as e:
            log.error(f"Failed to save settings group", exc_info=True)
            return False
    
    def get_organize_config(self) -> Dict[str, Any]:
        """获取整理配置
        
        Returns:
            整理配置字典
        """
        config = self.get_group('organize')
        return {
            'mode': config.get('organize_mode', 'copy'),
            'source': config.get('organize_source', ''),
            'base': config.get('organize_base', ''),
            'include_unknown': config.get('organize_include_unknown', 'true') == 'true',
            'time_priority': config.get('time_priority', 'exif>mtime>ctime')
        }
    
    def save_organize_config(self, mode: str = None, source: str = None, 
                            base: str = None, include_unknown: bool = None,
                            time_priority: str = None) -> bool:
        """保存整理配置
        
        Args:
            mode: 整理模式 (copy/move/link)
            source: 源目录
            base: 输出目录
            include_unknown: 是否包含无法识别时间的照片
            time_priority: 时间优先级
            
        Returns:
            是否成功
        """
        settings = {}
        if mode is not None:
            settings['organize_mode'] = mode
        if source is not None:
            settings['organize_source'] = source
        if base is not None:
            settings['organize_base'] = base
        if include_unknown is not None:
            settings['organize_include_unknown'] = 'true' if include_unknown else 'false'
        if time_priority is not None:
            settings['time_priority'] = time_priority
        
        if not settings:
            return True
        
        return self.set_group(settings)
