"""
数据库模块 - PhotoManager

使用 SQLite 存储照片管理数据
"""

import sqlite3
from pathlib import Path
from typing import Optional
from .logger import get_logger

log = get_logger(__name__)


class Database:
    """数据库管理器"""
    
    def __init__(self, db_path: str = None):
        """初始化数据库
        
        Args:
            db_path: 数据库文件路径，默认为当前目录下的 photo-manager.db
        """
        if db_path is None:
            db_path = "photo-manager.db"
        
        self.db_path = Path(db_path)
        self.conn: Optional[sqlite3.Connection] = None
        
    def connect(self):
        """连接数据库"""
        log.debug(f"Connecting to database: {self.db_path}")
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        
    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
            log.debug("Database connection closed")
            
    def __enter__(self):
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        
    def execute(self, sql: str, params: tuple = None):
        """执行 SQL"""
        cursor = self.conn.cursor()
        if params:
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)
        return cursor
    
    def commit(self):
        """提交事务"""
        self.conn.commit()
        
    def get_photo_by_hash(self, file_hash: str):
        """通过哈希查询照片"""
        cursor = self.execute(
            "SELECT * FROM photo_info WHERE file_hash = ?",
            (file_hash,)
        )
        return cursor.fetchone()
    
    def get_photo_by_id(self, photo_id: int):
        """通过 ID 查询照片"""
        cursor = self.execute(
            "SELECT * FROM photo_info WHERE id = ?",
            (photo_id,)
        )
        return cursor.fetchone()
    
    def record_log_operation(
        self,
        action: str,
        source_path: str = None,
        dest_path: str = None,
        action_type: str = None,
        status: str = 'success',
        error_msg: str = None,
        photo_id: int = None
    ) -> int:
        """记录照片操作日志
        
        Args:
            action: 操作类型 (added/skipped/updated/failed)
            source_path: 源路径
            dest_path: 目标路径
            action_type: 操作子类型 (import/update/delete)
            status: 状态 (success/failed)
            error_msg: 错误信息
            photo_id: 关联的照片 ID
            
        Returns:
            日志记录 ID
        """
        cursor = self.execute("""
            INSERT INTO photo_log_operation 
            (photo_id, action, source_path, dest_path, action_type, status, error_msg)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (photo_id, action, source_path, dest_path, action_type, status, error_msg))
        self.commit()
        return cursor.lastrowid
    
    def get_photos(self, limit: int = 100, offset: int = 0):
        """获取照片列表"""
        cursor = self.execute(
            "SELECT * FROM photo_info ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset)
        )
        return cursor.fetchall()
    
    def insert_photo(self, data: dict) -> int:
        """插入照片记录"""
        sql = """
        INSERT INTO photo_info (
            file_path, file_hash, file_size, file_name,
            taken_at, taken_at_local, created_at_file, modified_at_file,
            camera_make, camera_model, lens_model, iso, aperture,
            shutter_speed, focal_length, latitude, longitude,
            organized_path, organized_date, rating,
            thumb_path, exif_json
        ) VALUES (
            :file_path, :file_hash, :file_size, :file_name,
            :taken_at, :taken_at_local, :created_at_file, :modified_at_file,
            :camera_make, :camera_model, :lens_model, :iso, :aperture,
            :shutter_speed, :focal_length, :latitude, :longitude,
            :organized_path, :organized_date, :rating,
            :thumb_path, :exif_json
        )
        """
        cursor = self.execute(sql, data)
        self.commit()
        return cursor.lastrowid


def init_database(db_path: str = None) -> Database:
    """初始化数据库（创建表结构）"""
    db = Database(db_path)
    db.connect()
    
    # photo_info
    db.execute("""
    CREATE TABLE IF NOT EXISTS photo_info (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
        file_path           TEXT NOT NULL UNIQUE,
        file_hash           TEXT NOT NULL,
        file_size           INTEGER,
        file_name           TEXT NOT NULL,
        taken_at            DATETIME,
        taken_at_local      DATETIME,
        created_at_file     DATETIME,
        modified_at_file    DATETIME,
        camera_make         TEXT,
        camera_model        TEXT,
        lens_model          TEXT,
        iso                 INTEGER,
        aperture            REAL,
        shutter_speed       TEXT,
        focal_length        REAL,
        latitude        REAL,
        longitude       REAL,
        organized_path  TEXT,
        organized_date  TEXT,
        rating          INTEGER DEFAULT 0,
        thumb_path      TEXT,
        exif_json       TEXT
    )
    """)
    
    # photo_tag
    db.execute("""
    CREATE TABLE IF NOT EXISTS photo_tag (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
        name        TEXT NOT NULL UNIQUE,
        color       TEXT DEFAULT '#808080',
        parent_id   INTEGER REFERENCES photo_tag(id) ON DELETE SET NULL
    )
    """)
    
    # photo_photo_tag
    db.execute("""
    CREATE TABLE IF NOT EXISTS photo_photo_tag (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
        photo_id    INTEGER NOT NULL REFERENCES photo_info(id) ON DELETE CASCADE,
        tag_id      INTEGER NOT NULL REFERENCES photo_tag(id) ON DELETE CASCADE,
        UNIQUE (photo_id, tag_id)
    )
    """)
    
    # photo_face_detect
    db.execute("""
    CREATE TABLE IF NOT EXISTS photo_face_detect (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
        photo_id        INTEGER NOT NULL REFERENCES photo_info(id) ON DELETE CASCADE,
        face_x          REAL,
        face_y          REAL,
        face_w          REAL,
        face_h          REAL,
        embedding       BLOB,
        subject_id      INTEGER REFERENCES photo_face_subject(id) ON DELETE SET NULL,
        confidence      REAL
    )
    """)
    
    # photo_face_subject
    db.execute("""
    CREATE TABLE IF NOT EXISTS photo_face_subject (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
        name            TEXT NOT NULL,
        avatar_path     TEXT,
        embedding_avg   BLOB,
        face_count      INTEGER DEFAULT 0
    )
    """)
    
    # photo_log_operation
    db.execute("""
    CREATE TABLE IF NOT EXISTS photo_log_operation (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
        photo_id        INTEGER REFERENCES photo_info(id) ON DELETE SET NULL,
        action          TEXT NOT NULL,
        source_path     TEXT,
        dest_path       TEXT,
        action_type     TEXT,
        status          TEXT,
        error_msg       TEXT
    )
    """)
    
    # photo_import_record
    db.execute("""
    CREATE TABLE IF NOT EXISTS photo_import_record (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
        source_path     TEXT NOT NULL,
        dest_path       TEXT NOT NULL,
        mode            TEXT NOT NULL DEFAULT 'copy',
        duplicate_mode  TEXT NOT NULL DEFAULT 'skip',
        total_count     INTEGER DEFAULT 0,
        success_count   INTEGER DEFAULT 0,
        skip_count      INTEGER DEFAULT 0,
        fail_count      INTEGER DEFAULT 0,
        status          TEXT NOT NULL DEFAULT 'running',
        error_msg       TEXT
    )
    """)
    
    # photo_import_item
    db.execute("""
    CREATE TABLE IF NOT EXISTS photo_import_item (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
        import_id       INTEGER NOT NULL REFERENCES photo_import_record(id) ON DELETE CASCADE,
        file_path       TEXT NOT NULL,
        file_hash       TEXT NOT NULL,
        file_size       INTEGER,
        organized_path   TEXT,
        action          TEXT NOT NULL,
        reason          TEXT,
        error_msg       TEXT
    )
    """)
    
    # sys_setting
    db.execute("""
    CREATE TABLE IF NOT EXISTS sys_setting (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
        key             TEXT NOT NULL UNIQUE,
        value           TEXT,
        type            TEXT,
        group_name      TEXT,
        description     TEXT
    )
    """)
    
    # sys_log_operation
    db.execute("""
    CREATE TABLE IF NOT EXISTS sys_log_operation (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
        level           TEXT NOT NULL,
        module          TEXT,
        action          TEXT,
        message         TEXT,
        detail          TEXT
    )
    """)
    
    # 创建索引
    db.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_photo_info_hash ON photo_info(file_hash)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_photo_info_taken_at ON photo_info(taken_at)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_photo_info_organized_date ON photo_info(organized_date)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_photo_info_rating ON photo_info(rating)")
    db.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_photo_tag_name ON photo_tag(name)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_photo_photo_tag_photo ON photo_photo_tag(photo_id)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_photo_photo_tag_tag ON photo_photo_tag(tag_id)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_photo_face_detect_photo ON photo_face_detect(photo_id)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_photo_face_detect_subject ON photo_face_detect(subject_id)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_photo_face_subject_name ON photo_face_subject(name)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_photo_log_operation_photo ON photo_log_operation(photo_id)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_photo_import_record_created ON photo_import_record(created_at)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_photo_import_record_status ON photo_import_record(status)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_photo_import_item_import ON photo_import_item(import_id)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_photo_import_item_hash ON photo_import_item(file_hash)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_photo_import_item_action ON photo_import_item(action)")
    db.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_sys_setting_key ON sys_setting(key)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_sys_log_operation_level ON sys_log_operation(level)")
    
    # 插入预设标签
    db.execute("""
    INSERT OR IGNORE INTO photo_tag (name, color) VALUES 
        ('人像', '#FF6B6B'),
        ('风景', '#4ECDC4'),
        ('建筑', '#45B7D1'),
        ('美食', '#FFA07A'),
        ('宠物', '#98D8C8'),
        ('旅行', '#9B59B6'),
        ('日常', '#95A5A6')
    """)
    
    # 插入预设配置
    db.execute("""
    INSERT OR IGNORE INTO sys_setting (key, value, type, group_name, description) VALUES
        ('organize_mode', 'copy', 'string', 'organize', '整理模式'),
        ('organize_source', '', 'string', 'organize', '整理源目录'),
        ('organize_base', '', 'string', 'organize', '整理输出根目录'),
        ('organize_include_unknown', 'true', 'boolean', 'organize', '是否整理无法识别时间的照片'),
        ('organize_duplicate_mode', 'skip', 'string', 'organize', '重复文件处理：skip/update'),
        ('time_priority', 'exif>mtime>ctime', 'string', 'organize', '时间优先级'),
        ('thumb_size', '200', 'number', 'display', '缩略图大小'),
        ('grid_columns', '4', 'number', 'display', '网格列数'),
        ('theme', 'light', 'string', 'display', '主题'),
('log_level', 'INFO', 'string', 'log', '日志级别')
    """)
    
    db.commit()
    log.info("Database initialized successfully")
    
    return db
