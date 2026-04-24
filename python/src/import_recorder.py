"""
导入记录模块 - PhotoManager

记录导入操作，支持 Hash 去重
"""

from typing import Optional, Dict, List, Any
from .database import Database
from .logger import get_logger

log = get_logger(__name__)


class HashChecker:
    """Hash 去重检查器"""
    
    def __init__(self, db: Database):
        self.db = db
    
    def exists(self, file_hash: str) -> bool:
        """检查 hash 是否已存在"""
        cursor = self.db.execute(
            "SELECT 1 FROM photo_info WHERE file_hash = ? LIMIT 1",
            (file_hash,)
        )
        return cursor.fetchone() is not None
    
    def get_existing(self, file_hash: str) -> Optional[Dict[str, Any]]:
        """获取已存在的记录"""
        cursor = self.db.execute(
            "SELECT * FROM photo_info WHERE file_hash = ? LIMIT 1",
            (file_hash,)
        )
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None
    
    def get_existing_by_path(self, file_path: str) -> Optional[Dict[str, Any]]:
        """通过文件路径获取已存在的记录"""
        cursor = self.db.execute(
            "SELECT * FROM photo_info WHERE file_path = ? LIMIT 1",
            (file_path,)
        )
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None
    
    def check(self, file_hash: str, duplicate_mode: str = 'skip', file_path: str = None) -> tuple:
        """检查重复，返回 (action, reason, existing_path)
        
        Args:
            file_hash: 文件哈希
            duplicate_mode: skip=跳过, update=覆盖
            file_path: 文件路径（用于查找已存在的记录）
            
        Returns:
            (action, reason, existing_path) - action: added/skipped/updated, reason: 原因, existing_path: 已存在文件的路径
        """
        existing = self.get_existing(file_hash)
        
        if existing is None and file_path:
            # 按文件路径查找
            existing = self.get_existing_by_path(file_path)
        
        if existing is None:
            return 'added', None, None
        
        # 优先使用 organized_path，其次使用 file_path
        existing_path = existing.get('organized_path') or existing.get('file_path')
        log.info(f"HashChecker.check: hash={file_hash[:16] if file_hash else 'N/A'}..., existing={existing['id'] if existing else None}, existing_path={existing_path}")
        
        if duplicate_mode == 'update':
            return 'updated', f"updated existing record (id={existing['id']})", existing_path
        
        # duplicate_mode == 'skip'
        return 'skipped', 'duplicate', existing_path


class ImportRecorder:
    """导入记录器"""
    
    def __init__(self, db: Database):
        self.db = db
        self.hash_checker = HashChecker(db)
    
    def start_import(self, source_path: str, dest_path: str, 
                     mode: str = 'copy', duplicate_mode: str = 'skip') -> int:
        """开始导入会话，返回 import_id"""
        cursor = self.db.execute("""
            INSERT INTO photo_import_record 
            (source_path, dest_path, mode, duplicate_mode, status)
            VALUES (?, ?, ?, ?, 'running')
        """, (source_path, dest_path, mode, duplicate_mode))
        self.db.commit()
        
        import_id = cursor.lastrowid
        log.info(f"Started import session: id={import_id}, source={source_path}")
        return import_id
    
    def record_item(self, import_id: int, file_path: str, file_hash: str,
                    file_size: int, organized_path: str, 
                    action: str, reason: str = None, error_msg: str = None) -> int:
        """记录单个文件导入结果"""
        cursor = self.db.execute("""
            INSERT INTO photo_import_item 
            (import_id, file_path, file_hash, file_size, organized_path, action, reason, error_msg)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (import_id, file_path, file_hash, file_size, organized_path, action, reason, error_msg))
        self.db.commit()
        return cursor.lastrowid
    
    def update_stats(self, import_id: int):
        """更新导入会话统计"""
        self.db.execute("""
            UPDATE photo_import_record SET
                success_count = (SELECT COUNT(*) FROM photo_import_item WHERE import_id = ? AND action = 'added'),
                skip_count = (SELECT COUNT(*) FROM photo_import_item WHERE import_id = ? AND action = 'skipped'),
                fail_count = (SELECT COUNT(*) FROM photo_import_item WHERE import_id = ? AND action = 'failed'),
                total_count = (SELECT COUNT(*) FROM photo_import_item WHERE import_id = ?)
            WHERE id = ?
        """, (import_id, import_id, import_id, import_id, import_id))
        self.db.commit()
    
    def finish_import(self, import_id: int, status: str = 'completed', error_msg: str = None):
        """完成导入会话"""
        self.db.execute("""
            UPDATE photo_import_record 
            SET status = ?, error_msg = ?
            WHERE id = ?
        """, (status, error_msg, import_id))
        self.db.commit()
        log.info(f"Finished import session: id={import_id}, status={status}")
    
    def get_import_history(self, limit: int = 20, offset: int = 0,
                          status: str = None) -> List[Dict[str, Any]]:
        """获取导入历史"""
        if status:
            cursor = self.db.execute("""
                SELECT * FROM photo_import_record 
                WHERE status = ?
                ORDER BY created_at DESC 
                LIMIT ? OFFSET ?
            """, (status, limit, offset))
        else:
            cursor = self.db.execute("""
                SELECT * FROM photo_import_record 
                ORDER BY created_at DESC 
                LIMIT ? OFFSET ?
            """, (limit, offset))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def get_import_items(self, import_id: int, 
                        action: str = None) -> List[Dict[str, Any]]:
        """获取导入明细"""
        if action:
            cursor = self.db.execute("""
                SELECT * FROM photo_import_item 
                WHERE import_id = ? AND action = ?
                ORDER BY created_at DESC
            """, (import_id, action))
        else:
            cursor = self.db.execute("""
                SELECT * FROM photo_import_item 
                WHERE import_id = ?
                ORDER BY created_at DESC
            """, (import_id,))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def get_import_by_id(self, import_id: int) -> Optional[Dict[str, Any]]:
        """获取单个导入会话"""
        cursor = self.db.execute(
            "SELECT * FROM photo_import_record WHERE id = ?",
            (import_id,)
        )
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None
    
    def check_and_record(self, import_id: int, file_path: str, file_hash: str,
                        file_size: int, organized_path: str,
                        duplicate_mode: str = 'skip') -> tuple:
        """检查重复并记录，返回 (action, reason)
        
        Returns:
            (action, reason) - 添加到导入记录
        """
        action, reason, existing_path = self.hash_checker.check(file_hash, duplicate_mode)
        
        self.record_item(
            import_id=import_id,
            file_path=file_path,
            file_hash=file_hash,
            file_size=file_size,
            organized_path=existing_path if action in ('skipped', 'updated') else organized_path,
            action=action,
            reason=reason
        )
        
        self.update_stats(import_id)
        
        return action, reason
