"""
PhotoManager - Python 主程序

支持 CLI 和 IPC 两种模式
"""

import sys
import json
import click
from pathlib import Path
from typing import Dict, Any, Optional

from .logger import Logger, get_logger
from .database import Database, init_database
from .organizer import PhotoOrganizer
from .exif_parser import parse_exif, get_file_info
from .face_detector import detect_faces, FaceDetector
from .json_exporter import export_db, import_db
from .photo_repo import PhotoRepo, TagRepo, FaceRepo, SubjectRepo
from .setting_repo import SettingRepo

# 初始化日志
Logger.init(level="INFO")
log = get_logger(__name__)

# 数据库路径
DB_PATH = Path.home() / ".photo-manager" / "photo-manager.db"


class IPCServer:
    """IPC 服务端（用于与 Electron 通信）"""
    
    def __init__(self, db_path: str = None):
        """初始化 IPC 服务
        
        Args:
            db_path: 数据库路径
        """
        self.db_path = db_path or str(DB_PATH)
        self.db: Optional[Database] = None
        self.photo_repo: Optional[PhotoRepo] = None
        self.tag_repo: Optional[TagRepo] = None
        self.face_repo: Optional[FaceRepo] = None
        self.subject_repo: Optional[SubjectRepo] = None
        self.setting_repo: Optional[SettingRepo] = None
        
    def connect(self):
        """连接数据库"""
        # 确保目录存在
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        # 初始化数据库（创建表）
        self.db = init_database(self.db_path)
        self.db.connect()
        
        # 初始化仓库
        self.photo_repo = PhotoRepo(self.db)
        self.tag_repo = TagRepo(self.db)
        self.face_repo = FaceRepo(self.db)
        self.subject_repo = SubjectRepo(self.db)
        self.setting_repo = SettingRepo(self.db)
        
        log.info(f"Connected to database: {self.db_path}")
    
    def close(self):
        """关闭连接"""
        if self.db:
            self.db.close()
    
    def handle_command(self, command: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """处理 IPC 命令
        
        Args:
            command: 命令名称
            args: 命令参数
            
        Returns:
            命令结果
        """
        try:
            # 照片操作
            if command == "organize":
                return self._organize(args)
            elif command == "query-photos":
                return self._query_photos(args)
            elif command == "get-photo":
                return self._get_photo(args)
            elif command == "set-rating":
                return self._set_rating(args)
            
            # 标签操作
            elif command == "get-tags":
                return self._get_tags(args)
            elif command == "create-tag":
                return self._create_tag(args)
            elif command == "update-tag":
                return self._update_tag(args)
            elif command == "delete-tag":
                return self._delete_tag(args)
            elif command == "get-photo-tags":
                return self._get_photo_tags(args)
            elif command == "add-tag":
                return self._add_tag(args)
            elif command == "remove-tag":
                return self._remove_tag(args)
            
            # 人脸操作
            elif command == "detect-faces":
                return self._detect_faces(args)
            elif command == "get-faces":
                return self._get_faces(args)
            elif command == "name-face":
                return self._name_face(args)
            elif command == "get-subjects":
                return self._get_subjects(args)
            
            # 数据操作
            elif command == "export-json":
                return self._export_json(args)
            elif command == "import-json":
                return self._import_json(args)
            elif command == "get-stats":
                return self._get_stats(args)
            
            # 配置操作
            elif command == "get-settings":
                return self._get_settings(args)
            elif command == "save-settings":
                return self._save_settings(args)
            else:
                return {"success": False, "error": f"Unknown command: {command}"}
        except Exception as e:
            log.error(f"Command failed: {command}", exc_info=e)
            return {"success": False, "error": str(e)}
    
    # ============ 照片操作 ============
    
    def _organize(self, args: Dict) -> Dict:
        """整理照片"""
        source = args.get("source")
        dest = args.get("dest", "")
        mode = args.get("mode", "copy")
        include_unknown = args.get("include_unknown", True)
        
        if not source:
            return {"success": False, "error": "Source directory required"}
        
        if not dest:
            dest = str(DB_PATH.parent / "organized")
        
        organizer = PhotoOrganizer(
            source_dir=source,
            dest_dir=dest,
            mode=mode,
            include_unknown=include_unknown,
            photo_repo=self.photo_repo
        )
        
        result = organizer.organize()
        return {"success": True, "data": result}
    
    def _query_photos(self, args: Dict) -> Dict:
        """查询照片"""
        limit = args.get("limit", 100)
        offset = args.get("offset", 0)
        
        photos = self.photo_repo.get_list(
            limit=limit,
            offset=offset,
            rating=args.get("rating"),
            is_portrait=args.get("is_portrait"),
            tag_id=args.get("tag_id"),
            date_from=args.get("date_from"),
            date_to=args.get("date_to"),
            search=args.get("search")
        )
        
        # 转换日期
        for photo in photos:
            for key in ['taken_at', 'created_at', 'created_at_file', 'modified_at_file']:
                if photo.get(key):
                    photo[key] = str(photo[key])
        
        return {"success": True, "data": photos}
    
    def _get_photo(self, args: Dict) -> Dict:
        """获取单个照片"""
        photo_id = args.get("id")
        
        if not photo_id:
            return {"success": False, "error": "Photo ID required"}
        
        photo = self.photo_repo.get_by_id(photo_id)
        
        if not photo:
            return {"success": False, "error": "Photo not found"}
        
        result = dict(photo)
        for key in ['taken_at', 'created_at', 'created_at_file', 'modified_at_file']:
            if result.get(key):
                result[key] = str(result[key])
        
        return {"success": True, "data": result}
    
    def _set_rating(self, args: Dict) -> Dict:
        """设置照片评分"""
        photo_id = args.get("photo_id")
        rating = args.get("rating", 0)
        
        if not photo_id:
            return {"success": False, "error": "Photo ID required"}
        
        self.photo_repo.set_rating(photo_id, rating)
        return {"success": True}
    
    # ============ 标签操作 ============
    
    def _get_tags(self, args: Dict) -> Dict:
        """获取所有标签"""
        tags = self.tag_repo.get_all()
        return {"success": True, "data": tags}
    
    def _create_tag(self, args: Dict) -> Dict:
        """创建标签"""
        name = args.get("name")
        color = args.get("color", "#808080")
        
        if not name:
            return {"success": False, "error": "Tag name required"}
        
        tag_id = self.tag_repo.create(name, color)
        return {"success": True, "data": {"id": tag_id}}
    
    def _update_tag(self, args: Dict) -> Dict:
        """更新标签"""
        tag_id = args.get("id")
        name = args.get("name")
        color = args.get("color")
        
        if not tag_id:
            return {"success": False, "error": "Tag ID required"}
        
        self.tag_repo.update(tag_id, name, color)
        return {"success": True}
    
    def _delete_tag(self, args: Dict) -> Dict:
        """删除标签"""
        tag_id = args.get("id")
        
        if not tag_id:
            return {"success": False, "error": "Tag ID required"}
        
        self.tag_repo.delete(tag_id)
        return {"success": True}
    
    def _get_photo_tags(self, args: Dict) -> Dict:
        """获取照片的标签"""
        photo_id = args.get("photo_id")
        
        if not photo_id:
            return {"success": False, "error": "Photo ID required"}
        
        tags = self.tag_repo.get_photo_tags(photo_id)
        return {"success": True, "data": tags}
    
    def _add_tag(self, args: Dict) -> Dict:
        """添加照片标签"""
        photo_id = args.get("photo_id")
        tag_id = args.get("tag_id")
        
        if not photo_id or not tag_id:
            return {"success": False, "error": "Photo ID and Tag ID required"}
        
        self.tag_repo.add_photo_tag(photo_id, tag_id)
        return {"success": True}
    
    def _remove_tag(self, args: Dict) -> Dict:
        """移除照片标签"""
        photo_id = args.get("photo_id")
        tag_id = args.get("tag_id")
        
        if not photo_id or not tag_id:
            return {"success": False, "error": "Photo ID and Tag ID required"}
        
        self.tag_repo.remove_photo_tag(photo_id, tag_id)
        return {"success": True}
    
    # ============ 人脸操作 ============
    
    def _detect_faces(self, args: Dict) -> Dict:
        """检测人脸"""
        photo_id = args.get("photo_id")
        
        if not photo_id:
            return {"success": False, "error": "Photo ID required"}
        
        photo = self.photo_repo.get_by_id(photo_id)
        if not photo:
            return {"success": False, "error": "Photo not found"}
        
        file_path = photo['file_path']
        
        # 检测人脸
        faces = detect_faces(file_path)
        
        # 保存到数据库
        for face in faces:
            self.face_repo.insert({
                'photo_id': photo_id,
                'face_x': face.get('face_x'),
                'face_y': face.get('face_y'),
                'face_w': face.get('face_w'),
                'face_h': face.get('face_h'),
                'embedding': face.get('embedding'),
                'confidence': face.get('confidence')
            })
        
        # 更新照片的人像标记
        if len(faces) > 0:
            self.photo_repo.set_portrait(photo_id, True)
        
        return {"success": True, "data": {"count": len(faces), "faces": faces}}
    
    def _get_faces(self, args: Dict) -> Dict:
        """获取照片的人脸"""
        photo_id = args.get("photo_id")
        
        if not photo_id:
            return {"success": False, "error": "Photo ID required"}
        
        faces = self.face_repo.get_by_photo(photo_id)
        return {"success": True, "data": faces}
    
    def _name_face(self, args: Dict) -> Dict:
        """命名人脸"""
        face_id = args.get("face_id")
        subject_id = args.get("subject_id")
        
        if not face_id:
            return {"success": False, "error": "Face ID required"}
        
        # 如果有 subject_id，创建或更新人物
        if subject_id:
            self.face_repo.set_subject(face_id, subject_id)
        else:
            # 创建新人物
            name = args.get("name", "未知人物")
            subject_id = self.subject_repo.create(name)
            self.face_repo.set_subject(face_id, subject_id)
        
        return {"success": True, "data": {"subject_id": subject_id}}
    
    def _get_subjects(self, args: Dict) -> Dict:
        """获取所有人物"""
        subjects = self.subject_repo.get_all()
        return {"success": True, "data": subjects}
    
    # ============ 数据操作 ============
    
    def _export_json(self, args: Dict) -> Dict:
        """导出 JSON"""
        output_path = args.get("output_path")
        
        if not output_path:
            return {"success": False, "error": "Output path required"}
        
        success = export_db(self.db_path, output_path)
        return {"success": success}
    
    def _import_json(self, args: Dict) -> Dict:
        """导入 JSON"""
        input_path = args.get("input_path")
        merge = args.get("merge", True)
        
        if not input_path:
            return {"success": False, "error": "Input path required"}
        
        success = import_db(self.db_path, input_path, merge)
        return {"success": success}
    
    def _get_stats(self, args: Dict) -> Dict:
        """获取统计信息"""
        total = self.photo_repo.count()
        portrait_count = self.photo_repo.count(is_portrait=True)
        tagged_count = self.photo_repo.count(tag_id=args.get("tag_id"))
        
        return {
            "success": True,
            "data": {
                "total_photos": total,
                "portrait_photos": portrait_count,
                "tagged_photos": tagged_count
            }
        }
    
    # ============ 配置操作 ============
    
    def _get_settings(self, args: Dict) -> Dict:
        """获取配置"""
        group = args.get("group", "organize")
        
        if group == "organize":
            data = self.setting_repo.get_organize_config()
            return {"success": True, "data": data}
        else:
            data = self.setting_repo.get_group(group)
            return {"success": True, "data": data}
    
    def _save_settings(self, args: Dict) -> Dict:
        """保存配置"""
        group = args.get("group", "organize")
        
        if group == "organize":
            success = self.setting_repo.save_organize_config(
                mode=args.get("mode"),
                source=args.get("source"),
                base=args.get("base"),
                include_unknown=args.get("include_unknown"),
                time_priority=args.get("time_priority")
            )
            return {"success": success}
        else:
            settings = args.get("settings", {})
            success = self.setting_repo.set_group(settings)
            return {"success": success}


def run_ipc():
    """运行 IPC 模式"""
    server = IPCServer()
    server.connect()
    
    # 发送就绪信号
    print(json.dumps({"ready": True, "version": "1.0"}), flush=True)
    log.info("IPC server ready")
    
    try:
        # 从 stdin 读取命令
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            
            log.debug(f"Received command: {line}")
            
            try:
                request = json.loads(line)
                command = request.get("command")
                args = request.get("args", {})
                
                log.debug(f"Executing command: {command}, args: {args}")
                
                result = server.handle_command(command, args)
                
                # 添加 id 到响应
                result['id'] = request.get('id')
                
                # 对列表结果，只记录条数（非空才详细）
                data = result.get('data')
                if isinstance(data, list):
                    if len(data) > 0:
                        log.debug(f"Result: {command} returned {len(data)} items")
                    else:
                        log.debug(f"Result: {command} returned empty list")
                else:
                    log.debug(f"Result: {command}, success: {result.get('success')}")
                
                # 输出结果到 stdout
                output = json.dumps(result)
                print(output, flush=True)
                
            except json.JSONDecodeError as e:
                log.error(f"Invalid JSON: {e}")
                print(json.dumps({"success": False, "error": f"Invalid JSON: {e}"}), flush=True)
            except Exception as e:
                log.error(f"Command error", exc_info=e)
                print(json.dumps({"success": False, "error": str(e)}), flush=True)
    finally:
        server.close()


# ============ CLI 命令 ============

@click.group()
def cli():
    """PhotoManager - 照片管理工具"""
    pass


@cli.command()
@click.option("--source", "-s", required=True, help="源目录")
@click.option("--dest", "-d", default="", help="目标目录")
@click.option("--mode", "-m", type=click.Choice(["copy", "move", "link"]), default="copy", help="整理模式")
@click.option("--init-db", is_flag=True, help="初始化数据库")
def organize(source: str, dest: str, mode: str, init_db: bool):
    """整理照片"""
    if init_db:
        # 初始化数据库
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        db = init_database(str(DB_PATH))
        db.connect()
        db.close()
        click.echo(f"Database initialized: {DB_PATH}")
    
    if not dest:
        dest = str(DB_PATH.parent / "organized")
    
    organizer = PhotoOrganizer(source, dest, mode)
    result = organizer.organize()
    
    click.echo(f"\n整理完成:")
    click.echo(f"  总数: {result['total']}")
    click.echo(f"  成功: {result['processed']}")
    click.echo(f"  跳过: {result['skipped']}")
    click.echo(f"  失败: {result['failed']}")


@cli.command()
@click.option("--output", "-o", required=True, help="输出文件路径")
def export(output: str):
    """导出数据库到 JSON"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    # 确保数据库存在
    if not DB_PATH.exists():
        db = init_database(str(DB_PATH))
        db.connect()
        db.close()
    
    success = export_db(str(DB_PATH), output)
    
    if success:
        click.echo(f"导出成功: {output}")
    else:
        click.echo("导出失败", err=True)
        sys.exit(1)


@cli.command()
@click.option("--input", "-i", required=True, help="输入文件路径")
@click.option("--merge/--replace", default=True, help="合并或替换")
def import_json(input: str, merge: bool):
    """从 JSON 导入数据库"""
    success = import_db(str(DB_PATH), input, merge)
    
    if success:
        click.echo("导入成功")
    else:
        click.echo("导入失败", err=True)
        sys.exit(1)


@cli.command()
def init():
    """初始化数据库"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = init_database(str(DB_PATH))
    db.connect()
    db.close()
    click.echo(f"Database initialized: {DB_PATH}")


@cli.command()
@click.argument("file_path")
def info(file_path: str):
    """查看图片信息"""
    exif = parse_exif(file_path)
    file_info = get_file_info(file_path)
    
    click.echo(f"文件: {file_path}")
    click.echo(f"大小: {file_info.get('file_size', 0)} bytes")
    click.echo(f"创建: {file_info.get('created_at_file', 'N/A')}")
    click.echo(f"修改: {file_info.get('modified_at_file', 'N/A')}")
    click.echo(f"相机: {exif.get('camera_make', 'N/A')} {exif.get('camera_model', '')}")
    click.echo(f"拍摄: {exif.get('taken_at', 'N/A')}")


if __name__ == "__main__":
    # 检查是否为 IPC 模式
    if len(sys.argv) > 1 and sys.argv[1] == "--ipc":
        sys.argv.pop(1)
        run_ipc()
    else:
        cli()
