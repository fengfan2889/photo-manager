# 导入记录与 Hash 去重设计

## 版本信息

| 版本 | 日期 | 说明 |
|------|------|------|
| v1.0.0 | 2026-04-13 | 初始版本 |

---

## 1. 功能目标

### 1.1 导入记录

- 记录每次导入照片的操作
- 支持查看历史导入记录
- 支持按导入时间、状态筛选

### 1.2 Hash 去重

- 按文件内容 hash 判断是否重复
- 支持跳过/覆盖两种策略
- 记录跳过原因

### 1.3 直接操作模式

- 无需预扫描，直接处理
- 边处理边记录
- 完成后显示完整报告

---

## 2. 新增表设计

### 2.1 photo_import_record（导入会话）

记录一次完整的导入操作。

```sql
CREATE TABLE photo_import_record (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    -- 导入配置
    source_path     TEXT NOT NULL,
    dest_path       TEXT NOT NULL,
    mode            TEXT NOT NULL DEFAULT 'copy',
    duplicate_mode  TEXT NOT NULL DEFAULT 'skip',
    
    -- 统计
    total_count     INTEGER DEFAULT 0,
    success_count   INTEGER DEFAULT 0,
    skip_count      INTEGER DEFAULT 0,
    fail_count      INTEGER DEFAULT 0,
    
    -- 状态
    status          TEXT NOT NULL DEFAULT 'running',
    
    -- 错误信息
    error_msg       TEXT
);

CREATE INDEX idx_photo_import_record_created ON photo_import_record(created_at);
CREATE INDEX idx_photo_import_record_status ON photo_import_record(status);
```

### 2.2 photo_import_item（导入明细）

每个文件的导入记录。

```sql
CREATE TABLE photo_import_item (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    -- 关联
    import_id       INTEGER NOT NULL REFERENCES photo_import_record(id) ON DELETE CASCADE,
    
    -- 文件信息
    file_path       TEXT NOT NULL,
    file_hash       TEXT NOT NULL,
    file_size       INTEGER,
    
    -- 结果
    organized_path   TEXT,
    action          TEXT NOT NULL,
    reason          TEXT,
    error_msg       TEXT
);

CREATE INDEX idx_photo_import_item_import ON photo_import_item(import_id);
CREATE INDEX idx_photo_import_item_hash ON photo_import_item(file_hash);
CREATE INDEX idx_photo_import_item_action ON photo_import_item(action);
```

---

## 3. action 字段枚举

| 值 | 说明 |
|------|------|
| `added` | 新增导入成功 |
| `skipped` | 跳过（hash 重复） |
| `updated` | 更新（覆盖重复文件） |
| `failed` | 导入失败 |

---

## 4. duplicate_mode 字段枚举

| 值 | 说明 |
|------|------|
| `skip` | 跳过已存在的 hash（默认） |
| `update` | 覆盖已存在的 hash |

---

## 5. 处理流程

```
开始导入
    ↓
创建 import_record（status=running）
    ↓
遍历源目录文件
    ↓
┌─ 计算文件 hash ─┐
│                 │
│  hash 存在？    │
│                 │
└─┬───────────────┘
  │
  ├─ 否 → 正常导入 → action='added'
  │
  ├─ 是 + skip → 跳过 → action='skipped', reason='duplicate'
  │
  └─ 是 + update → 覆盖 → action='updated'
    ↓
创建 import_item 记录
    ↓
更新 import_record 统计
    ↓
全部完成 → status='completed'
```

---

## 6. 数据库修改

### 6.1 photo_info 表新增字段

```sql
ALTER TABLE photo_info ADD COLUMN import_id INTEGER REFERENCES photo_import_record(id);
```

### 6.2 完整建表 SQL

```sql
-- photo_import_record（导入会话）
CREATE TABLE photo_import_record (
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
);

CREATE INDEX idx_photo_import_record_created ON photo_import_record(created_at);
CREATE INDEX idx_photo_import_record_status ON photo_import_record(status);

-- photo_import_item（导入明细）
CREATE TABLE photo_import_item (
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
);

CREATE INDEX idx_photo_import_item_import ON photo_import_item(import_id);
CREATE INDEX idx_photo_import_item_hash ON photo_import_item(file_hash);
CREATE INDEX idx_photo_import_item_action ON photo_import_item(action);
```

---

## 7. Python 模块设计

### 7.1 ImportRecorder 类

```python
class ImportRecorder:
    """导入记录器"""
    
    def __init__(self, db: Database):
        self.db = db
    
    def start_import(self, source: str, dest: str, mode: str, duplicate_mode: str) -> int:
        """开始导入会话，返回 import_id"""
        pass
    
    def record_item(self, import_id: int, file_info: dict, action: str, reason: str = None):
        """记录单个文件导入结果"""
        pass
    
    def finish_import(self, import_id: int, status: str, error_msg: str = None):
        """完成导入会话"""
        pass
    
    def get_import_history(self, limit: int = 20) -> list:
        """获取导入历史"""
        pass
```

### 7.2 HashChecker 类

```python
class HashChecker:
    """Hash 去重检查"""
    
    def __init__(self, db: Database):
        self.db = db
    
    def exists(self, file_hash: str) -> bool:
        """检查 hash 是否已存在"""
        pass
    
    def get_existing(self, file_hash: str) -> dict:
        """获取已存在的记录"""
        pass
    
    def check(self, file_hash: str, duplicate_mode: str) -> tuple:
        """检查重复，返回 (action, reason)"""
        pass
```

---

## 8. IPC 命令扩展

| 命令 | 参数 | 返回 | 说明 |
|------|------|------|------|
| `get-import-history` | `limit` | `ImportRecord[]` | 获取导入历史 |
| `get-import-items` | `import_id` | `ImportItem[]` | 获取导入明细 |
| `start-import` | `source, dest, mode, duplicate_mode` | `import_id` | 开始导入 |
| `cancel-import` | `import_id` | `boolean` | 取消导入 |

---

## 9. 前端页面设计

### 9.1 导入历史页面

- 列表展示历史导入记录
- 显示：时间、源目录、文件数、状态
- 支持按状态筛选（全部/成功/失败）
- 点击查看导入明细

### 9.2 导入明细弹窗

- 显示该次导入的所有文件
- 按 action 分类（added/skipped/failed）
- 支持搜索文件名
- 失败文件显示错误原因

---

## 10. 配置文件扩展

```sql
-- sys_setting 新增配置
INSERT INTO sys_setting (key, value, type, group_name, description) VALUES
    ('organize_duplicate_mode', 'skip', 'string', 'organize', '重复文件处理模式：skip/update');
```

---

*文档版本: v1.0.0*
*更新日期: 2026-04-13*
