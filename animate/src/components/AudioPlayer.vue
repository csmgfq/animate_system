<template>
  <div class="my-audio">
    <!-- 音频播放器，使用timeupdate事件更新播放进度 -->
    <audio @timeupdate="updateProgress" controls ref="audioRef">
      <source :src="audioUrl" :type="fileType || 'audio/mpeg'" />
      您的浏览器不支持音频播放
    </audio>
    <!-- 音频控制区域 -->
    <div class="audio-container">
      <!-- 快退、播放/暂停、快进按钮 -->
      <div class="audio-controls">
        <el-button :disabled="!disabled" circle size="small" link @click="beforeTen" class="control-btn">
          <el-icon :size="20"><i class="el-icon-arrow-left">
            <CaretLeft />
          </i></el-icon>
        </el-button>
        <!-- 播放/暂停按钮，根据audioIsPlay动态改变图标 -->
        <el-button :disabled="!disabled" link @click="playAudio" circle class="play-button">
          <el-icon :size="35">
            <el-icon v-if="isLoading" class="is-loading"><Loading /></el-icon>
            <VideoPlay v-else-if="!audioIsPlay"/>
            <VideoPause v-else />
          </el-icon>
        </el-button>
        
        <el-button :disabled="!disabled" circle size="small" link @click="afterTen" class="control-btn">
          <el-icon :size="20"><i class="el-icon-arrow-right">
            <CaretRight />
          </i></el-icon>
        </el-button>
      </div>
      <!-- 播放进度条 -->
      <div class="slider-box">
        <span class="time-display">{{ audioStart }}</span>
        <el-slider class="slider" v-model="currentProgress" :show-tooltip="false" @input="handleProgressChange" />
        <span class="time-display">{{ durationTime }}</span>
      </div>
      <!-- 音量控制 -->
      <div class="volume" v-click-outside="closeVolumePanel">
        <div class="volume-progress" v-show="audioHubs">
          <el-slider
            vertical
            height="100px"
            class="volume-bar"
            v-model="audioVolume"
            :show-tooltip="false"
            @change="handleAudioVolume" />
        </div>
        <el-button class="volume-button" circle size="small" link @click="toggleVolumePanel">
          <el-icon :size="24" class="volume-icon">
            <Mute v-if="audioVolume === 0" />
            <Headset v-else />
          </el-icon>
        </el-button>
      </div>

      <!-- 历史菜单：点击后可选择已生成音乐 -->
      <el-popover
        v-model:visible="historyOpen"
        placement="top"
        width="320"
        trigger="click"
        @show="loadHistory"
      >
        <template #reference>
          <el-button class="history-button" circle size="small" link>
            <el-icon :size="24">
              <!-- 全局已注册所有 Element Plus 图标，这里直接使用 List 图标组件 -->
              <List />
            </el-icon>
          </el-button>
        </template>

        <div class="history-panel">
          <div v-if="historyLoading" class="history-empty">加载中...</div>
          <div v-else-if="historyItems.length === 0" class="history-empty">暂无历史音乐</div>
          <div v-else class="history-list">
            <div
              v-for="item in historyItems"
              :key="item.id"
              class="history-item"
              @click="selectHistory(item)"
            >
              <div class="history-title">
                <span>{{ item.genre }} / {{ item.timbre }}</span>
                <el-button
                  circle
                  size="small"
                  link
                  class="history-delete"
                  @click.stop="deleteHistory(item)"
                >
                  <el-icon :size="18"><Delete /></el-icon>
                </el-button>
              </div>
              <div class="history-sub">
                {{ formatCreatedAt(item.created_at) }}
              </div>
            </div>
          </div>
        </div>
      </el-popover>
    </div> 
  </div>
</template>

<script setup>
import axios from 'axios'
import { ref, watch, onMounted } from 'vue'
import { ElMessageBox, ElMessage, ClickOutside } from 'element-plus'
import { VideoPlay, VideoPause, CaretLeft, CaretRight, Mute, Headset, Loading, List, Delete } from '@element-plus/icons-vue'

// 注册点击外部指令
const vClickOutside = ClickOutside

// 定义 Props
const props = defineProps({
  baseUrl: {
    type: String,
    required: true
  }
})

const audioUrl = ref(''); // 存储音频文件的 URL
const isLoading = ref(false); // 新增加载状态
const audioRef = ref(null); // 存储音频元素的引用
const fileType = ref(null);

// 历史音乐（从后端按当前用户拉取）
const historyOpen = ref(false);
const historyLoading = ref(false);
const historyItems = ref([]);

// 默认不请求占位音频：占位路径可能不在库内或无归属导致 403
const currentFilePath = ref('');

function getAuthHeaders() {
  try {
    const raw = localStorage.getItem('currentUser');
    if (!raw) return {};
    const user = JSON.parse(raw);
    const headers = {};
    if (user?.id != null) headers['X-User-Id'] = String(user.id);
    if (user?.account) headers['X-User-Account'] = String(user.account);
    return headers;
  } catch (e) {
    return {};
  }
}

function formatCreatedAt(value) {
  if (!value) return '';
  // 后端 created_at 现在按本地时间写入（无时区信息的 ISO 字符串），这里默认按“本地时间”解析。
  // 若字符串自带时区（如 Z 或 +08:00），则按其时区解析并展示为本地时间。
  const s = String(value).trim();
  if (!s) return '';
  const hasTz = /([zZ]|[+-]\d\d:?\d\d)$/.test(s);
  const d = new Date(s);
  // 某些运行环境对无时区的 "YYYY-MM-DD HH:mm:ss" 解析不稳定，兜底替换为空间/补 T
  if (Number.isNaN(d.getTime())) {
    const normalized = s.replace(' ', 'T');
    const d2 = new Date(normalized);
    if (!Number.isNaN(d2.getTime())) {
      return d2.toLocaleString('zh-CN', { hour12: false });
    }
  }
  if (Number.isNaN(d.getTime())) return s;

  // 如果带时区，Date 会自动转本地；不带时区且是 ISO(T) 格式，通常按本地解析
  if (Number.isNaN(d.getTime())) return s;
  return d.toLocaleString('zh-CN', { hour12: false });
}

async function loadHistory() {
  if (historyLoading.value) return;
  historyLoading.value = true;
  try {
    const res = await axios.get(`${props.baseUrl}/api/music`, { headers: getAuthHeaders() });
    const items = res?.data?.data;
    historyItems.value = Array.isArray(items) ? items : [];
  } catch (e) {
    historyItems.value = [];
  } finally {
    historyLoading.value = false;
  }
}

async function deleteHistory(item) {
  const id = item?.id;
  if (id == null) return;
  try {
    await ElMessageBox.confirm(
      '确认删除这条音乐记录吗？将同时删除本地文件与数据库记录。',
      '确认删除',
      {
        type: 'warning',
        confirmButtonText: '删除',
        cancelButtonText: '取消',
      }
    );

    await axios.delete(`${props.baseUrl}/api/music/${id}`, { headers: getAuthHeaders() });
    historyItems.value = historyItems.value.filter((x) => x?.id !== id);
    const path = item?.file_path || item?.filePath;
    if (path && currentFilePath.value === path) {
      currentFilePath.value = '';
      audioUrl.value = '';
      fileType.value = null;
      audioIsPlay.value = false;
      try {
        const last = localStorage.getItem('lastMusicFilePath');
        if (last === path) localStorage.removeItem('lastMusicFilePath');
      } catch (e) {
        // ignore
      }
    }
    ElMessage.success('已删除');
  } catch (e) {
    // 取消删除
    if (e === 'cancel' || e?.toString?.() === 'cancel') return;
    // 删除失败时不阻断 UI，控制台可查看原因
    console.error('删除音乐失败:', e);
    ElMessage.error('删除失败');
  }
}

function selectHistory(item) {
  const path = item?.file_path || item?.filePath;
  if (!path) return;
  historyOpen.value = false;
  isLoading.value = true;
  audioIsPlay.value = false;
  audioUrl.value = '';
  currentFilePath.value = path;
  try {
    localStorage.setItem('lastMusicFilePath', path);
  } catch (e) {
    // ignore
  }
  fetchAudio(path);
}

async function fetchAudio(filePathArg) {
  try {
    const targetPath = filePathArg || currentFilePath.value;
    if (!targetPath) {
      isLoading.value = false;
      return;
    }

    // 兜底：若拦截器未注入请求头，则在 body 里带上用户信息（后端兼容 userId/user_id）
    let currentUser = null;
    try {
      const raw = localStorage.getItem('currentUser');
      currentUser = raw ? JSON.parse(raw) : null;
    } catch (e) {
      currentUser = null;
    }

    const response = await axios.post(`${props.baseUrl}/api/music-gen/music`, {
      filePath: targetPath,
      userId: currentUser?.id,
      userAccount: currentUser?.account,
    });
    if (response.data.error) {
      console.error(response.data.error);
      isLoading.value = false; // 出现错误时取消加载状态
      return;
    }
    const fileUrl = response.data.fileUrl; // 从响应中提取 fileUrl
    if (fileUrl) {
      // 构建完整的 URL
      audioUrl.value = `${props.baseUrl}${fileUrl}`; // 设置音频 URL
      fileType.value = fileUrl.endsWith('.mp3') ? 'audio/mpeg' : 'audio/wav'; // 设置文件类型
      // console.log('Audio URL fetched:', audioUrl.value);
      isLoading.value = false; // 音频加载成功后取消加载状态
      audioIsPlay.value = true; // 音频加载成功后设置为播放状态
    } else {
      console.error('Audio URL is undefined');
      isLoading.value = false; // URL 未定义时取消加载状态
    }
  } catch (error) {
    console.error('There was an error fetching the audio file!', error);
    isLoading.value = false; // 捕获到错误时取消加载状态
  }
}

// 使用 watch 来观察 audioUrl 的变化
watch(audioUrl, (newUrl) => {
  if (newUrl && audioRef.value) {
    audioRef.value.src = newUrl;
    audioRef.value.load(); // 加载新的音频源
    // 尝试播放，但由于浏览器策略，可能需要用户交互
    // audioRef.value.play().then(() => {
    //   audioIsPlay.value = true;
    // }).catch(error => {
    //   console.warn('自动播放失败，可能需要用户交互:', error);
    // });
  }
});

// 在组件挂载时获取音频URL
onMounted(() => {
  // console.log('Received audio URL1:', audioUrl);
  // 不在挂载时自动请求音频，避免触发无归属/无权限音频导致 403
  try {
    const last = localStorage.getItem('lastMusicFilePath');
    if (last) currentFilePath.value = last;
  } catch (e) {
    // ignore
  }
  window.addEventListener('music-generated', handleMusicGenerated);
});

const handleMusicGenerated = (event) => {
  isLoading.value = true;
  audioIsPlay.value = false;
  audioUrl.value = '';
  const nextPath = event?.detail?.filePath;
  if (nextPath) {
    currentFilePath.value = nextPath;
    try {
      localStorage.setItem('lastMusicFilePath', nextPath);
    } catch (e) {
      // ignore
    }
  }
  fetchAudio(currentFilePath.value);
  // 确保在音乐生成后，如果用户点击播放，能够正确加载和播放
  if (audioRef.value) {
    audioRef.value.load();
  }
};


onMounted(() => {
  audioRef.value = document.querySelector('audio'); // 确保选择器匹配您的 <audio> 元素
});

onMounted(() => {
  audioRef.value.addEventListener('loadeddata', () => {
    console.log('音频已加载，可以播放');
  });
});



// 是否正在播放
const audioIsPlay = ref(false);
// 音频开始时间显示
const audioStart = ref('0:00');
// 音频总时长显示
const durationTime = ref('0:00');
// 音频总时长
const duration = ref(0);
// 音量控制
const audioVolume = ref(80);
// 是否显示音量控制滑块
const audioHubs = ref(false);

// 切换音量面板显示
const toggleVolumePanel = () => {
  audioHubs.value = !audioHubs.value;
};

// 关闭音量面板
const closeVolumePanel = () => {
  audioHubs.value = false;
};

// 音频元素引用
// const audioRef = ref(null); 
// 当前播放进度
const currentProgress = ref(0);
// 是否已经加载过音频
const isAudioLoaded = ref(false);
// 是否禁用控制按钮
const disabled = ref(true);
// 监听音频总时长变化，禁用快进和快退按钮

onMounted(() => {
  const audio = audioRef.value;
  audio.addEventListener('timeupdate', updateProgress);
  audio.addEventListener('loadeddata', () => {
    duration.value = audio.duration; // 获取音频时长
    durationTime.value = transTime(audio.duration); // 更新音频时长显示
  });
  audio.addEventListener('ended', () => {
    audioIsPlay.value = false;
  });
});

watch(
  () => duration.value,
  (newVal) => {
    if (newVal) {
      disabled.value = true;
    }
  }
);


// 监听音频URL变化，重置加载状态
watch(
  () => audioUrl.value,
  () => {
    if (audioRef.value) {
      audioRef.value.src = audioUrl.value;
      duration.value = 0; // 重置时长
      audioStart.value = '0:00'; // 重置开始时间
      durationTime.value = '0:00'; // 重置时长显示
      currentProgress.value = 0; // 重置进度
      audioIsPlay.value = false; // 重置播放状态
      isAudioLoaded.value = false; // 重置音频加载状态
    }
  }
);

// 将秒转换为分钟:秒的格式
const transTime = (duration) => {
  const minutes = Math.floor(duration / 60);
  const seconds = Math.floor(duration % 60);
  const formattedMinutes = String(minutes).padStart(2, '0');
  const formattedSeconds = String(seconds).padStart(2, '0');
  return `${formattedMinutes}:${formattedSeconds}`;
};


// 播放或暂停音频
const playAudio = () => {
  if (audioRef.value && !isLoading.value) {
    if (!audioIsPlay.value) {
      if (audioRef.value.currentTime !== 0) {
        // 如果当前播放时间不为0，说明是暂停后播放，直接播放
        audioRef.value.play()
          .then(() => {
            audioIsPlay.value = true;
          })
          .catch(error => {
            console.error('播放音频时出错:', error);
          });
      } else if (audioUrl.value) {
        // 如果当前播放时间为0，但audioUrl已经存在，则直接播放
        audioRef.value.play()
          .then(() => {
            audioIsPlay.value = true;
          })
          .catch(error => {
            console.error('播放音频时出错:', error);
          });
      } else {
        // 如果audioUrl为空，则重新获取音频
        isLoading.value = true; // 进入加载状态
        audioUrl.value = ''; // 清空音频 URL
        fetchAudio(); // 重新请求音频
        audioRef.value.load(); // 确保音频元素加载新的音频源
      }
    } else {
      audioRef.value.pause();
      audioIsPlay.value = false;
    }
  }
};

// 更新播放进度
const updateProgress = (e) => {
  let value = e.target.currentTime / duration.value;
  currentProgress.value = value * 100;
  audioStart.value = transTime(e.target.currentTime);
};

// 调整播放进度
const handleProgressChange = (val) => {
  if (!val) {
    return;
  }
  audioRef.value.currentTime = duration.value * (val / 100);
};

// 调整音量
const handleAudioVolume = (val) => {
  audioRef.value.volume = val / 100;
};

// 快退10秒
const beforeTen = () => {
  audioRef.value.currentTime -= 10;
};

// 快进10秒
const afterTen = () => {
  audioRef.value.currentTime += 10;
};
</script>

<style lang="scss" scoped>
.my-audio {
  width: 100%;
  max-width: 100%;
  margin: 0;
  padding: 15px;
  border-radius: 12px;
  background: linear-gradient(145deg, #f0f0f0, #ffffff);
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.1);
  
  audio {
    display: none;
  }
  
  .audio-container {
    width: 100%;
    height: 70px;
    display: flex;
    align-items: center;
    border-radius: 10px;
    box-sizing: border-box;
    position: relative;
    padding: 0 10px;
    background: rgba(255, 255, 255, 0.8);
    backdrop-filter: blur(5px);
    
    .audio-controls {
      display: flex;
      margin-right: 20px;
      align-items: center;
      
      .control-btn {
        transition: all 0.3s ease;
        color: #005fff;
        
        &:hover {
          transform: scale(1.1);
          color: #005fff;
        }
        
        &:active {
          transform: scale(0.95);
        }
      }
      
      .play-button {
        margin: 0 12px;
        background: linear-gradient(145deg, #f0f0f0, #ffffff);
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
        transition: all 0.3s ease;
        border-radius: 50%;
        width: 50px;
        height: 50px;
        display: flex;
        align-items: center;
        justify-content: center;
        
        &:hover {
          transform: scale(1.05);
          box-shadow: 0 6px 12px rgba(0, 0, 0, 0.15);
        }
        
        &:active {
          transform: scale(0.95);
        }
        
        .el-icon {
          color: #005fff;
        }
      }
    }
    
    .slider-box {
      flex: 1;
      min-width: 120px;
      display: flex;
      align-items: center;
      padding: 0 10px;
      overflow: hidden;

      .time-display {
        font-size: 14px;
        color: #49505c;
        line-height: 18px;
        font-weight: 500;
        min-width: 45px;
        flex-shrink: 0;
      }

      .slider {
        flex: 1;
        min-width: 60px;
        margin: 0 10px;
        height: 8px;
        
        :deep(.el-slider__runway) {
          height: 8px;
          background-color: rgba(200, 200, 200, 0.3);
          border-radius: 4px;
        }
        
        :deep(.el-slider__bar) {
          height: 8px;
          background: linear-gradient(to right, #005fff, #005fff);
          border-radius: 4px;
        }
        
        :deep(.el-slider__button-wrapper) {
          top: -8px;
          width: 24px;
          height: 24px;
        }
        
        :deep(.el-slider__button) {
          width: 16px;
          height: 16px;
          border: 3px solid #005fff;
          background: white;
          transition: transform 0.2s;
          
          &:hover {
            transform: scale(1.1);
          }
        }
      }
    }
  }
  
  .volume {
  position: relative;
  width: 40px;
  height: 40px;
  margin: 0 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  
  .volume-progress {
    width: 40px;
    height: 150px;
    position: absolute;
    bottom: 45px;
    right: 0;
    background: white;
    border-radius: 10px;
    box-shadow: 0 5px 15px rgba(0, 0, 0, 0.15);
    padding: 10px 0;
    display: flex;
    justify-content: center;
    z-index: 1000;
  }
  
  .volume-bar {
    background: #ffffff;
    border-radius: 8px;
    
    :deep(.el-slider__runway) {
      width: 6px;
      background-color: rgba(200, 200, 200, 0.3);
    }
    
    :deep(.el-slider__bar) {
      width: 6px;
      background: linear-gradient(to top, #13d6e5, #005fff);
    }
    
    :deep(.el-slider__button) {
      width: 14px;
      height: 14px;
      border: 2px solid #13d6e5;
      background: white;
    }
  }
  
  .volume-button {
    padding: 8px;
    transition: all 0.3s ease;
    
    &:hover {
      transform: scale(1.1);
    }
    
    &:active {
      transform: scale(0.95);
    }
  }
  
  .volume-icon {
    color: #005fff;
    transition: color 0.3s;
    
    &:hover {
      color: #005fff;
    }
  }
  }
}

.history-button {
  margin-left: 6px;
}

.history-panel {
  max-height: 240px;
  overflow: auto;
}

.history-empty {
  color: #666;
  font-size: 12px;
  padding: 8px 4px;
}

.history-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.history-item {
  padding: 8px 10px;
  border-radius: 8px;
  cursor: pointer;
  background: #f5f5f5;
}

.history-item:hover {
  background: #eeeeee;
}

.history-title {
  font-size: 13px;
  font-weight: 600;
  color: #333;
}

.history-sub {
  font-size: 12px;
  color: #666;
  margin-top: 2px;
}

@media (max-width: 600px) {
  .my-audio {
    padding: 10px;

    .audio-container {
      height: auto;
      min-height: 60px;
      flex-wrap: wrap;
      gap: 8px;
      padding: 8px;

      .audio-controls {
        margin-right: 10px;
        flex-shrink: 0;

        .play-button {
          width: 40px;
          height: 40px;
          margin: 0 8px;
        }
      }

      .slider-box {
        flex: 1 1 100%;
        min-width: 0;
        order: 1;
        padding: 0 5px;

        .time-display {
          font-size: 12px;
          min-width: 36px;
        }

        .slider {
          margin: 0 8px;
          min-width: 50px;
        }
      }
    }

    .volume {
      margin: 0 5px;
      flex-shrink: 0;
    }
  }
}
</style>