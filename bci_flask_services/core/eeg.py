"""
EEG 设备连接核心模块
提供脑电设备连接、数据解析、缓冲和存储的核心功能

架构设计：
- 使用独立线程处理设备连接和数据接收，不阻塞 Flask 主线程
- 双缓冲机制：实时数据写入内存缓冲，异步写入磁盘
- 丢包补偿：检测序列号跳跃，用前一帧数据填充丢失帧
"""

import time
import h5py
import socket
import threading
import queue
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Union, Any, Callable
import numpy as np

StrPath = Union[str, Path]

# ============================================
# EEG 设备协议常量
# ============================================
EEG_DEVICE_CHANNELS = 32
EEG_DEVICE_BYTES_PER_CHANNEL = 3
EEG_BOX_START_BYTES = b"\xA1\x05"
TRIGGER_BOX_START_BYTES = b"\xAA\x56"
EEG_DEVICE_START_INSTRUCTION = b"\xBB\x66\x01"

# 全局连接状态
EEG_CONNECTED = False
TRIGGER_CONNECTED = False


class RealtimeStats:
    """
    线程安全的实时统计容器
    用于跟踪 EEG/Trigger 数据接收状态和丢包率
    """
    def __init__(self):
        self.lock = threading.Lock()
        # EEG 统计
        self.eeg_seq = 0
        self.eeg_received = 0
        self.eeg_loss_rate = 0.0
        self.eeg_supplement = 0
        self.eeg_connected = False
        self.eeg_first_packet = False
        self.eeg_first_seq = None
        # Trigger 统计
        self.trigger_seq = 0
        self.trigger_received = 0
        self.trigger_loss_rate = 0.0
        self.trigger_supplement = 0
        self.trigger_connected = False
        self.trigger_first_packet = False
        self.trigger_first_seq = None
        self.last_trigger_value = 0
        # 会话信息
        self.recording = False
        self.session_id = ""
        self.start_time = None

    def update_eeg(self, seq: int, received: int, supplement: int = 0):
        """更新 EEG 统计信息"""
        with self.lock:
            self.eeg_seq = seq
            self.eeg_received = received
            self.eeg_supplement = supplement
            if self.eeg_first_seq is None:
                self.eeg_first_seq = seq
            total_expected = received + supplement
            self.eeg_loss_rate = 100 * (supplement / total_expected) if total_expected > 0 else 0
            self.eeg_first_packet = True

    def update_trigger(self, seq: int, received: int, supplement: int = 0, trigger_value: Optional[int] = None):
        """更新 Trigger 统计信息"""
        with self.lock:
            self.trigger_seq = seq
            self.trigger_received = received
            self.trigger_supplement = supplement
            if self.trigger_first_seq is None:
                self.trigger_first_seq = seq
            total_expected = received + supplement
            self.trigger_loss_rate = 100 * (supplement / total_expected) if total_expected > 0 else 0
            if trigger_value is not None and trigger_value != 0:
                self.last_trigger_value = trigger_value
            self.trigger_first_packet = True

    def get_stats(self) -> dict:
        """获取当前统计快照"""
        with self.lock:
            duration = 0.0
            if self.start_time:
                duration = time.time() - self.start_time
            return {
                "eeg": {
                    "connected": self.eeg_connected,
                    "sequence": self.eeg_seq,
                    "received": self.eeg_received,
                    "loss_rate": round(self.eeg_loss_rate, 4),
                    "supplement": self.eeg_supplement,
                },
                "trigger": {
                    "connected": self.trigger_connected,
                    "sequence": self.trigger_seq,
                    "received": self.trigger_received,
                    "loss_rate": round(self.trigger_loss_rate, 4),
                    "supplement": self.trigger_supplement,
                    "last_value": self.last_trigger_value,
                },
                "recording": self.recording,
                "session_id": self.session_id,
                "duration": round(duration, 2),
            }

    def reset(self):
        """重置所有统计"""
        with self.lock:
            self.eeg_seq = 0
            self.eeg_received = 0
            self.eeg_loss_rate = 0.0
            self.eeg_supplement = 0
            self.eeg_first_packet = False
            self.eeg_first_seq = None
            self.trigger_seq = 0
            self.trigger_received = 0
            self.trigger_loss_rate = 0.0
            self.trigger_supplement = 0
            self.trigger_first_packet = False
            self.trigger_first_seq = None
            self.last_trigger_value = 0
            self.recording = False
            self.session_id = ""
            self.start_time = None


# 全局统计实例
realtime_stats = RealtimeStats()


class FrameParser:
    """
    基于状态机的 EEG/Trigger 数据帧解析器

    协议结构：
        [START_BYTES][RESERVED][PACKET_INDEX][DATA]
        - START_BYTES: 2字节设备标识 (0xA1 0x05 EEG, 0xAA 0x56 Trigger)
        - RESERVED: 1字节 (Trigger模式为触发值，EEG模式为0)
        - PACKET_INDEX: 4字节无符号大端整数
        - DATA: EEG 96字节 (32通道×3字节), Trigger 3字节
    """

    def __init__(self, start_bytes: bytes):
        self.state = "WAITING_FOR_HEADER"
        self.start_bytes = start_bytes
        self.len_start_bytes = len(start_bytes)
        self.len_reserved_bytes = 1
        self.len_packet_index = 4
        self.trigger = 0

        if self.start_bytes == EEG_BOX_START_BYTES:
            self.mode = "EEG"
            self.len_data = EEG_DEVICE_CHANNELS * EEG_DEVICE_BYTES_PER_CHANNEL
        elif self.start_bytes == TRIGGER_BOX_START_BYTES:
            self.mode = "TRIGGER"
            self.len_data = EEG_DEVICE_BYTES_PER_CHANNEL
        else:
            raise ValueError("Invalid start bytes")

        self.recv_buffer = bytearray()
        self.sequence = []
        self.num_channels = EEG_DEVICE_CHANNELS
        self.data = np.zeros(shape=self.num_channels, dtype=np.int32)
        self.packet_count = 0

    def process_byte(self, byte: int):
        """处理单个字节，返回完整帧或 None"""
        result = None

        if self.state == "WAITING_FOR_HEADER":
            self.recv_buffer.append(byte)
            if len(self.recv_buffer) == self.len_start_bytes and self.recv_buffer == self.start_bytes:
                self.state = "WAITING_FOR_RESERVED"
                self.recv_buffer.clear()
            else:
                del self.recv_buffer[:-(self.len_start_bytes - 1)]

        elif self.state == "WAITING_FOR_RESERVED":
            self.recv_buffer.append(byte)
            if len(self.recv_buffer) == self.len_reserved_bytes:
                if self.mode == "EEG":
                    self.trigger = 0
                elif self.mode == "TRIGGER":
                    self.trigger = int.from_bytes(self.recv_buffer, byteorder='big', signed=False)
                self.state = "WAITING_FOR_INDEX"
                self.recv_buffer.clear()

        elif self.state == "WAITING_FOR_INDEX":
            self.recv_buffer.append(byte)
            if len(self.recv_buffer) == self.len_packet_index:
                packet_index = int.from_bytes(self.recv_buffer, byteorder='big', signed=False)
                self.sequence.append(packet_index)
                self.packet_count += 1
                self.state = "WAITING_FOR_DATA"
                self.recv_buffer.clear()

        elif self.state == "WAITING_FOR_DATA":
            self.recv_buffer.append(byte)
            if len(self.recv_buffer) == self.len_data:
                if self.mode == "EEG":
                    for ch in range(self.num_channels):
                        encoded_data = self.recv_buffer[ch * 3: (ch + 1) * 3]
                        encoded_data[0] ^= 0x80
                        decoded_data = int.from_bytes(encoded_data, byteorder='big', signed=False) - 8388608
                        decoded_data = decoded_data * 0.02483  # uV
                        self.data[ch] = decoded_data
                    result = (self.mode, self.sequence[-1], self.data.copy())
                elif self.mode == "TRIGGER":
                    result = (self.mode, self.sequence[-1], self.trigger)

                self.recv_buffer.clear()
                self.state = "WAITING_FOR_HEADER"

        return result

    def process_bytes(self, client_socket: socket.socket):
        """从 socket 持续读取直到获得完整帧"""
        while True:
            frame = self.process_byte(client_socket.recv(1)[0])
            if frame is not None:
                return frame


class StreamBuffer:
    """
    线程安全的双缓冲系统，用于实时数据流

    架构：
        生产者(实时线程) -> write_buffer -> data_queue -> 消费者(写入线程)

    关键设计：
        - 非阻塞写入：队列满时丢弃数据而非阻塞，保证实时性
        - 固定大小块：数据按 buffer_size 打包，优化磁盘 I/O
    """

    def __init__(self, num_channels: int = EEG_DEVICE_CHANNELS, buffer_size: int = 1000):
        self.num_channels = num_channels
        self.buffer_size = buffer_size
        self.write_buffer = np.empty((self.num_channels, self.buffer_size), dtype=np.float32)
        self.write_idx = 0
        self.data_queue = queue.Queue(maxsize=100)
        self.total_samples = 0
        self.lock = threading.Lock()

    def write(self, data: np.ndarray):
        """写入单个样本（线程安全）"""
        with self.lock:
            if data.ndim == 1:
                if len(data) == self.num_channels:
                    self.write_buffer[:, self.write_idx] = data
                else:
                    self.write_buffer[0, self.write_idx] = data[0] if len(data) > 0 else 0
            else:
                self.write_buffer[:, self.write_idx] = data.flatten()[:self.num_channels]

            self.write_idx += 1
            self.total_samples += 1

            if self.write_idx >= self.buffer_size:
                data_chunk = self.write_buffer.copy()
                try:
                    self.data_queue.put((data_chunk, self.total_samples), block=False)
                except queue.Full:
                    pass  # 丢弃数据，避免阻塞实时线程
                self.write_idx = 0

    def read_chunk(self, timeout: float = 1.0):
        """读取完整数据块（消费者端）"""
        try:
            return self.data_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def get_current_data(self, last_n_samples: Optional[int] = None):
        """获取当前缓冲数据副本"""
        with self.lock:
            if last_n_samples is None or last_n_samples >= self.write_idx:
                return self.write_buffer[:, :self.write_idx].copy()
            else:
                start_idx = max(0, self.write_idx - last_n_samples)
                return self.write_buffer[:, start_idx:self.write_idx].copy()


class StreamWriter:
    """
    HDF5 文件流式写入器

    特点：
        - 可扩展数据集：支持无限追加
        - gzip 压缩：减少磁盘占用
        - 线程安全：使用锁保护写入操作
    """

    def __init__(self, save_dir: StrPath, file_prefix: str = "eeg_data"):
        self.save_dir = Path(save_dir)
        if not self.save_dir.exists():
            self.save_dir.mkdir(parents=True, exist_ok=True)
        self.file_prefix = file_prefix

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.eeg_file = self.save_dir / f"{self.file_prefix}_eeg_{timestamp}.h5"
        self.trigger_file = self.save_dir / f"{self.file_prefix}_trigger_{timestamp}.h5"

        self.eeg_h5 = h5py.File(self.eeg_file, "w")
        self.trigger_h5 = h5py.File(self.trigger_file, "w")

        self.eeg_dataset = self.eeg_h5.create_dataset(
            "eeg_data",
            shape=(EEG_DEVICE_CHANNELS, 0),
            maxshape=(EEG_DEVICE_CHANNELS, None),
            dtype=np.float32,
            chunks=(EEG_DEVICE_CHANNELS, 1000),
            compression="gzip"
        )

        self.trigger_dataset = self.trigger_h5.create_dataset(
            "trigger_data",
            shape=(0,),
            maxshape=(None,),
            dtype=np.int32,
            chunks=(1000,),
            compression="gzip"
        )

        self.running = False
        self.lock = threading.Lock()

    def write_eeg_chunk(self, data_chunk: np.ndarray):
        """写入 EEG 数据块"""
        with self.lock:
            current_size = self.eeg_dataset.shape[1]
            new_size = current_size + data_chunk.shape[1]
            self.eeg_dataset.resize((EEG_DEVICE_CHANNELS, new_size))
            self.eeg_dataset[:, current_size:new_size] = data_chunk
            self.eeg_h5.flush()

    def write_trigger_chunk(self, data_chunk: np.ndarray):
        """写入 Trigger 数据块"""
        with self.lock:
            current_size = self.trigger_dataset.shape[0]
            new_size = current_size + data_chunk.shape[0]
            self.trigger_dataset.resize((new_size,))
            self.trigger_dataset[current_size:new_size] = data_chunk
            self.trigger_h5.flush()

    def close(self):
        """关闭 HDF5 文件"""
        with self.lock:
            try:
                self.eeg_h5.close()
                self.trigger_h5.close()
            except Exception:
                pass


class SessionManager:
    """
    EEG 录制会话管理器

    职责：
        - 会话生命周期管理（开始/停止录制）
        - 缓冲区和写入器协调
        - 元数据跟踪和统计
    """

    def __init__(self, save_dir: StrPath):
        self.save_dir = Path(save_dir)
        if not self.save_dir.exists():
            self.save_dir.mkdir(parents=True, exist_ok=True)

        self.current_session = None
        self.is_recording = False
        self.sessions = []

        self.eeg_buffer = None
        self.trigger_buffer = None
        self.writer = None
        self.writer_thread = None

        self.stats = {
            "total_samples": 0,
            "recording_duration": 0.0,
            "start_time": None,
            "packets_received": 0,
            "packets_dropped": 0,
        }
        self.lock = threading.Lock()

    def start_new_session(self, user_id=None, user_account=None):
        """开始新的录制会话（支持用户关联）"""
        with self.lock:
            if self.is_recording:
                return False, "Already recording"

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            session_id = f"session_{timestamp}"

            # 按用户目录保存
            if user_account:
                session_dir = self.save_dir / user_account / session_id
            else:
                session_dir = self.save_dir / session_id
            session_dir.mkdir(parents=True, exist_ok=True)

            self.current_session = {
                "id": session_id,
                "dir": session_dir,
                "start_time": datetime.now().isoformat(),
                "end_time": None,
                "samples": 0,
                "user_id": user_id,
                "user_account": user_account,
            }

            self.eeg_buffer = StreamBuffer(num_channels=EEG_DEVICE_CHANNELS, buffer_size=1000)
            self.trigger_buffer = StreamBuffer(num_channels=1, buffer_size=1000)
            self.writer = StreamWriter(save_dir=session_dir, file_prefix="eeg_data")
            self.writer.running = True

            self.writer_thread = threading.Thread(
                target=_stream_writer_thread,
                args=(self.eeg_buffer, self.trigger_buffer, self.writer, self)
            )
            self.writer_thread.daemon = True
            self.writer_thread.start()

            self.is_recording = True
            self.stats["start_time"] = time.time()
            self.stats["total_samples"] = 0
            self.stats["packets_received"] = 0
            self.stats["packets_dropped"] = 0

            realtime_stats.recording = True
            realtime_stats.session_id = session_id
            realtime_stats.start_time = time.time()

            return True, session_id

    def stop_session(self):
        """停止当前录制会话"""
        with self.lock:
            if not self.is_recording:
                return False, "Not recording"

            session_id = self.current_session["id"] if self.current_session else None
            if self.writer:
                self.writer.running = False
            self.is_recording = False

        # 在锁外等待写入线程结束，避免死锁
        if self.writer_thread:
            self.writer_thread.join(timeout=5.0)

        with self.lock:
            self._flush_remaining_data()

            if self.writer:
                self.writer.close()

            if self.current_session:
                self.current_session["end_time"] = datetime.now().isoformat()
                self.current_session["samples"] = self.stats["total_samples"]
                duration = time.time() - self.stats["start_time"] if self.stats["start_time"] else 0.0
                self.current_session["duration"] = duration
                self.sessions.append(self.current_session)

                # 保存元数据
                meta_file = self.current_session["dir"] / "metadata.json"
                session_data = {
                    "id": self.current_session["id"],
                    "dir": str(self.current_session["dir"]),
                    "start_time": self.current_session["start_time"],
                    "end_time": self.current_session["end_time"],
                    "samples": self.current_session["samples"],
                    "duration": self.current_session["duration"]
                }
                with open(meta_file, "w") as f:
                    json.dump(session_data, f, indent=2, ensure_ascii=False)

            self.stats["recording_duration"] = time.time() - self.stats["start_time"] if self.stats["start_time"] else 0.0
            self.current_session = None
            self.eeg_buffer = None
            self.trigger_buffer = None
            self.writer = None

            realtime_stats.recording = False

            return True, session_id

    def _flush_remaining_data(self):
        """刷新剩余缓冲数据"""
        if self.eeg_buffer and self.eeg_buffer.write_idx > 0 and self.writer:
            remaining = self.eeg_buffer.write_buffer[:, :self.eeg_buffer.write_idx].copy()
            if remaining.shape[1] > 0:
                self.writer.write_eeg_chunk(remaining)

        if self.trigger_buffer and self.trigger_buffer.write_idx > 0 and self.writer:
            remaining = self.trigger_buffer.write_buffer[:, :self.trigger_buffer.write_idx].copy()
            if remaining.shape[1] > 0:
                self.writer.write_trigger_chunk(remaining.flatten().astype(np.int32))

    def get_status(self) -> dict:
        """获取当前状态"""
        with self.lock:
            duration = 0.0
            if self.is_recording and self.stats["start_time"]:
                duration = time.time() - self.stats["start_time"]

            return {
                "is_recording": self.is_recording,
                "current_session": self.current_session["id"] if self.current_session else None,
                "session_dir": str(self.current_session["dir"]) if self.current_session else None,
                "eeg_connected": EEG_CONNECTED,
                "trigger_connected": TRIGGER_CONNECTED,
                "total_samples": self.stats["total_samples"],
                "recording_duration": round(duration, 2),
                "packets_received": self.stats["packets_received"],
                "packets_dropped": self.stats["packets_dropped"],
                "queue_size": self.eeg_buffer.data_queue.qsize() if self.eeg_buffer else 0
            }

    def get_sessions(self) -> list:
        """获取所有会话列表"""
        return self.sessions


def _stream_writer_thread(eeg_buffer: StreamBuffer, trigger_buffer: StreamBuffer,
                          writer: StreamWriter, session_manager: SessionManager):
    """后台写入线程：从缓冲区读取数据并写入磁盘"""
    while writer.running:
        # 轮询 EEG 缓冲区
        eeg_chunk = eeg_buffer.read_chunk(timeout=0.5)
        if eeg_chunk is not None:
            data, total_samples = eeg_chunk
            writer.write_eeg_chunk(data)
            with session_manager.lock:
                session_manager.stats["total_samples"] = total_samples

        # 轮询 Trigger 缓冲区
        trigger_chunk = trigger_buffer.read_chunk(timeout=0.1)
        if trigger_chunk is not None:
            data, _ = trigger_chunk
            writer.write_trigger_chunk(data.flatten().astype(np.int32))


def _handle_eeg_client(client_socket: socket.socket, session_manager: SessionManager,
                       eeg_device_ip: str):
    """处理 EEG 设备连接"""
    global EEG_CONNECTED
    EEG_CONNECTED = True
    realtime_stats.eeg_connected = True

    eeg_parser = FrameParser(start_bytes=EEG_BOX_START_BYTES)
    last_packet_index = None
    supplement_count = 0
    received_count = 0
    last_data = None
    update_interval = 2000

    try:
        while True:
            result = eeg_parser.process_bytes(client_socket)
            current_index = result[1]
            current_data = result[2]
            received_count += 1

            if session_manager.is_recording and session_manager.eeg_buffer:
                # 丢包补偿：用前一帧数据填充
                if last_packet_index is not None:
                    missing = current_index - last_packet_index - 1
                    if missing > 0 and last_data is not None:
                        for _ in range(missing):
                            session_manager.eeg_buffer.write(last_data)
                        supplement_count += missing

                session_manager.eeg_buffer.write(current_data)
                session_manager.stats["packets_received"] += 1

            last_packet_index = current_index
            last_data = current_data.copy()

            if received_count % update_interval == 0:
                realtime_stats.update_eeg(current_index, received_count, supplement_count)

    except Exception:
        pass
    finally:
        EEG_CONNECTED = False
        realtime_stats.eeg_connected = False
        client_socket.close()


def _handle_trigger_client(client_socket: socket.socket, session_manager: SessionManager,
                           trigger_device_ip: str):
    """处理 Trigger 设备连接"""
    global TRIGGER_CONNECTED
    TRIGGER_CONNECTED = True
    realtime_stats.trigger_connected = True

    trigger_parser = FrameParser(start_bytes=TRIGGER_BOX_START_BYTES)
    last_packet_index = None
    supplement_count = 0
    received_count = 0
    update_interval = 2000

    try:
        while True:
            result = trigger_parser.process_bytes(client_socket)
            current_index = result[1]
            current_trigger = result[2]
            received_count += 1

            if session_manager.is_recording and session_manager.trigger_buffer:
                # 丢包补偿：用 0 填充
                if last_packet_index is not None:
                    missing = current_index - last_packet_index - 1
                    if missing > 0:
                        for _ in range(missing):
                            session_manager.trigger_buffer.write(np.array([0], dtype=np.float32))
                        supplement_count += missing

                session_manager.trigger_buffer.write(np.array([current_trigger], dtype=np.float32))

            last_packet_index = current_index

            if current_trigger != 0:
                realtime_stats.last_trigger_value = current_trigger

            if received_count % update_interval == 0:
                realtime_stats.update_trigger(current_index, received_count, supplement_count)

    except Exception:
        pass
    finally:
        TRIGGER_CONNECTED = False
        realtime_stats.trigger_connected = False
        client_socket.close()


def send_start_instruction(host_ip: str, eeg_ip: str, trigger_ip: str, port: int = 8080):
    """发送 UDP 启动指令到设备"""
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    try:
        udp_socket.bind((host_ip, 0))
    except Exception:
        pass

    # 发送到广播地址和各设备
    broadcast = ".".join(host_ip.split(".")[:3]) + ".255"
    for target in [broadcast, eeg_ip, trigger_ip]:
        try:
            udp_socket.sendto(EEG_DEVICE_START_INSTRUCTION, (target, port))
        except Exception:
            pass

    udp_socket.close()


class EEGDeviceServer:
    """
    EEG 设备 TCP 服务器管理器

    在后台线程运行，不阻塞 Flask 主线程
    """

    def __init__(self, host_ip: str, port: int, eeg_ip: str, trigger_ip: str,
                 session_manager: SessionManager):
        self.host_ip = host_ip
        self.port = port
        self.eeg_ip = eeg_ip
        self.trigger_ip = trigger_ip
        self.session_manager = session_manager
        self.server_socket = None
        self.running = False
        self.server_thread = None

    def start(self):
        """启动 TCP 服务器（后台线程）"""
        if self.running:
            return False, "Server already running"

        self.running = True
        self.server_thread = threading.Thread(target=self._run_server, daemon=True)
        self.server_thread.start()
        return True, f"Server started on {self.host_ip}:{self.port}"

    def stop(self):
        """停止 TCP 服务器"""
        if not self.running:
            return False, "Server not running"

        self.running = False
        if self.server_socket:
            try:
                self.server_socket.close()
            except Exception:
                pass
        return True, "Server stopped"

    def send_start_cmd(self):
        """发送启动指令到设备"""
        for _ in range(5):
            send_start_instruction(self.host_ip, self.eeg_ip, self.trigger_ip)
            time.sleep(0.1)

    def _run_server(self):
        """TCP 服务器主循环"""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1024 * 1024)
        self.server_socket.settimeout(1.0)

        try:
            self.server_socket.bind((self.host_ip, self.port))
            self.server_socket.listen(2)
        except Exception as e:
            self.running = False
            return

        while self.running:
            try:
                client_socket, client_address = self.server_socket.accept()
                client_ip = client_address[0]

                # 发送启动指令
                self.send_start_cmd()

                # 根据 IP 分发到对应处理器
                if client_ip == self.eeg_ip:
                    t = threading.Thread(
                        target=_handle_eeg_client,
                        args=(client_socket, self.session_manager, self.eeg_ip),
                        daemon=True
                    )
                    t.start()
                elif client_ip == self.trigger_ip:
                    t = threading.Thread(
                        target=_handle_trigger_client,
                        args=(client_socket, self.session_manager, self.trigger_ip),
                        daemon=True
                    )
                    t.start()
                else:
                    client_socket.close()

            except socket.timeout:
                continue
            except Exception:
                if self.running:
                    continue
                break

        try:
            self.server_socket.close()
        except Exception:
            pass
