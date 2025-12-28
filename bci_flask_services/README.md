# Flask 模块化单体应用

基于 Blueprint 的模块化架构，支持渐进式演进到微服务。

## 📋 架构设计

### 当前阶段：模块化单体应用

采用 Flask Blueprint 将业务拆分为独立模块，保持单一部署单元，便于后续拆分为微服务。

```
bci_flask_services/
├── app.py                    # 主应用入口
├── config.py                 # 配置管理
├── db.py                     # 数据库实例
├── models.py                 # 数据模型
├── blueprints/               # 业务模块（Blueprint）
│   ├── user_service.py       # ✅ 用户管理服务
│   ├── question_service.py   # ✅ 问卷管理服务
│   ├── music_service.py      # ✅ 音乐管理服务
│   ├── eeg_service.py        # ⏸️ 脑电读写服务（预留）
│   ├── inference_service.py  # ⏸️ 脑电推理服务（预留）
│   ├── music_gen_service.py  # ⏸️ 音乐生成服务（预留）
│   └── video_rec_service.py  # ⏸️ 视频推荐服务（预留）
└── requirements.txt
```

### 演进路径

1. **第一阶段（当前）**: 模块化单体应用
   - Blueprint 模块化架构
   - 共享数据库
   - 单一部署单元

2. **第二阶段**: 识别性能瓶颈
   - 监控各模块性能
   - 识别需要独立扩展的服务

3. **第三阶段**: 完整微服务架构
   - 拆分独立服务
   - 独立数据库
   - API 网关/服务发现

## 🚀 快速启动

### 1. 激活 Python 环境

```bash
conda activate BCIGame
```

### 2. 安装依赖

```bash
cd d:/tlias/tlias/bci_flask_services
pip install -r requirements.txt
```

### 3. 配置数据库

确保 MySQL 服务运行，并在 `config.py` 中配置：

```python
DB_HOST = "localhost"
DB_PORT = 3306
DB_USER = "root"
DB_PASSWORD = "root"
DB_NAME = "music_db"
```

### 4. 启动应用

```bash
python app.py
```

访问：`http://localhost:8088`

#### Windows 桌面端（内嵌窗口）

- 若已构建并拷贝前端 `dist` 到 `bci_flask_services/frontend_dist/`（存在 `frontend_dist/index.html`），Windows 下源码运行将默认打开桌面窗口，并默认绑定 `0.0.0.0` 以支持局域网访问。
- 也可显式指定：
  - 打开桌面窗口：`python app.py --desktop`
  - 仅启动服务：`python app.py --no-desktop`
  - 桌面窗口 + 局域网绑定：`python app.py --dual`

如果启动时“啥也没出现”，优先检查是否已安装依赖：`python -m pip install -r requirements.txt`

## 🧩 前后端合并为一个应用（Flask 托管 Vue3 dist）

核心思路：将前端 `animate` 构建为静态文件（`dist/`），拷贝到后端目录 `bci_flask_services/frontend_dist/`，由 Flask 直接托管。

### 1) 构建前端 dist

在仓库根目录执行：

```bash
cd animate
npm install
npm run build
```

### 2) 拷贝 dist 到后端约定目录

```bash
# Windows PowerShell
Remove-Item -Recurse -Force bci_flask_services\frontend_dist -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Path bci_flask_services\frontend_dist | Out-Null
Copy-Item -Recurse -Force animate\dist\* bci_flask_services\frontend_dist
```

### 3) 启动后端（同时提供前端页面）

```bash
cd bci_flask_services
python app.py
```

浏览器访问：`http://localhost:8088/`

说明：

- `frontend_dist` 存在时，Flask 会托管 `/` 与前端路由（history 模式兜底返回 `index.html`）。
- `/api/*` 与 `/static/*` 仍按原有后端逻辑处理；未命中的 API 会返回 JSON 404。
- 可通过环境变量 `FRONTEND_DIST_DIR` 覆盖前端 dist 目录位置。

## 🧱 Windows 打包为单文件 EXE（PyInstaller）

核心：用 PyInstaller 打包 Flask + 静态资源；通过 `--add-data` 将 `frontend_dist`（以及需要的 `static`）带进 EXE。

### 方式 A：直接命令打包（推荐先跑通）

```bash
pip install pyinstaller

# Windows 下 --add-data 使用 ; 分隔 "源;目标"
pyinstaller --noconfirm --clean --onefile --name bci_app ^
    --add-data "bci_flask_services\frontend_dist;bci_flask_services\frontend_dist" ^
    --add-data "bci_flask_services\static;bci_flask_services\static" ^
    bci_flask_services\app.py
```

产物：`dist/bci_app.exe`

### 方式 B：一键脚本

项目已提供 PowerShell 脚本：[bci_flask_services/packaging/build_windows_exe.ps1](bci_flask_services/packaging/build_windows_exe.ps1)

```powershell
powershell -ExecutionPolicy Bypass -File bci_flask_services\packaging\build_windows_exe.ps1
```

脚本参数（可选）：

- `-CondaEnvName bci`：指定用于打包的 conda 环境名（默认 `bci`）
- `-SkipFrontendBuild`：跳过 `npm run build`（你已手动 build 时用这个更快）
- `-OneFile`：打包为单文件 EXE（默认是 `onedir`，启动更快、调试更容易）
- `-IncludeMusicGen`：包含 MusicGen（会把 `torch/audiocraft` 等打进包，体积会很大）

轻量打包说明：默认不带 `-IncludeMusicGen` 时，会设置 `BCI_ENABLE_MUSICGEN=0`，后端不会注册 `/api/music-gen/*`，但 EXE 体积会显著降低。

完整打包说明（包含 MusicGen）：

- 运行脚本时加 `-IncludeMusicGen`，会额外收集 `audiocraft` 子模块，并把本地离线资源目录一起放进 onedir 产物（体积会明显变大）：
    - `bci_flask_services/audiocraft`
    - `bci_flask_services/musicgenmodel`
    - `bci_flask_services/hf_cache`

小包但可生成（推荐）：EXE 只带代码与前端静态资源，模型与缓存放在 EXE 同目录，通过 `MUSICGEN_MODEL_PATH` / `HF_HOME` 指向外置目录（或直接按默认目录名放置）。

默认约定（打包后 onedir）：

- 模型目录：`dist/bci_app/musicgenmodel/`（你把现有 `bci_flask_services/musicgenmodel` 复制到这里即可）
- 缓存目录：`dist/bci_app/hf_cache/`（可选；离线翻译/依赖模型会用到）

打包命令（onedir + 包含 MusicGen 代码，但不打包模型/缓存）：

```cmd
conda run -n bci python -m PyInstaller --noconfirm --clean --onedir --name bci_app --paths bci_flask_services\audiocraft --collect-submodules audiocraft --add-data "bci_flask_services\frontend_dist;bci_flask_services\frontend_dist" --add-data "bci_flask_services\static;bci_flask_services\static" --add-data "bci_flask_services\audiocraft;bci_flask_services\audiocraft" bci_flask_services\app.py
```

如你确实要把模型/缓存也打进包（非常大），再用脚本加 `-BundleModels`。

示例（onedir，推荐）：

```powershell
powershell -ExecutionPolicy Bypass -File bci_flask_services\packaging\build_windows_exe.ps1 -SkipFrontendBuild -CondaEnvName bci -IncludeMusicGen
```

### 性能/体积注意事项

- 生产运行建议关闭调试：不要设置 `FLASK_DEBUG=1`（默认是关闭的）。
- PyInstaller 单文件 EXE 会在启动时解压到临时目录，首次启动会比 onedir 慢一些；如更关注启动速度，可改用 onedir 模式。
- MusicGen/HF 模型与缓存通常体积很大，不建议打进 onefile；更建议通过外置目录 + 环境变量（如 `HF_HOME`、`MUSICGEN_MODEL_PATH`）挂载/指定。

## 📡 API 端点

### 系统端点

- `GET /health` - 健康检查
- `GET /api/services` - 服务发现（列出所有模块）

### 用户管理服务 (`/api/users`)

- `GET /api/users/info` - 查询所有用户基本信息
- `GET /api/users?page=1&pageSize=10` - 分页查询用户
- `POST /api/users` - 新增用户
- `PUT /api/users/<id>` - 更新用户
- `DELETE /api/users/<ids>` - 批量删除（逗号分隔ID）

### 问卷管理服务 (`/api/question`)

- `GET /api/question` - 查询所有问卷
- `POST /api/question` - 更新问卷

### 音乐管理服务 (`/api/music`)

- `GET /api/music` - 查询所有音乐
- `POST /api/music` - 更新音乐信息

### 预留服务（返回健康状态）

- `GET /api/eeg/health` - 脑电读写服务
- `GET /api/inference/health` - 脑电推理服务
- `GET /api/music-gen/health` - 音乐生成服务
- `GET /api/video-rec/health` - 视频推荐服务

## 🔧 模块化优势

### 1. 代码组织清晰
每个 Blueprint 独立管理自己的路由和业务逻辑，职责明确。

### 2. 易于测试
可以独立测试每个 Blueprint 模块。

### 3. 渐进式演进
需要时可将 Blueprint 拆分为独立微服务，无需重写业务逻辑。

### 4. 团队协作友好
不同团队可并行开发不同模块，减少代码冲突。

## 📦 技术栈

- **Web 框架**: Flask 3.0.2
- **ORM**: Flask-SQLAlchemy 3.1.1
- **数据库驱动**: PyMySQL 1.1.0
- **跨域支持**: Flask-Cors 4.0.0
- **数据库**: MySQL 8.0.40

## 🔮 未来扩展

### 异步任务处理（规划中）

使用 Celery 处理耗时任务（如音乐生成、深度推理）：

```python
from celery import Celery

celery = Celery(app.name, broker='redis://localhost:6379')

@celery.task
def generate_music_task(params):
    # 异步音乐生成
    pass
```

### 微服务拆分示例（规划中）

将脑电推理服务拆分为独立服务：

```python
# inference_service/ (独立项目)
from flask import Flask
app = Flask(__name__)

@app.route("/predict", methods=["POST"])
def predict():
    # 独立的推理服务
    pass
```

## 📝 开发指南

### 添加新的 Blueprint 模块

1. 在 `blueprints/` 创建新文件：

```python
# blueprints/new_service.py
from flask import Blueprint, jsonify

new_bp = Blueprint('new_service', __name__)

@new_bp.route("/endpoint", methods=["GET"])
def handler():
    return jsonify({"status": "ok"})
```

2. 在 `app.py` 中注册：

```python
from bci_flask_services.blueprints.new_service import new_bp
app.register_blueprint(new_bp, url_prefix='/api/new')
```

### 数据库迁移

如需修改表结构，建议使用 Flask-Migrate：

```bash
pip install Flask-Migrate
flask db init
flask db migrate -m "描述"
flask db upgrade
```

## 🐛 故障排查

### 导入错误
确保 Python 路径正确，`sys.path` 包含项目根目录。

### 数据库连接失败
- 检查 MySQL 服务状态
- 验证 `config.py` 中的数据库配置
- 确保 `music_db` 数据库已创建

### 模块未找到
激活正确的 Conda 环境：
```bash
conda activate BCIGame
```

## 📄 许可证

MIT
