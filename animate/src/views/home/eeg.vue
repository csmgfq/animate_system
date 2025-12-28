<template>
  <div class="eeg-control">
    <el-card class="status-card">
      <template #header>
        <div class="card-header">
          <span>脑电设备状态</span>
          <el-button type="primary" size="small" @click="refreshStatus">
            刷新
          </el-button>
        </div>
      </template>

      <el-descriptions :column="2" border>
        <el-descriptions-item label="EEG 设备">
          <el-tag :type="status.eeg_connected ? 'success' : 'danger'">
            {{ status.eeg_connected ? '已连接' : '未连接' }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="Trigger 设备">
          <el-tag :type="status.trigger_connected ? 'success' : 'danger'">
            {{ status.trigger_connected ? '已连接' : '未连接' }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="服务器状态">
          <el-tag :type="status.server_running ? 'success' : 'info'">
            {{ status.server_running ? '运行中' : '已停止' }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="录制状态">
          <el-tag :type="status.recording ? 'warning' : 'info'">
            {{ status.recording ? '录制中' : '空闲' }}
          </el-tag>
        </el-descriptions-item>
      </el-descriptions>
    </el-card>

    <!-- 控制按钮 -->
    <el-card class="control-card">
      <template #header>
        <span>设备控制</span>
      </template>

      <el-space wrap>
        <el-button
          type="primary"
          @click="startServer"
        >
          启动服务器
        </el-button>
        <el-button
          type="danger"
          @click="stopServer"
        >
          停止服务器
        </el-button>
        <el-button
          type="warning"
          @click="sendStartCmd"
          :disabled="!status.server_running"
        >
          发送启动指令
        </el-button>
      </el-space>
    </el-card>

    <!-- 录制控制 -->
    <el-card class="record-card">
      <template #header>
        <span>录制控制</span>
      </template>

      <el-space wrap>
        <el-button
          type="success"
          size="large"
          @click="startRecording"
          :disabled="status.recording || !status.server_running"
        >
          <el-icon><VideoPlay /></el-icon>
          开始录制
        </el-button>
        <el-button
          type="danger"
          size="large"
          @click="stopRecording"
          :disabled="!status.recording"
        >
          <el-icon><VideoPause /></el-icon>
          停止录制
        </el-button>
      </el-space>

      <div v-if="status.recording" class="recording-info">
        <el-tag type="warning" effect="dark" size="large">
          录制中: {{ status.session_id }}
        </el-tag>
        <p>时长: {{ formatDuration(status.duration) }}</p>
      </div>
    </el-card>

    <!-- 实时统计 -->
    <el-card v-if="realtime" class="stats-card">
      <template #header>
        <span>实时统计</span>
      </template>

      <el-row :gutter="20">
        <el-col :span="12">
          <el-statistic title="EEG 接收包数" :value="realtime.eeg?.received || 0" />
        </el-col>
        <el-col :span="12">
          <el-statistic title="EEG 丢包率" :value="realtime.eeg?.loss_rate || 0" suffix="%" />
        </el-col>
        <el-col :span="12">
          <el-statistic title="Trigger 接收包数" :value="realtime.trigger?.received || 0" />
        </el-col>
        <el-col :span="12">
          <el-statistic title="最后触发值" :value="realtime.trigger?.last_value || 0" />
        </el-col>
      </el-row>
    </el-card>
  </div>
</template>

<script>
import { VideoPlay, VideoPause } from '@element-plus/icons-vue'
import { getApiBaseUrl } from '@/api/baseUrl'

export default {
  name: 'EegControl',
  components: { VideoPlay, VideoPause },
  data() {
    return {
      status: {
        eeg_connected: false,
        trigger_connected: false,
        server_running: false,
        recording: false,
        session_id: '',
        duration: 0
      },
      realtime: null,
      pollTimer: null
    }
  },
  mounted() {
    this.refreshStatus()
    this.startPolling()
  },
  beforeUnmount() {
    this.stopPolling()
  },
  methods: {
    async refreshStatus() {
      try {
        const res = await fetch(`${getApiBaseUrl()}/api/eeg/status`)
        const data = await res.json()
        if (data.code === 1) {
          this.status = {
            eeg_connected: data.data.realtime?.eeg?.connected || false,
            trigger_connected: data.data.realtime?.trigger?.connected || false,
            server_running: data.data.server_running || false,
            recording: data.data.realtime?.recording || false,
            session_id: data.data.realtime?.session_id || '',
            duration: data.data.realtime?.duration || 0
          }
          this.realtime = data.data.realtime
        }
      } catch (e) {
        console.error('获取状态失败:', e)
      }
    },
    startPolling() {
      this.pollTimer = setInterval(() => this.refreshStatus(), 2000)
    },
    stopPolling() {
      if (this.pollTimer) {
        clearInterval(this.pollTimer)
        this.pollTimer = null
      }
    },
    async startServer() {
      try {
        const res = await fetch(`${getApiBaseUrl()}/api/eeg/server/start`, { method: 'POST' })
        const data = await res.json()
        this.$message({ type: data.code ? 'success' : 'error', message: data.msg })
        this.refreshStatus()
      } catch (e) {
        this.$message.error('启动服务器失败')
      }
    },
    async stopServer() {
      try {
        const res = await fetch(`${getApiBaseUrl()}/api/eeg/server/stop`, { method: 'POST' })
        const data = await res.json()
        this.$message({ type: data.code ? 'success' : 'error', message: data.msg })
        this.refreshStatus()
      } catch (e) {
        this.$message.error('停止服务器失败')
      }
    },
    async sendStartCmd() {
      try {
        const res = await fetch(`${getApiBaseUrl()}/api/eeg/server/send-start-cmd`, { method: 'POST' })
        const data = await res.json()
        this.$message({ type: data.code ? 'success' : 'error', message: data.msg })
      } catch (e) {
        this.$message.error('发送指令失败')
      }
    },
    async startRecording() {
      const userInfo = JSON.parse(localStorage.getItem('userInfo') || '{}')
      try {
        const res = await fetch(`${getApiBaseUrl()}/api/eeg/recording/start`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            user_id: userInfo.id,
            user_account: userInfo.account
          })
        })
        const data = await res.json()
        this.$message({ type: data.code ? 'success' : 'error', message: data.msg })
        this.refreshStatus()
      } catch (e) {
        this.$message.error('开始录制失败')
      }
    },
    async stopRecording() {
      try {
        const res = await fetch(`${getApiBaseUrl()}/api/eeg/recording/stop`, { method: 'POST' })
        const data = await res.json()
        this.$message({ type: data.code ? 'success' : 'error', message: data.msg })
        this.refreshStatus()
      } catch (e) {
        this.$message.error('停止录制失败')
      }
    },
    formatDuration(seconds) {
      const mins = Math.floor(seconds / 60)
      const secs = Math.floor(seconds % 60)
      return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
    }
  }
}
</script>

<style scoped>
.eeg-control {
  padding: 20px;
}

.status-card,
.control-card,
.record-card,
.stats-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.recording-info {
  margin-top: 20px;
  text-align: center;
}

.recording-info p {
  margin-top: 10px;
  font-size: 18px;
  color: #e6a23c;
}

.el-statistic {
  margin: 10px 0;
}
</style>
