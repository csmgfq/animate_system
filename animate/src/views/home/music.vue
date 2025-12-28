<template>
  <div>
    <div class="container">
      <div class="left-content">
        <el-button type="success" class="my-button" @click="showEmotion">情绪判别结果展示</el-button>

        <el-form :model="formData" label-width="120px" class="my-form" @submit.prevent="handleSubmit">
          <p class="center-text">音乐生成</p>

          <el-form-item label="选择曲风">
            <el-select v-model="formData.genre" placeholder="请选择曲风">
              <el-option label="流行" value="pop"></el-option>
              <el-option label="摇滚" value="rock"></el-option>
              <el-option label="爵士" value="jazz"></el-option>
              <el-option label="电子" value="electronic"></el-option>
              <el-option label="古典" value="classical"></el-option>
            </el-select>
          </el-form-item>

          <el-form-item label="选择音色">
            <el-radio-group v-model="formData.timbre">
              <el-radio label="piano">钢琴</el-radio>
              <el-radio label="guitar">吉他</el-radio>
              <el-radio label="violin">小提琴</el-radio>
            </el-radio-group>
          </el-form-item>

          <el-form-item label="具体描述">
            <el-input
              type="textarea"
              v-model="formData.description"
              :rows="4"
              placeholder="请输入对音乐的具体描述，例如风格特点、情感表达等"
            ></el-input>
          </el-form-item>

          <el-button
            type="primary"
            :loading="isGenerating"
            :disabled="!formData.genre || !formData.timbre"
            @click="handleSubmit"
          >
            {{ buttonText }}
          </el-button>
        </el-form>

        <!-- 音频播放器：放到左侧表单下面对齐 -->
        <div class="audio-player-container">
          <audio-player :base-url="baseUrl" />
        </div>
      </div>

      <div class="right-content">
        <el-header class="header">
          <img :src="logoImage" alt="科技飞鸟" class="header-image" />
          <span class="header-text">情绪判别结果</span>
        </el-header>
        <el-card class="box-card">
          <template #header>
            <img v-if="dictImg[emotionText]" :src="dictImg[emotionText]" alt="emoji" class="emotion-image" />
            <span v-else class="header-text">暂无结果</span>
          </template>
          <el-form>
            <el-text class="emotion-text">
              {{ emotionText }}
            </el-text>
          </el-form>
        </el-card>
      </div>
    </div>
  </div>
</template>

<script setup>
import axios from 'axios'
import { ref, reactive } from 'vue'
import { getApiBaseUrl } from '../../api/baseUrl'
import logoImage from '../../assets/images/logo.jpg'
import Happy from '../../assets/images/emoji/Happy.webp'
import Sad from '../../assets/images/emoji/Sad.webp'
import Calm from '../../assets/images/emoji/Calm.webp'
import Angry from '../../assets/images/emoji/Angry.webp'


const formData = reactive({
  genre: '',
  timbre: '',
  description: ''
});

const isGenerating = ref(false);
const buttonText = ref('提交');
const baseUrl = ref(getApiBaseUrl());

const handleSubmit = async () => {
  if (!formData.genre || !formData.timbre) {
    alert('请先选择曲风和音色')
    return
  }

  let user = null
  try {
    const raw = localStorage.getItem('currentUser')
    user = raw ? JSON.parse(raw) : null
    if (!user || user.id == null) {
      alert('请先登录后再生成音乐')
      return
    }
  } catch (e) {
    alert('请先登录后再生成音乐')
    return
  }

  isGenerating.value = true;
  buttonText.value = '等待音乐生成中...';

  try {
    const payload = {
      ...formData,
      userId: user?.id,
      userAccount: user?.account,
    }
    const response = await axios.post(`${baseUrl.value}/api/music-gen/submit`, payload);
    console.log('Data submitted successfully:', response.data);
    alert('音乐生成成功');
    // 音乐生成成功后，通知 AudioPlayer 组件更新音频，传递后端返回的文件路径
    const filePath = response?.data?.data?.filePath;
    window.dispatchEvent(new CustomEvent('music-generated', { detail: { filePath } }));
  } catch (error) {
    console.error('Error submitting data:', error);
    alert('提交失败，请检查网络连接或后端服务是否正常运行');
  } finally {
    isGenerating.value = false;
    buttonText.value = '提交';
  }
}



// // 定义响应式数据
const emotionText = ref('等待情绪结果...')
const imgSources = ref([])
const dictImg = ref({"Happy": Happy, "Sad": Sad, "Calm": Calm, "Angry": Angry})


// 顶部按钮（与视频调控一致）
const showEmotion = () => {
  axios
    .post(`${baseUrl.value}/api/music-gen/emotion`, { filePath: 'public/toy.edf' })
    .then((response) => {
      const data = response.data;
      emotionText.value = data.emotionText;
      imgSources.value = data.imgSources;
    })
    .catch((error) => {
      console.log('Error: ', error);
    });
}



</script>


<style scoped>
/* 父容器，设置为 flex 布局（与视频调控一致） */
.container {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: var(--app-gap);
}

.left-content {
  flex: 1 1 520px;
  min-width: 0;
}

.right-content {
  flex: 1 1 360px;
  min-width: 0;
  margin-left: 0;
  margin-top: 0;
  display: flex;
  align-items: center;
  align-content: center;
  flex-direction: column;
}

.header {
  display: flex;
  align-items: center;
}

.header-image {
  width: 50px;
  height: auto;
  margin-right: 0px;
  margin-top: auto;
}

.header-text {
  font-size: 20px;
  font-weight: 700;
  color: #544d4d;
  letter-spacing: 0.5px;
  margin-left: 10px;
  margin-top: auto;
  text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.2);
}

.box-card {
  width: min(280px, 100%);
  margin-top: 10px;
  text-align: center;
}

.box-card :deep(.el-card__header) {
  padding: 20px 20px 10px;
  border-bottom: none;
  display: flex;
  justify-content: center;
}

.box-card :deep(.el-card__body) {
  padding: 10px 20px 20px;
}

.emotion-image {
  width: 64px;
  height: 64px;
  object-fit: contain;
}

.emotion-text {
  font-size: 22px;
  font-weight: 600;
  color: #544d4d;
  letter-spacing: 1px;
  text-align: center;
  display: block;
}

.my-button {
  margin: 10px;
  background-color: #4caf50;
  color: #fff;
  border: none;
  border-radius: 5px;
  padding: 10px 20px;
  font-size: 16px;
  cursor: pointer;
  transition: background-color 0.3s ease;
}

.my-button:hover {
  background-color: #45a049;
}

.my-form {
  margin-top: 20px;
  padding: 20px;
  border: 1px dashed var(--app-border);
  background: var(--app-surface);
  border-radius: var(--app-radius);
  box-shadow: var(--app-shadow-sm);
  width: 100%;
  box-sizing: border-box;
}

.center-text {
  text-align: center;
  font-size: 18px;
  margin-bottom: 10px;
}

.audio-player-container {
  margin-top: 20px;
  /* 与 el-form 的 label-width("120px") 对齐：播放器从“标签列结束的竖线”处开始 */
  /* padding-left: 10px; */
  width: 96%;
  box-sizing: border-box;
}

@media (max-width: 768px) {
  .container {
    flex-direction: column;
  }

  .left-content,
  .right-content {
    width: 100%;
    margin-left: 0;
  }

  .box-card {
    margin-left: 0;
    height: auto;
    padding: 10px 0;
  }
}
</style>
