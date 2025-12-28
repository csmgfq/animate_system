from datetime import date, datetime
from bci_flask_services.db import db


class BaseModel:
    def to_dict(self):
        result = {}
        for column in self.__table__.columns:  # type: ignore[attr-defined]
            value = getattr(self, column.name)
            if isinstance(value, (datetime, date)):
                result[column.name] = value.isoformat()
            else:
                result[column.name] = value
        return result


class Dept(db.Model, BaseModel):
    __tablename__ = "dept"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255))
    create_time = db.Column(db.DateTime)
    update_time = db.Column(db.DateTime)


class Emp(db.Model, BaseModel):
    __tablename__ = "emp"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(255))
    password = db.Column(db.String(255))
    name = db.Column(db.String(255))
    gender = db.Column(db.SmallInteger)
    image = db.Column(db.String(512))
    job = db.Column(db.SmallInteger)
    entrydate = db.Column(db.Date)
    dept_id = db.Column(db.Integer, db.ForeignKey("dept.id"))
    create_time = db.Column(db.DateTime)
    update_time = db.Column(db.DateTime)


class Question(db.Model, BaseModel):
    __tablename__ = "question"

    id = db.Column(db.Integer, primary_key=True)
    # 视频推荐问卷字段（前端 video.vue 使用 season/movie/music）
    # 注意：历史表结构可能没有 season 列，应用启动时会尝试自动补齐。
    season = db.Column(db.String(255))
    music = db.Column(db.String(255))
    movie = db.Column(db.String(255))
    musicInstrument = db.Column(db.String(255))


class Music(db.Model, BaseModel):
    __tablename__ = "music_data"

    id = db.Column(db.Integer, primary_key=True)
    genre = db.Column(db.String(255))
    timbre = db.Column(db.String(255))
    description = db.Column(db.Text)
    file_path = db.Column(db.String(512))
    # 归属用户（用于按用户查询/权限控制）
    user_id = db.Column(db.Integer)
    user_account = db.Column(db.String(255))
    # 本项目在本地运行时按本地时间存储，避免数据库时间与本地显示相差 8 小时
    created_at = db.Column(db.DateTime, default=datetime.now)


class User(db.Model, BaseModel):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(255))
    gender = db.Column(db.String(50))
    occupation = db.Column(db.String(255))
    birthday = db.Column(db.String(50))
    phone = db.Column(db.String(50))
    email = db.Column(db.String(255))
    account = db.Column(db.String(255))
    password = db.Column(db.String(255))
    # 0/1 管理员标记
    is_admin = db.Column(db.SmallInteger, default=0)


class EegSession(db.Model, BaseModel):
    """EEG 录制会话记录"""
    __tablename__ = "eeg_session"

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(255), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    user_account = db.Column(db.String(255))
    # 会话目录路径
    session_dir = db.Column(db.String(512))
    # EEG 数据文件路径
    eeg_file = db.Column(db.String(512))
    # Trigger 数据文件路径
    trigger_file = db.Column(db.String(512))
    # 录制时长（秒）
    duration = db.Column(db.Float, default=0.0)
    # 采样点数
    samples = db.Column(db.Integer, default=0)
    # 开始/结束时间
    start_time = db.Column(db.DateTime)
    end_time = db.Column(db.DateTime)
    # 创建时间
    created_at = db.Column(db.DateTime, default=datetime.now)
