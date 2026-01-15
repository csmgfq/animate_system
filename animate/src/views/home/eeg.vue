<template>
  <div class="eeg-control">
    <!-- 顶部控制栏 -->
    <div class="top-bar">
      <div class="status-section">
        <span class="section-title">设备状态</span>
        <el-tag :type="status.eeg_connected ? 'success' : 'danger'" size="small">
          EEG {{ status.eeg_connected ? '已连接' : '未连接' }}
        </el-tag>
        <el-tag :type="status.trigger_connected ? 'success' : 'danger'" size="small">
          Trigger {{ status.trigger_connected ? '已连接' : '未连接' }}
        </el-tag>
        <el-tag :type="status.server_running ? 'success' : 'info'" size="small">
          服务器 {{ status.server_running ? '运行中' : '已停止' }}
        </el-tag>
        <el-tag :type="status.recording ? 'warning' : 'info'" size="small">
          {{ status.recording ? '录制中' : '空闲' }}
        </el-tag>
        <el-button type="primary" size="small" link @click="refreshStatus">刷新</el-button>
      </div>

      <div class="control-section">
        <el-button-group size="small">
          <el-button type="primary" @click="startServer">启动服务器</el-button>
          <el-button type="danger" @click="stopServer">停止服务器</el-button>
          <el-button type="warning" @click="sendStartCmd" :disabled="!status.server_running">发送指令</el-button>
        </el-button-group>
        <el-button-group size="small" style="margin-left: 10px;">
          <el-button type="success" @click="startRecording" :disabled="status.recording || !status.server_running">
            <el-icon><VideoPlay /></el-icon> 开始录制
          </el-button>
          <el-button type="danger" @click="stopRecording" :disabled="!status.recording">
            <el-icon><VideoPause /></el-icon> 停止录制
          </el-button>
        </el-button-group>
        <span v-if="status.recording" class="recording-tag">
          <el-tag type="warning" effect="dark" size="small">{{ status.session_id }} - {{ formatDuration(status.duration) }}</el-tag>
        </span>
      </div>
    </div>

    <!-- 实时统计栏 -->
    <div v-if="realtime" class="stats-bar">
      <span class="stats-item">
        <span class="stats-label">EEG:</span>
        <el-tag size="small">接收 {{ realtime.eeg?.received || 0 }}</el-tag>
        <el-tag size="small" :type="(realtime.eeg?.loss_rate || 0) > 1 ? 'danger' : 'success'">
          丢包率 {{ realtime.eeg?.loss_rate || 0 }}%
        </el-tag>
      </span>
      <span class="stats-item">
        <span class="stats-label">Trigger:</span>
        <el-tag size="small">接收 {{ realtime.trigger?.received || 0 }}</el-tag>
        <el-tag size="small" :type="(realtime.trigger?.loss_rate || 0) > 1 ? 'danger' : 'success'">
          丢包率 {{ realtime.trigger?.loss_rate || 0 }}%
        </el-tag>
        <el-tag size="small" type="info">触发值 {{ realtime.trigger?.last_value || 0 }}</el-tag>
      </span>
    </div>

    <!-- 波形图主区域 -->
    <el-card class="waveform-card">
      <template #header>
        <div class="card-header">
          <span>EEG 实时波形</span>
          <el-button :type="waveformEnabled ? 'danger' : 'success'" size="small" @click="toggleWaveform">
            {{ waveformEnabled ? '停止显示' : '开始显示' }}
          </el-button>
        </div>
      </template>

      <div class="channel-selector">
        <span class="selector-label">通道：</span>
        <el-checkbox-group v-model="selectedChannels" size="small">
          <el-checkbox-button v-for="ch in 32" :key="ch - 1" :value="ch - 1">
            {{ ch }}
          </el-checkbox-button>
        </el-checkbox-group>
        <el-button size="small" @click="selectAllChannels">全选</el-button>
        <el-button size="small" @click="clearChannels">清空</el-button>
      </div>

      <div ref="waveformChart" class="waveform-chart"></div>
    </el-card>
  </div>
</template>

<script>
import { VideoPlay, VideoPause } from '@element-plus/icons-vue'
import { getApiBaseUrl } from '@/api/baseUrl'
import * as echarts from 'echarts'

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
      pollTimer: null,
      // 波形图相关
      waveformEnabled: false,
      waveformTimer: null,
      waveformChart: null,
      selectedChannels: [0, 1, 2, 3],  // 默认选择前4个通道
      sampleRate: 1000,
      displayDuration: 2  // 显示2秒数据
    }
  },
  mounted() {
    this.refreshStatus()
    this.startPolling()
  },
  beforeUnmount() {
    this.stopPolling()
    this.stopWaveform()
    if (this.waveformChart) {
      this.waveformChart.dispose()
      this.waveformChart = null
    }
  },
  methods: {
    getAuthHeaders() {
      try {
        const raw = localStorage.getItem('currentUser')
        if (!raw) return {}
        const user = JSON.parse(raw)
        const headers = {}
        if (user?.id != null) headers['X-User-Id'] = String(user.id)
        if (user?.account) headers['X-User-Account'] = String(user.account)
        return headers
      } catch (e) {
        return {}
      }
    },
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
        console.error('获取状态失败', e)
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
      const currentUser = JSON.parse(localStorage.getItem('currentUser') || '{}')
      try {
        const res = await fetch(`${getApiBaseUrl()}/api/eeg/recording/start`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', ...this.getAuthHeaders() },
          body: JSON.stringify({
            user_id: currentUser.id,
            user_account: currentUser.account
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
        const res = await fetch(`${getApiBaseUrl()}/api/eeg/recording/stop`, {
          method: 'POST',
          headers: { ...this.getAuthHeaders() }
        })
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
    },
    // 波形图相关方法
    toggleWaveform() {
      if (this.waveformEnabled) {
        this.stopWaveform()
      } else {
        this.startWaveform()
      }
    },
    startWaveform() {
      this.waveformEnabled = true
      this.initChart()
      this.fetchWaveformData()
      this.waveformTimer = setInterval(() => this.fetchWaveformData(), 1000)
    },
    stopWaveform() {
      this.waveformEnabled = false
      if (this.waveformTimer) {
        clearInterval(this.waveformTimer)
        this.waveformTimer = null
      }
    },
    selectAllChannels() {
      this.selectedChannels = Array.from({ length: 32 }, (_, i) => i)
    },
    clearChannels() {
      this.selectedChannels = []
    },
    initChart() {
      if (this.waveformChart) {
        this.waveformChart.dispose()
      }
      const chartDom = this.$refs.waveformChart
      if (!chartDom) return
      this.waveformChart = echarts.init(chartDom)
      this.updateChartOption([])
    },
    updateChartOption(seriesData) {
      if (!this.waveformChart) return

      const colors = [
        '#5470c6', '#91cc75', '#fac858', '#ee6666', '#73c0de',
        '#3ba272', '#fc8452', '#9a60b4', '#ea7ccc', '#48b8d0',
        '#ff9f7f', '#87cefa', '#da70d6', '#32cd32', '#6495ed',
        '#ff69b4', '#ba55d3', '#cd5c5c', '#ffa500', '#40e0d0',
        '#1e90ff', '#ff6347', '#7b68ee', '#00fa9a', '#ffd700',
        '#dc143c', '#00ced1', '#9400d3', '#ff1493', '#00bfff',
        '#adff2f', '#ff4500'
      ]

      const option = {
        animation: false,
        grid: {
          left: 60,
          right: 20,
          top: 30,
          bottom: 30
        },
        xAxis: {
          type: 'value',
          min: 0,
          max: this.displayDuration,
          name: '时间 (s)',
          nameLocation: 'middle',
          nameGap: 20
        },
        yAxis: {
          type: 'value',
          name: '电压 (μV)',
          nameLocation: 'middle',
          nameGap: 40
        },
        series: seriesData.map((data, idx) => ({
          name: `CH${this.selectedChannels[idx] + 1}`,
          type: 'line',
          showSymbol: false,
          data: data,
          lineStyle: { width: 1 },
          color: colors[this.selectedChannels[idx] % colors.length]
        })),
        tooltip: {
          show: false
        },
        legend: {
          show: this.selectedChannels.length <= 8,
          top: 0,
          type: 'scroll'
        }
      }
      this.waveformChart.setOption(option, true)
    },
    async fetchWaveformData() {
      if (!this.waveformEnabled || this.selectedChannels.length === 0) return

      try {
        const channels = this.selectedChannels.join(',')
        const url = `${getApiBaseUrl()}/api/eeg/waveform?duration=${this.displayDuration}&channels=${channels}`
        const res = await fetch(url)
        const json = await res.json()

        if (json.code === 1 && json.data && json.data.data) {
          const rawData = json.data.data
          const sampleRate = json.data.sample_rate || this.sampleRate

          // 降采样以提高性能（每10个点取1个）
          const downsampleFactor = 10
          const seriesData = rawData.map(channelData => {
            const result = []
            for (let i = 0; i < channelData.length; i += downsampleFactor) {
              const time = (i / sampleRate).toFixed(3)
              result.push([parseFloat(time), channelData[i]])
            }
            return result
          })

          this.updateChartOption(seriesData)
        }
      } catch (e) {
        console.error('获取波形数据失败', e)
      }
    }
  }
}
</script>

<style scoped>
.eeg-control {
  padding: 10px;
  height: calc(100vh - 80px);
  display: flex;
  flex-direction: column;
}

.top-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
  padding: 10px;
  background: #f5f7fa;
  border-radius: 4px;
  margin-bottom: 8px;
}

.status-section {
  display: flex;
  align-items: center;
  gap: 8px;
}

.section-title {
  font-weight: bold;
  color: #606266;
  margin-right: 5px;
}

.control-section {
  display: flex;
  align-items: center;
  gap: 8px;
}

.recording-tag {
  margin-left: 10px;
}

.stats-bar {
  display: flex;
  gap: 20px;
  padding: 8px 10px;
  background: #fafafa;
  border-radius: 4px;
  margin-bottom: 8px;
}

.stats-item {
  display: flex;
  align-items: center;
  gap: 6px;
}

.stats-label {
  font-weight: bold;
  color: #606266;
}

.waveform-card {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.waveform-card :deep(.el-card__body) {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 10px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.channel-selector {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  margin-bottom: 8px;
}

.selector-label {
  font-weight: bold;
  color: #606266;
}

.channel-selector .el-checkbox-group {
  display: flex;
  flex-wrap: wrap;
  gap: 2px;
}

.channel-selector .el-checkbox-button {
  margin: 0;
}

.waveform-chart {
  flex: 1;
  min-height: 300px;
}
</style>
