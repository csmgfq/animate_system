# Animate System

基于脑机接口(BCI)的智能动画与音乐生成系统。

## 项目简介

本项目是一个创新的多媒体交互系统，结合脑电信号(EEG)采集与分析、AI音乐生成等技术，为用户提供沉浸式的交互体验。

## 项目结构

```
animate_system/
├── animate/                 # Vue3 前端应用
│   ├── src/                # 源代码
│   ├── public/             # 静态资源
│   └── package.json        # 依赖配置
├── bci_flask_services/     # Flask 后端服务
│   ├── blueprints/         # API 蓝图模块
│   ├── core/               # 核心功能
│   └── app.py              # 应用入口
└── README.md               # 项目说明
```

## 主要功能

- **用户认证系统**: 注册、登录、用户管理
- **EEG 信号处理**: 脑电信号采集与分析
- **AI 音乐生成**: 基于 AudioCraft/MusicGen 的智能音乐创作
- **视频推荐**: 个性化内容推荐服务

## 技术栈

### 前端
- Vue 3
- Element Plus
- Vue Router
- Axios
- Capacitor (移动端支持)

### 后端
- Python Flask
- Flask-SQLAlchemy
- PyTorch
- AudioCraft (MusicGen)

## 快速开始

### 前端启动

```bash
cd animate
npm install
npm run serve
```

### 后端启动

```bash
cd bci_flask_services
pip install -r requirements.txt
python app.py
```

## 详细文档

- [前端文档](./animate/README.md)
- [后端文档](./bci_flask_services/README.md)

## License

MIT License
