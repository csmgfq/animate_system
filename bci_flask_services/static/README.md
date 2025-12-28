# 静态文件目录

此目录用于存储应用生成的静态文件。

## 目录结构

```
static/
├── .gitignore          # Git 忽略规则
└── music/              # 音乐文件存储目录
    ├── .gitkeep        # 保持目录结构
    └── *.mp3           # 生成的音乐文件（被 .gitignore 忽略）
```

## 音乐文件命名规范

生成的音乐文件采用以下命名格式：

```
{genre}_{timbre}_{userId}_{timestamp}.mp3
```

**示例：**
- `rock_guitar_user123_20231224_143022.mp3`
- `jazz_piano_guest_20231224_150145.mp3`
- `classical_violin_user456_20231224_161230.mp3`

**字段说明：**
- `genre`: 音乐风格（rock, jazz, classical, etc.）
- `timbre`: 音色/乐器（guitar, piano, violin, etc.）
- `userId`: 用户ID（如果未提供则为 'guest'）
- `timestamp`: 生成时间（格式：YYYYMMDD_HHMMSS）

## 访问方式

### 前端访问

生成的音乐文件可以通过以下 URL 访问：

```
http://localhost:8088/static/music/{filename}
```

**示例：**
```javascript
// Vue3 组件中
const musicUrl = 'http://localhost:8088/static/music/rock_guitar_user123_20231224_143022.mp3'

// 使用 Audio 元素播放
const audio = new Audio(musicUrl)
audio.play()
```

### API 返回格式

生成音乐接口返回的数据包含完整的访问信息：

```json
{
  "message": "Music generated successfully",
  "data": {
    "id": 1,
    "genre": "rock",
    "timbre": "guitar",
    "description": "energetic rock music",
    "filePath": "music/rock_guitar_user123_20231224_143022.mp3",
    "fileName": "rock_guitar_user123_20231224_143022.mp3",
    "fileUrl": "/static/music/rock_guitar_user123_20231224_143022.mp3"
  }
}
```

## 数据库存储

音乐文件信息存储在 `music_data` 表中：

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键 |
| genre | String | 音乐风格 |
| timbre | String | 音色 |
| description | Text | 描述（英文翻译后） |
| file_path | String | 相对路径（如：`music/rock_guitar_user123_20231224_143022.mp3`） |

**注意：** 数据库中存储的是相对路径，不是绝对路径，便于部署迁移。

## 存储管理

### 清理旧文件

由于音乐文件较大，建议定期清理旧文件：

```bash
# Windows PowerShell
cd D:\vue_electron\animate\bci_flask_services\static\music

# 删除 7 天前的文件
Get-ChildItem -Filter *.mp3 | Where-Object {$_.LastWriteTime -lt (Get-Date).AddDays(-7)} | Remove-Item
```

```bash
# Linux/Mac
cd /path/to/bci_flask_services/static/music

# 删除 7 天前的文件
find . -name "*.mp3" -type f -mtime +7 -delete
```

### 磁盘空间监控

每个音乐文件约 2-5 MB，请定期监控磁盘使用情况：

```python
# 获取目录大小的 Python 脚本
import os
from pathlib import Path

music_dir = Path(__file__).parent / 'music'
total_size = sum(f.stat().st_size for f in music_dir.glob('*.mp3'))
print(f"音乐文件总大小: {total_size / (1024*1024):.2f} MB")
```

## 配置

音乐文件存储路径可以在 `config.py` 中配置：

```python
MUSIC_OUTPUT_FOLDER = Path(os.getenv(
    "MUSIC_OUTPUT_FOLDER",
    str(Path(__file__).parent / "static" / "music")
))
```

也可以通过环境变量覆盖：

```bash
export MUSIC_OUTPUT_FOLDER=/path/to/custom/music/folder
```

## 安全注意事项

1. **文件大小限制**: 确保有足够的磁盘空间
2. **访问控制**: 考虑添加用户认证来限制访问
3. **CORS 设置**: 已在 `app.py` 中配置 CORS，允许前端跨域访问
4. **文件清理**: 实施定期清理策略，避免磁盘空间耗尽
