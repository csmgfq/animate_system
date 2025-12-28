# BCI Flask Services 后端

基于 Flask Blueprint 的模块化后端服务。

## 项目结构

```
bci_flask_services/
├── app.py                    # 主应用入口
├── config.py                 # 配置管理
├── models.py                 # 数据模型
├── blueprints/               # 业务模块
│   ├── user_service.py       # 用户管理服务
│   ├── question_service.py   # 问卷管理服务
│   ├── music_service.py      # 音乐管理服务
│   ├── eeg_service.py        # 脑电设备连接服务
│   ├── music_gen_service.py  # AI 音乐生成服务
│   └── video_rec_service.py  # 视频推荐服务
└── requirements.txt
```

## 技术栈

- Flask 3.0.2
- Flask-SQLAlchemy
- PyTorch + AudioCraft (MusicGen)
- MySQL

## 快速启动

```bash
pip install -r requirements.txt
python app.py
```

访问：`http://localhost:8088`
