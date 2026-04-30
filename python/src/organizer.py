"""
照片整理模块 - PhotoManager

根据拍摄时间整理照片到目标目录
"""

import os
import sys
import shutil
import json
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime
from .exif_parser import ExifParser, get_file_info, resolve_taken_time, is_video_file, get_video_creation_time
from .logger import get_logger
from .import_recorder import ImportRecorder
from PIL import Image

log = get_logger(__name__)

# 支持的图片格式
SUPPORTED_FORMATS = {'.jpg', '.jpeg', '.png', '.tiff', '.tif', '.webp', '.heic', '.heif'}

# 支持的视频格式
VIDEO_FORMATS = {'.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv', '.wmv', '.m4v'}

# 所有支持的文件格式
ALL_FORMATS = SUPPORTED_FORMATS | VIDEO_FORMATS


class PhotoOrganizer:
    """照片整理器"""
    
    def __init__(
        self,
        source_dir: str,
        dest_dir: str,
        mode: str = 'copy',
        include_unknown: bool = True,
        duplicate_mode: str = 'skip',
        on_progress: Optional[Callable] = None,
        photo_repo=None,  # 可选：用于保存到数据库
        import_recorder=None,  # 可选：导入记录器
        db=None  # 可选：数据库连接，用于记录操作日志
    ):
        """初始化整理器
        
        Args:
            source_dir: 源目录
            dest_dir: 目标目录
            mode: 整理模式 ('copy', 'move', 'link')
            include_unknown: 是否整理无法识别时间的照片
            duplicate_mode: 重复文件处理模式 ('skip', 'update')
            on_progress: 进度回调函数
            photo_repo: 可选，用于保存到数据库
            import_recorder: 可选，导入记录器
        """
        self.source_dir = Path(source_dir)
        self.dest_dir = Path(dest_dir)
        self.mode = mode
        self.include_unknown = include_unknown
        self.duplicate_mode = duplicate_mode
        self.on_progress = on_progress
        self.photo_repo = photo_repo  # 数据库仓库
        self.import_recorder = import_recorder  # 导入记录器
        self.db = db  # 数据库连接，用于记录操作日志
        
        # 导入会话 ID
        self.import_id: Optional[int] = None
        
        # 统计
        self.total = 0
        self.processed = 0
        self.skipped = 0
        self.failed = 0
        self.errors: List[str] = []
        
        # 移动日志
        self.move_logs: List[Dict[str, Any]] = []
        
        log.info(f"PhotoOrganizer initialized: {source_dir} -> {dest_dir} ({mode})")
    
    def scan(self) -> List[Path]:
        """扫描源目录中的媒体文件（图片+视频）
        
        Returns:
            媒体文件路径列表
        """
        log.info(f"Scanning: {self.source_dir}")
        
        files = []
        for root, _, filenames in os.walk(self.source_dir):
            for filename in filenames:
                file_path = Path(root) / filename
                if file_path.suffix.lower() in ALL_FORMATS:
                    files.append(file_path)
        
        self.total = len(files)
        log.info(f"Found {self.total} media files (images + videos)")

        return files
    
    def organize(self) -> Dict[str, Any]:
        """执行整理
        
        Returns:
            整理结果统计
        """
        # 创建导入会话
        if self.import_recorder:
            self.import_id = self.import_recorder.start_import(
                source_path=str(self.source_dir),
                dest_path=str(self.dest_dir),
                mode=self.mode,
                duplicate_mode=self.duplicate_mode
            )
        
        files = self.scan()
        
        for i, file_path in enumerate(files):
            try:
                result = self._process_file(file_path)
                if result:
                    self.processed += 1
                # 不在这里统计 skipped，因为 _process_file 内部已经统计了
            except Exception as e:
                log.error(f"Failed to process {file_path}", exc_info=e)
                self.failed += 1
                self.errors.append(f"{file_path}: {str(e)}")
                # 记录失败照片操作日志
                if self.db:
                    self.db.record_log_operation(
                        action='failed',
                        source_path=str(file_path),
                        action_type='import',
                        status='failed',
                        error_msg=str(e)
                    )
                # 记录失败到导入明细
                if self.import_recorder and self.import_id:
                    self.import_recorder.record_item(
                        import_id=self.import_id,
                        file_path=str(file_path),
                        file_hash='',
                        file_size=0,
                        organized_path=None,
                        action='failed',
                        reason=None,
                        error_msg=str(e)
                    )
                    self.import_recorder.update_stats(self.import_id)
            
            # 触发进度回调
            if self.on_progress:
                self.on_progress({
                    'current': i + 1,
                    'total': self.total,
                    'currentFile': str(file_path),
                    'status': f'处理中: {file_path.name}'
                })
            # 输出进度到 stdout 供 Electron 捕获（使用特殊前缀，立即刷新）
            print(f"__PM_PROGRESS__{json.dumps({'current': i + 1, 'total': self.total, 'status': file_path.name})}", flush=True)
        
        # 完成导入会话
        if self.import_recorder and self.import_id:
            status = 'completed' if self.failed == 0 else 'failed'
            error_msg = '; '.join(self.errors[:5]) if self.errors else None
            self.import_recorder.finish_import(self.import_id, status, error_msg)
        
        result = {
            'success': self.failed == 0,
            'total': self.total,
            'processed': self.processed,
            'skipped': self.skipped,
            'failed': self.failed,
            'errors': self.errors[:10],  # 最多返回10个错误
            'import_id': self.import_id  # 返回导入会话 ID
        }
        
        # 保存移动日志到文件
        if self.move_logs:
            self._save_move_log()
        
        log.info(f"Organize completed: {result}")
        return result
    
    def _process_file(self, file_path: Path) -> Optional[Path]:
        """处理单个文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            整理后的目标路径，失败返回 None
        """
        log.debug(f"Processing: {file_path}")
        
        # 计算文件哈希（提前计算用于去重检查）
        try:
            file_hash = self.compute_file_hash(str(file_path))
        except Exception as e:
            log.warning(f"Failed to compute hash for {file_path}: {e}")
            file_hash = ''
        
        # 检查重复
        action = 'added'
        reason = None
        existing_path = None  # 已存在的文件路径（用于显示对比）
        if self.import_recorder and file_hash:
            action, reason, existing_path = self.import_recorder.hash_checker.check(file_hash, self.duplicate_mode, str(file_path))
            
            if action == 'skipped':
                log.info(f"Skipping duplicate file: {file_path.name} (hash={file_hash[:16]}...) existing_path={existing_path}")
                self.skipped += 1
                # 记录照片操作日志
                if self.db:
                    self.db.record_log_operation(
                        action='skipped',
                        source_path=str(file_path),
                        dest_path=existing_path,
                        action_type='import',
                        status='success',
                        error_msg='duplicate'
                    )
                # 为已存在的照片添加来自新路径的标签
                if self.photo_repo and file_hash:
                    try:
                        existing_photo = self.photo_repo.get_by_hash(file_hash)
                        if existing_photo:
                            self.photo_repo.add_tags_from_path(
                                existing_photo['id'],
                                str(file_path),
                                str(self.source_dir)
                            )
                    except Exception as e:
                        log.error(f"Failed to add tags to existing photo: {e}", exc_info=e)
                # 记录到导入明细
                self.import_recorder.record_item(
                    import_id=self.import_id,
                    file_path=str(file_path),
                    file_hash=file_hash,
                    file_size=0,
                    organized_path=existing_path,  # 保存已存在文件的路径
                    action=action,
                    reason=reason
                )
                self.import_recorder.update_stats(self.import_id)
                return None
            
            if action == 'updated':
                log.info(f"Updating existing file: {file_path.name}")
        
        # 判断文件类型并解析
        is_video = file_path.suffix.lower() in VIDEO_FORMATS
        
        if is_video:
            # 视频文件 - 使用 ffprobe 获取时间
            taken_time = get_video_creation_time(str(file_path))
            exif_data = {}
        else:
            # 图片文件 - 使用 EXIF 解析
            exif_parser = ExifParser(str(file_path))
            exif_data = exif_parser.parse()
            taken_time = None
        
        file_info = get_file_info(str(file_path))
        
        # 如果图片没有从 EXIF 获取到时间，fallback 到文件时间
        if not is_video and not taken_time:
            taken_time = resolve_taken_time(exif_data, file_info)
        
        # 记录解析结果
        parse_result = {
            'file': str(file_path),
            'type': 'video' if is_video else 'image',
            'taken_time': taken_time,
            'exif': {
                'camera_make': exif_data.get('camera_make'),
                'camera_model': exif_data.get('camera_model'),
                'date_taken': exif_data.get('date_taken'),
            },
            'file_info': {
                'size': file_info.get('size'),
                'created': file_info.get('created'),
                'modified': file_info.get('modified'),
            }
        }
        
        if not taken_time and not self.include_unknown:
            log.debug(f"Skipping file without date: {file_path}")
            self.skipped += 1
            # 记录到导入明细
            if self.import_recorder and self.import_id:
                self.import_recorder.record_item(
                    import_id=self.import_id,
                    file_path=str(file_path),
                    file_hash=file_hash,
                    file_size=file_info.get('size', 0),
                    organized_path=None,
                    action='skipped',
                    reason='no_date'
                )
                self.import_recorder.update_stats(self.import_id)
            return None
        
        # 生成目标路径
        if taken_time:
            target_dir, target_name = self._generate_target_path(taken_time, file_path)
        else:
            target_dir = self.dest_dir / 'unknown_date'
            target_name = file_path.name
        
        target_path = target_dir / target_name
        
        # 处理文件名冲突
        target_path = self._resolve_conflict(target_path)
        
        # 执行整理操作
        log.debug(f"Target: {target_path}")
        
        # 记录原因
        reason = f"taken_time={taken_time}" if taken_time else "unknown_date"
        
        if self.mode == 'copy':
            shutil.copy2(file_path, target_path)
        elif self.mode == 'move':
            shutil.move(str(file_path), str(target_path))
        elif self.mode == 'link':
            # 创建符号链接
            try:
                os.symlink(file_path, target_path)
            except OSError:
                # Windows 上可能需要管理员权限，回退到复制
                shutil.copy2(file_path, target_path)
        
        # 记录移动日志
        self.move_logs.append({
            'timestamp': datetime.now().isoformat(),
            'source': str(file_path),
            'dest': str(target_path),
            'mode': self.mode,
            'reason': reason,
            'parse_result': parse_result
        })
        
        # 保存到数据库
        if self.photo_repo:
            photo_id = self._save_to_database(file_path, target_path, parse_result, file_hash)
            # 记录照片操作日志
            self.db.record_log_operation(
                action='added',
                source_path=str(file_path),
                dest_path=str(target_path),
                action_type='import',
                status='success',
                photo_id=photo_id
            )
            # 从文件路径提取标签并关联
            if photo_id and self.photo_repo:
                try:
                    self.photo_repo.add_tags_from_path(
                        photo_id,
                        str(file_path),
                        str(self.source_dir)
                    )
                except Exception as e:
                    log.error(f"Failed to extract tags from path: {e}", exc_info=e)
        else:
            photo_id = None
        
        # 记录到导入明细
        if self.import_recorder and self.import_id:
            self.import_recorder.record_item(
                import_id=self.import_id,
                file_path=str(file_path),
                file_hash=file_hash,
                file_size=file_info.get('size', 0),
                organized_path=str(target_path),
                action='added' if action == 'added' else action,
                reason=reason
            )
            self.import_recorder.update_stats(self.import_id)
        
        return target_path
    
    def _generate_target_path(self, taken_time: str, file_path: Path = None) -> tuple:
        """生成目标路径
        
        Args:
            taken_time: ISO 格式时间字符串
            file_path: 原文件路径（用于获取文件名）
            
        Returns:
            (目标目录, 文件名)
        """
        # 解析时间
        try:
            dt = datetime.fromisoformat(taken_time.replace('Z', '+00:00'))
            year = dt.year
            date_str = dt.strftime('%Y-%m-%d')
        except (ValueError, TypeError):
            year = 'unknown'
            date_str = 'unknown'
        
        # 构建目录结构
        target_dir = self.dest_dir / str(year) / date_str
        target_dir.mkdir(parents=True, exist_ok=True)
        
        # 文件名使用原文件名
        file_name = file_path.name if file_path else 'unknown'
        
        return target_dir, file_name
    
    def _resolve_conflict(self, target_path: Path) -> Path:
        """解决文件名冲突
        
        Args:
            target_path: 目标路径
            
        Returns:
            不冲突的目标路径
        """
        if not target_path.exists():
            return target_path
        
        # 尝试添加序号
        stem = target_path.stem
        suffix = target_path.suffix
        parent = target_path.parent
        counter = 1
        
        while True:
            new_path = parent / f"{stem}_{counter}{suffix}"
            if not new_path.exists():
                return new_path
            counter += 1
            
            # 防止无限循环
            if counter > 1000:
                timestamp = datetime.now().strftime('%H%M%S')
                return parent / f"{stem}_{timestamp}{suffix}"
    
    def compute_file_hash(self, file_path: str) -> str:
        """计算文件 SHA256 哈希
        
        Args:
            file_path: 文件路径
            
        Returns:
            文件哈希值
        """
        sha256 = hashlib.sha256()
        
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha256.update(chunk)
        
        return sha256.hexdigest()
    
    def _save_move_log(self):
        """保存移动日志到文件"""
        try:
            # 日志文件路径：目标目录下的 move_log.json
            log_file = self.dest_dir / 'move_log.json'
            
            # 读取现有日志
            existing_logs = []
            if log_file.exists():
                with open(log_file, 'r', encoding='utf-8') as f:
                    existing_logs = json.load(f)
            
            # 追加新日志
            existing_logs.extend(self.move_logs)
            
            # 写入文件
            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump(existing_logs, f, ensure_ascii=False, indent=2)
            
            log.info(f"Move log saved to {log_file}, {len(self.move_logs)} records")
            
        except Exception as e:
            log.error(f"Failed to save move log: {e}", exc_info=True)
    
    def _save_to_database(self, source_path: Path, dest_path: Path, parse_result: dict, file_hash: str = None) -> int:
        """保存照片信息到数据库
        
        Args:
            source_path: 原始文件路径
            dest_path: 目标文件路径
            parse_result: 解析结果
            file_hash: 预计算的文件哈希
            
        Returns:
            保存的照片记录 ID，失败返回 None
        """
        try:
            # 如果没有预计算哈希，则计算
            if not file_hash:
                file_hash = self.compute_file_hash(str(dest_path))
            
            # 检查是否已存在（根据 hash 去重）
            existing = self.photo_repo.get_by_hash(file_hash)
            if existing:
                # 如果是 update 模式，更新记录
                if self.duplicate_mode == 'update':
                    self.photo_repo.update(existing['id'], {
                        'file_path': str(dest_path),
                        'organized_date': datetime.now().isoformat(),
                    })
                    log.info(f"Updated existing record: {dest_path.name}")
                else:
                    log.debug(f"Photo already exists, skipping: {dest_path.name}")
                return
            
            # 文件信息
            file_info = get_file_info(str(dest_path))
            
            data = {
                'file_path': str(dest_path),
                'file_hash': file_hash,
                'file_size': file_info.get('size'),
                'file_name': dest_path.name,
                'taken_at': parse_result.get('taken_time'),
                'taken_at_local': None,
                'created_at_file': file_info.get('created'),
                'modified_at_file': file_info.get('modified'),
                'camera_make': parse_result.get('exif', {}).get('camera_make'),
                'camera_model': parse_result.get('exif', {}).get('camera_model'),
                'lens_model': None,
                'iso': None,
                'aperture': None,
                'shutter_speed': None,
                'focal_length': None,
                'latitude': None,
                'longitude': None,
                'organized_path': None,
                'organized_date': datetime.now().isoformat(),
                'is_portrait': 0,
                'rating': 0,
                'thumb_path': None,
                'exif_json': None,
                'import_id': self.import_id if self.import_id else None,
            }
            
            self.photo_repo.insert(data)
            log.info(f"Added to database: {dest_path.name}")
            return data.get('id')  # 返回插入的记录 ID
            
        except Exception as e:
            log.error(f"Failed to save to database: {e}", exc_info=True)
            return None
    
    def _generate_thumbnail(self, file_path: Path, size: int = 200) -> Optional[str]:
        """生成缩略图
        
        Args:
            file_path: 文件路径
            size: 缩略图大小
            
        Returns:
            缩略图路径，失败返回 None
        """
        try:
            # 缩略图目录
            thumb_dir = self.dest_dir / '.thumbnails'
            thumb_dir.mkdir(parents=True, exist_ok=True)
            
            # 缩略图路径
            thumb_path = thumb_dir / f"{file_path.stem}_thumb.jpg"
            
            # 如果缩略图已存在，直接返回
            if thumb_path.exists():
                return str(thumb_path)
            
            # 生成缩略图
            with Image.open(file_path) as img:
                # 转换为 RGB（处理 PNG 等）
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # 缩放
                img.thumbnail((size, size), Image.Resampling.LANCZOS)
                
                # 保存
                img.save(thumb_path, 'JPEG', quality=80)
            
            log.debug(f"Thumbnail generated: {thumb_path.name}")
            return str(thumb_path)
            
        except Exception as e:
            log.warning(f"Failed to generate thumbnail: {e}")
            return None
