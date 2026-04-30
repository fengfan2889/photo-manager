"""
照片管理模块 - PhotoManager

提供照片相关的 CRUD 操作
"""

from typing import List, Dict, Any, Optional
from .database import Database
from .logger import get_logger

log = get_logger(__name__)


class PhotoRepo:
    """照片仓库类"""
    
    def __init__(self, db: Database, tag_repo: TagRepo = None):
        self.db = db
        self.tag_repo = tag_repo
    
    def get_by_id(self, photo_id: int) -> Optional[Dict[str, Any]]:
        """通过 ID 获取照片"""
        cursor = self.db.execute(
            "SELECT * FROM photo_info WHERE id = ?",
            (photo_id,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def get_by_hash(self, file_hash: str) -> Optional[Dict[str, Any]]:
        """通过哈希获取照片"""
        cursor = self.db.execute(
            "SELECT * FROM photo_info WHERE file_hash = ?",
            (file_hash,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def get_list(
        self,
        limit: int = 100,
        offset: int = 0,
        rating: int = None,
        is_portrait: bool = None,
        tag_id: int = None,
        date_from: str = None,
        date_to: str = None,
        search: str = None
    ) -> List[Dict[str, Any]]:
        """获取照片列表"""
        sql = "SELECT DISTINCT p.* FROM photo_info p WHERE 1=1"
        params = []
        
        if rating is not None:
            sql += " AND p.rating = ?"
            params.append(rating)
        
        if is_portrait is not None:
            sql += " AND p.is_portrait = ?"
            params.append(1 if is_portrait else 0)
        
        if tag_id is not None:
            sql += " AND EXISTS (SELECT 1 FROM photo_photo_tag pt WHERE pt.photo_id = p.id AND pt.tag_id = ?)"
            params.append(tag_id)
        
        if date_from:
            sql += " AND p.taken_at >= ?"
            params.append(date_from)
        
        if date_to:
            sql += " AND p.taken_at <= ?"
            params.append(date_to)
        
        if search:
            sql += " AND (p.file_name LIKE ? OR p.camera_model LIKE ?)"
            params.extend([f'%{search}%', f'%{search}%'])
        
        sql += " ORDER BY p.created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        cursor = self.db.execute(sql, tuple(params))
        return [dict(row) for row in cursor.fetchall()]
    
    def count(
        self,
        rating: int = None,
        is_portrait: bool = None,
        tag_id: int = None
    ) -> int:
        """获取照片总数"""
        sql = "SELECT COUNT(*) as count FROM photo_info WHERE 1=1"
        params = []
        
        if rating is not None:
            sql += " AND rating = ?"
            params.append(rating)
        
        if is_portrait is not None:
            sql += " AND is_portrait = ?"
            params.append(1 if is_portrait else 0)
        
        if tag_id is not None:
            sql += " AND EXISTS (SELECT 1 FROM photo_photo_tag pt WHERE pt.photo_id = photo_info.id AND pt.tag_id = ?)"
            params.append(tag_id)
        
        cursor = self.db.execute(sql, tuple(params))
        row = cursor.fetchone()
        return row['count'] if row else 0
    
    def insert(self, data: Dict[str, Any]) -> int:
        """插入照片"""
        return self.db.insert_photo(data)
    
    def update(self, photo_id: int, data: Dict[str, Any]) -> bool:
        """更新照片"""
        sets = []
        values = []
        
        for key, value in data.items():
            if key not in ('id', 'created_at'):
                sets.append(f"{key} = ?")
                values.append(value)
        
        if not sets:
            return False
        
        sets.append("updated_at = CURRENT_TIMESTAMP")
        values.append(photo_id)
        
        sql = f"UPDATE photo_info SET {', '.join(sets)} WHERE id = ?"
        self.db.execute(sql, tuple(values))
        self.db.commit()
        
        return True
    
    def set_rating(self, photo_id: int, rating: int) -> bool:
        """设置评分"""
        self.db.execute(
            "UPDATE photo_info SET rating = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (rating, photo_id)
        )
        self.db.commit()
        log.debug(f"Set rating {rating} for photo {photo_id}")
        return True
    
    def set_portrait(self, photo_id: int, is_portrait: bool) -> bool:
        """设置人像标记"""
        self.db.execute(
            "UPDATE photo_info SET is_portrait = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (1 if is_portrait else 0, photo_id)
        )
        self.db.commit()
        return True
    
    def add_tags_from_path(self, photo_id: int, file_path: str, import_root: str = None):
        """从文件路径提取标签并关联到照片
        
        Args:
            photo_id: 照片 ID
            file_path: 照片文件路径
            import_root: 导入根目录（用于计算相对路径）
        """
        if not self.tag_repo:
            return
        
        from .path_utils import extract_tags_from_path
        
        tags = extract_tags_from_path(file_path, import_root)
        
        for tag_name in tags:
            tag_id = self.tag_repo.get_or_create(tag_name)
            self.tag_repo.add_photo_tag(photo_id, tag_id)
        
        log.info(f"Added {len(tags)} tags to photo {photo_id}: {tags}")
    
    def delete(self, photo_id: int) -> bool:
        """删除照片"""
        self.db.execute(
            "DELETE FROM photo_info WHERE id = ?",
            (photo_id,)
        )
        self.db.commit()
        return True


class TagRepo:
    """标签仓库类"""
    
    def __init__(self, db: Database):
        self.db = db
    
    def get_all(self) -> List[Dict[str, Any]]:
        """获取所有标签"""
        cursor = self.db.execute(
            "SELECT * FROM photo_tag ORDER BY name"
        )
        return [dict(row) for row in cursor.fetchall()]
    
    def get_by_id(self, tag_id: int) -> Optional[Dict[str, Any]]:
        """通过 ID 获取标签"""
        cursor = self.db.execute(
            "SELECT * FROM photo_tag WHERE id = ?",
            (tag_id,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def get_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """通过名称获取标签"""
        cursor = self.db.execute(
            "SELECT * FROM photo_tag WHERE name = ?",
            (name,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def get_or_create(self, name: str, color: str = '#808080') -> int:
        """获取或创建标签，返回标签 ID
        
        Args:
            name: 标签名
            color: 标签颜色（仅创建时使用）
            
        Returns:
            标签 ID
        """
        # 先查找
        existing = self.get_by_name(name)
        if existing:
            return existing['id']
        # 不存在则创建
        return self.create(name, color)
    
    def create(self, name: str, color: str = '#808080', parent_id: int = None) -> int:
        """创建标签"""
        try:
            cursor = self.db.execute(
                "INSERT INTO photo_tag (name, color, parent_id) VALUES (?, ?, ?)",
                (name, color, parent_id)
            )
            self.db.commit()
            log.info(f"Created tag: {name}")
            return cursor.lastrowid
        except Exception as e:
            log.error(f"Failed to create tag: {name}", exc_info=e)
            raise
    
    def update(self, tag_id: int, name: str = None, color: str = None) -> bool:
        """更新标签"""
        sets = []
        values = []
        
        if name is not None:
            sets.append("name = ?")
            values.append(name)
        
        if color is not None:
            sets.append("color = ?")
            values.append(color)
        
        if not sets:
            return False
        
        values.append(tag_id)
        sql = f"UPDATE photo_tag SET {', '.join(sets)} WHERE id = ?"
        self.db.execute(sql, tuple(values))
        self.db.commit()
        return True
    
    def delete(self, tag_id: int) -> bool:
        """删除标签"""
        self.db.execute(
            "DELETE FROM photo_tag WHERE id = ?",
            (tag_id,)
        )
        self.db.commit()
        log.info(f"Deleted tag {tag_id}")
        return True
    
    def get_photo_tags(self, photo_id: int) -> List[Dict[str, Any]]:
        """获取照片的所有标签"""
        cursor = self.db.execute("""
            SELECT t.* FROM photo_tag t
            INNER JOIN photo_photo_tag pt ON t.id = pt.tag_id
            WHERE pt.photo_id = ?
            ORDER BY t.name
        """, (photo_id,))
        return [dict(row) for row in cursor.fetchall()]
    
    def add_photo_tag(self, photo_id: int, tag_id: int) -> bool:
        """添加照片标签"""
        try:
            self.db.execute(
                "INSERT OR IGNORE INTO photo_photo_tag (photo_id, tag_id) VALUES (?, ?)",
                (photo_id, tag_id)
            )
            self.db.commit()
            log.debug(f"Added tag {tag_id} to photo {photo_id}")
            return True
        except Exception as e:
            log.error(f"Failed to add photo tag", exc_info=e)
            return False
    
    def remove_photo_tag(self, photo_id: int, tag_id: int) -> bool:
        """移除照片标签"""
        self.db.execute(
            "DELETE FROM photo_photo_tag WHERE photo_id = ? AND tag_id = ?",
            (photo_id, tag_id)
        )
        self.db.commit()
        log.debug(f"Removed tag {tag_id} from photo {photo_id}")
        return True


class FaceRepo:
    """人脸仓库类"""
    
    def __init__(self, db: Database):
        self.db = db
    
    def get_by_photo(self, photo_id: int) -> List[Dict[str, Any]]:
        """获取照片的所有人脸"""
        cursor = self.db.execute("""
            SELECT fd.*, fs.name as subject_name
            FROM photo_face_detect fd
            LEFT JOIN photo_face_subject fs ON fd.subject_id = fs.id
            WHERE fd.photo_id = ?
            ORDER BY fd.id
        """, (photo_id,))
        return [dict(row) for row in cursor.fetchall()]
    
    def insert(self, data: Dict[str, Any]) -> int:
        """插入人脸记录"""
        cursor = self.db.execute("""
            INSERT INTO photo_face_detect 
            (photo_id, face_x, face_y, face_w, face_h, embedding, subject_id, confidence)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data.get('photo_id'),
            data.get('face_x'),
            data.get('face_y'),
            data.get('face_w'),
            data.get('face_h'),
            data.get('embedding'),
            data.get('subject_id'),
            data.get('confidence')
        ))
        self.db.commit()
        return cursor.lastrowid
    
    def set_subject(self, face_id: int, subject_id: int = None) -> bool:
        """设置人脸所属人物"""
        self.db.execute(
            "UPDATE photo_face_detect SET subject_id = ? WHERE id = ?",
            (subject_id, face_id)
        )
        self.db.commit()
        return True
    
    def delete_by_photo(self, photo_id: int) -> bool:
        """删除照片的所有人脸记录"""
        self.db.execute(
            "DELETE FROM photo_face_detect WHERE photo_id = ?",
            (photo_id,)
        )
        self.db.commit()
        return True
    
    def get_subject_faces(self, subject_id: int) -> List[Dict[str, Any]]:
        """获取人物的所有人脸"""
        cursor = self.db.execute("""
            SELECT fd.*, p.file_path, p.thumb_path
            FROM photo_face_detect fd
            INNER JOIN photo_info p ON fd.photo_id = p.id
            WHERE fd.subject_id = ?
            ORDER BY fd.created_at DESC
        """, (subject_id,))
        return [dict(row) for row in cursor.fetchall()]


class SubjectRepo:
    """人物主题仓库类"""
    
    def __init__(self, db: Database):
        self.db = db
    
    def get_all(self) -> List[Dict[str, Any]]:
        """获取所有人物"""
        cursor = self.db.execute(
            "SELECT * FROM photo_face_subject ORDER BY name"
        )
        return [dict(row) for row in cursor.fetchall()]
    
    def get_by_id(self, subject_id: int) -> Optional[Dict[str, Any]]:
        """通过 ID 获取人物"""
        cursor = self.db.execute(
            "SELECT * FROM photo_face_subject WHERE id = ?",
            (subject_id,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def create(self, name: str) -> int:
        """创建人物"""
        cursor = self.db.execute(
            "INSERT INTO photo_face_subject (name) VALUES (?)",
            (name,)
        )
        self.db.commit()
        log.info(f"Created subject: {name}")
        return cursor.lastrowid
    
    def update_name(self, subject_id: int, name: str) -> bool:
        """更新人物名称"""
        self.db.execute(
            "UPDATE photo_face_subject SET name = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (name, subject_id)
        )
        self.db.commit()
        return True
    
    def delete(self, subject_id: int) -> bool:
        """删除人物（解除关联但不删除人脸记录）"""
        # 先解除人脸关联
        self.db.execute(
            "UPDATE photo_face_detect SET subject_id = NULL WHERE subject_id = ?",
            (subject_id,)
        )
        # 删除人物
        self.db.execute(
            "DELETE FROM photo_face_subject WHERE id = ?",
            (subject_id,)
        )
        self.db.commit()
        return True
    
    def update_face_count(self, subject_id: int) -> bool:
        """更新人物关联人脸数"""
        cursor = self.db.execute(
            "SELECT COUNT(*) as count FROM photo_face_detect WHERE subject_id = ?",
            (subject_id,)
        )
        row = cursor.fetchone()
        count = row['count'] if row else 0
        
        self.db.execute(
            "UPDATE photo_face_subject SET face_count = ? WHERE id = ?",
            (count, subject_id)
        )
        self.db.commit()
        return True
