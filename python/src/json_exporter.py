"""
JSON 导入导出模块 - PhotoManager

导出数据库到 JSON，导入 JSON 到数据库
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from .database import Database
from .logger import get_logger

log = get_logger(__name__)

CURRENT_VERSION = "1.0.0"


class JsonExporter:
    """JSON 导出器"""
    
    def __init__(self, db: Database):
        """初始化导出器
        
        Args:
            db: 数据库实例
        """
        self.db = db
    
    def export(self, output_path: str) -> bool:
        """导出数据库到 JSON 文件
        
        Args:
            output_path: 输出文件路径
            
        Returns:
            是否成功
        """
        log.info(f"Exporting database to: {output_path}")
        
        try:
            # 收集所有数据
            data = {
                'version': CURRENT_VERSION,
                'exported_at': datetime.now().isoformat(),
                'photos': self._export_photos(),
                'tags': self._export_tags(),
                'faces': self._export_faces(),
                'subjects': self._export_subjects(),
                'settings': self._export_settings()
            }
            
            # 写入文件
            output = Path(output_path)
            output.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            log.info(f"Export completed: {len(data['photos'])} photos")
            return True
            
        except Exception as e:
            log.error(f"Export failed", exc_info=e)
            return False
    
    def _export_photos(self) -> List[Dict[str, Any]]:
        """导出照片数据"""
        cursor = self.db.execute("""
            SELECT 
                id, file_path, file_hash, file_size, file_name,
                taken_at, taken_at_local, created_at_file, modified_at_file,
                camera_make, camera_model, lens_model, iso, aperture,
                shutter_speed, focal_length, latitude, longitude,
                organized_path, organized_date, is_portrait, rating,
                thumb_path, exif_json, created_at
            FROM photo_info
            ORDER BY id
        """)
        
        photos = []
        for row in cursor.fetchall():
            photo = dict(row)
            # 转换日期
            for date_field in ['taken_at', 'taken_at_local', 'created_at_file', 
                             'modified_at_file', 'created_at']:
                if photo.get(date_field):
                    photo[date_field] = str(photo[date_field])
            photos.append(photo)
        
        return photos
    
    def _export_tags(self) -> List[Dict[str, Any]]:
        """导出标签数据"""
        cursor = self.db.execute("""
            SELECT id, name, color, parent_id, created_at
            FROM photo_tag
            ORDER BY id
        """)
        
        tags = []
        for row in cursor.fetchall():
            tag = dict(row)
            if tag.get('created_at'):
                tag['created_at'] = str(tag['created_at'])
            tags.append(tag)
        
        return tags
    
    def _export_photo_tags(self) -> List[Dict[str, Any]]:
        """导出照片-标签关联"""
        cursor = self.db.execute("""
            SELECT photo_id, tag_id, created_at
            FROM photo_photo_tag
            ORDER BY photo_id, tag_id
        """)
        
        photo_tags = []
        for row in cursor.fetchall():
            pt = dict(row)
            if pt.get('created_at'):
                pt['created_at'] = str(pt['created_at'])
            photo_tags.append(pt)
        
        return photo_tags
    
    def _export_faces(self) -> List[Dict[str, Any]]:
        """导出人脸数据"""
        cursor = self.db.execute("""
            SELECT 
                id, photo_id, face_x, face_y, face_w, face_h,
                embedding, subject_id, confidence, created_at
            FROM photo_face_detect
            ORDER BY id
        """)
        
        faces = []
        for row in cursor.fetchall():
            face = dict(row)
            # embedding 转换为 base64
            if face.get('embedding'):
                import base64
                face['embedding'] = base64.b64encode(face['embedding']).decode('ascii')
            if face.get('created_at'):
                face['created_at'] = str(face['created_at'])
            faces.append(face)
        
        return faces
    
    def _export_subjects(self) -> List[Dict[str, Any]]:
        """导出人物主题"""
        cursor = self.db.execute("""
            SELECT 
                id, name, avatar_path, embedding_avg, face_count, created_at
            FROM photo_face_subject
            ORDER BY id
        """)
        
        subjects = []
        for row in cursor.fetchall():
            subject = dict(row)
            if subject.get('embedding_avg'):
                import base64
                subject['embedding_avg'] = base64.b64encode(subject['embedding_avg']).decode('ascii')
            if subject.get('created_at'):
                subject['created_at'] = str(subject['created_at'])
            subjects.append(subject)
        
        return subjects
    
    def _export_settings(self) -> List[Dict[str, Any]]:
        """导出设置"""
        cursor = self.db.execute("""
            SELECT key, value, type, group_name, description
            FROM sys_setting
            ORDER BY key
        """)
        
        return [dict(row) for row in cursor.fetchall()]


class JsonImporter:
    """JSON 导入器"""
    
    def __init__(self, db: Database):
        """初始化导入器
        
        Args:
            db: 数据库实例
        """
        self.db = db
    
    def import_data(self, input_path: str, merge: bool = True) -> bool:
        """从 JSON 文件导入数据
        
        Args:
            input_path: 输入文件路径
            merge: 是否合并（True=追加，False=覆盖）
            
        Returns:
            是否成功
        """
        log.info(f"Importing data from: {input_path}")
        
        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 验证版本
            version = data.get('version', 'unknown')
            log.info(f"Importing version: {version}")
            
            # 清空现有数据（如果覆盖）
            if not merge:
                self._clear_data()
            
            # 导入数据
            imported_photos = self._import_photos(data.get('photos', []))
            imported_tags = self._import_tags(data.get('tags', []))
            self._import_photo_tags(data.get('photo_tags', []), imported_photos, imported_tags)
            imported_subjects = self._import_subjects(data.get('subjects', []))
            self._import_faces(data.get('faces', []), imported_photos, imported_subjects)
            
            self.db.commit()
            log.info("Import completed")
            return True
            
        except Exception as e:
            log.error(f"Import failed", exc_info=e)
            return False
    
    def _clear_data(self):
        """清空现有数据"""
        log.warning("Clearing existing data")
        self.db.execute("DELETE FROM photo_face_detect")
        self.db.execute("DELETE FROM photo_face_subject")
        self.db.execute("DELETE FROM photo_photo_tag")
        self.db.execute("DELETE FROM photo_info")
        self.db.execute("DELETE FROM photo_tag")
        self.db.commit()
    
    def _import_photos(self, photos: List[Dict]) -> Dict[int, int]:
        """导入照片，返回旧ID到新ID的映射"""
        old_new_map = {}
        
        for photo in photos:
            old_id = photo.get('id')
            
            # 构建插入数据
            insert_data = {
                'file_path': photo.get('file_path'),
                'file_hash': photo.get('file_hash'),
                'file_size': photo.get('file_size'),
                'file_name': photo.get('file_name'),
                'taken_at': photo.get('taken_at'),
                'taken_at_local': photo.get('taken_at_local'),
                'created_at_file': photo.get('created_at_file'),
                'modified_at_file': photo.get('modified_at_file'),
                'camera_make': photo.get('camera_make'),
                'camera_model': photo.get('camera_model'),
                'lens_model': photo.get('lens_model'),
                'iso': photo.get('iso'),
                'aperture': photo.get('aperture'),
                'shutter_speed': photo.get('shutter_speed'),
                'focal_length': photo.get('focal_length'),
                'latitude': photo.get('latitude'),
                'longitude': photo.get('longitude'),
                'organized_path': photo.get('organized_path'),
                'organized_date': photo.get('organized_date'),
                'is_portrait': photo.get('is_portrait', 0),
                'rating': photo.get('rating', 0),
                'thumb_path': photo.get('thumb_path'),
                'exif_json': photo.get('exif_json')
            }
            
            try:
                new_id = self.db.insert_photo(insert_data)
                if old_id:
                    old_new_map[old_id] = new_id
            except Exception as e:
                log.debug(f"Failed to import photo {old_id}: {e}")
        
        return old_new_map
    
    def _import_tags(self, tags: List[Dict]) -> Dict[int, int]:
        """导入标签，返回旧ID到新ID的映射"""
        old_new_map = {}
        
        for tag in tags:
            old_id = tag.get('id')
            
            try:
                self.db.execute(
                    "INSERT OR IGNORE INTO photo_tag (name, color, parent_id) VALUES (?, ?, ?)",
                    (tag.get('name'), tag.get('color'), tag.get('parent_id'))
                )
                
                # 获取实际ID
                cursor = self.db.execute(
                    "SELECT id FROM photo_tag WHERE name = ?",
                    (tag.get('name'),)
                )
                row = cursor.fetchone()
                if row and old_id:
                    old_new_map[old_id] = row['id']
            except Exception as e:
                log.debug(f"Failed to import tag {old_id}: {e}")
        
        self.db.commit()
        return old_new_map
    
    def _import_photo_tags(self, photo_tags: List[Dict], photo_map: Dict, tag_map: Dict):
        """导入照片-标签关联"""
        for pt in photo_tags:
            old_photo_id = pt.get('photo_id')
            old_tag_id = pt.get('tag_id')
            
            new_photo_id = photo_map.get(old_photo_id, old_photo_id)
            new_tag_id = tag_map.get(old_tag_id, old_tag_id)
            
            try:
                self.db.execute(
                    "INSERT OR IGNORE INTO photo_photo_tag (photo_id, tag_id) VALUES (?, ?)",
                    (new_photo_id, new_tag_id)
                )
            except Exception as e:
                log.debug(f"Failed to import photo_tag: {e}")
        
        self.db.commit()
    
    def _import_subjects(self, subjects: List[Dict]) -> Dict[int, int]:
        """导入人物主题，返回旧ID到新ID的映射"""
        old_new_map = {}
        
        for subject in subjects:
            old_id = subject.get('id')
            
            import base64
            embedding = None
            if subject.get('embedding_avg'):
                try:
                    embedding = base64.b64decode(subject['embedding_avg'])
                except:
                    pass
            
            try:
                self.db.execute("""
                    INSERT INTO photo_face_subject 
                    (name, avatar_path, embedding_avg, face_count) 
                    VALUES (?, ?, ?, ?)
                """, (
                    subject.get('name'),
                    subject.get('avatar_path'),
                    embedding,
                    subject.get('face_count', 0)
                ))
                
                cursor = self.db.execute("SELECT last_insert_rowid() as id")
                row = cursor.fetchone()
                if row and old_id:
                    old_new_map[old_id] = row['id']
            except Exception as e:
                log.debug(f"Failed to import subject {old_id}: {e}")
        
        self.db.commit()
        return old_new_map
    
    def _import_faces(self, faces: List[Dict], photo_map: Dict, subject_map: Dict):
        """导出人脸数据"""
        for face in faces:
            old_photo_id = face.get('photo_id')
            old_subject_id = face.get('subject_id')
            
            new_photo_id = photo_map.get(old_photo_id, old_photo_id)
            new_subject_id = subject_map.get(old_subject_id, old_subject_id)
            
            import base64
            embedding = None
            if face.get('embedding'):
                try:
                    embedding = base64.b64decode(face['embedding'])
                except:
                    pass
            
            try:
                self.db.execute("""
                    INSERT INTO photo_face_detect 
                    (photo_id, face_x, face_y, face_w, face_h, embedding, subject_id, confidence) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    new_photo_id,
                    face.get('face_x'),
                    face.get('face_y'),
                    face.get('face_w'),
                    face.get('face_h'),
                    embedding,
                    new_subject_id,
                    face.get('confidence')
                ))
            except Exception as e:
                log.debug(f"Failed to import face: {e}")
        
        self.db.commit()


def export_db(db_path: str, output_path: str) -> bool:
    """快捷函数：导出数据库到 JSON
    
    Args:
        db_path: 数据库路径
        output_path: 输出文件路径
        
    Returns:
        是否成功
    """
    db = Database(db_path)
    db.connect()
    
    try:
        exporter = JsonExporter(db)
        return exporter.export(output_path)
    finally:
        db.close()


def import_db(db_path: str, input_path: str, merge: bool = True) -> bool:
    """快捷函数：从 JSON 导入数据库
    
    Args:
        db_path: 数据库路径
        input_path: 输入文件路径
        merge: 是否合并
        
    Returns:
        是否成功
    """
    db = Database(db_path)
    db.connect()
    
    try:
        importer = JsonImporter(db)
        return importer.import_data(input_path, merge)
    finally:
        db.close()
