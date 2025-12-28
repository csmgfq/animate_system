<template>
  <div class="container">
    <div class="left-content">
      <el-button type="success" class="my-button" @click="showEmotion">
        情绪判别结果展示</el-button
      >

      <!-- <el-dialog :visible.sync="formVisible" title="视频推荐问卷"> -->

      <el-form :model="formData" label-width="200px" class="my-form">
        <p class="center-text">视频推荐</p>
        <el-form-item label="场景/自然标签">
          <el-checkbox-group v-model="formData.season" multiple>
            <el-checkbox v-for="t in seasonTags" :key="t" :label="t" />
          </el-checkbox-group>
        </el-form-item>

        <el-form-item label="内容/类型标签">
          <el-checkbox-group v-model="formData.movie" multiple>
            <el-checkbox v-for="t in movieTags" :key="t" :label="t" />
          </el-checkbox-group>
        </el-form-item>

        <el-form-item label="音乐/氛围标签">
          <el-checkbox-group v-model="formData.music" multiple>
            <el-checkbox v-for="t in musicTags" :key="t" :label="t" />
          </el-checkbox-group>
        </el-form-item>

        <el-form-item label="自定义标签">
          <el-input
            v-model="formData.customTags"
            clearable
            placeholder="可输入表格里的任意标签，多个用逗号分隔（例如：雨声, 放松, 4K）"
          />
        </el-form-item>

        <el-button
          type="primary"
          :disabled="!hasAnySelection"
          @click="submitForm"
        >提交</el-button>
      </el-form>

      <!-- 推荐结果：给出 3 个可选视频，不自动跳转 -->
      <el-dialog v-model="recommendVisible" class="recommend-dialog" title="推荐视频（可选）" width="520px">
        <div v-if="recommendations.length === 0">暂无推荐结果</div>
        <div v-else>
          <div v-for="(item, idx) in recommendations" :key="item.url" class="recommend-row">
            <el-button class="recommend-btn" type="primary" @click="openVideo(item.url)">
              选项{{ idx + 1 }}
            </el-button>
            <div class="recommend-tags">
              <el-tag v-for="t in (item.tags || []).slice(0, 8)" :key="t" size="small">{{ t }}</el-tag>
            </div>
          </div>
        </div>
      </el-dialog>

      <!-- B站视频：弹窗 iframe 播放（点推荐选项后弹出，不跳转新网页） -->
      <el-dialog
        v-model="playerVisible"
        class="player-dialog"
        title="视频播放"
        width="70%"
        top="8vh"
        @close="stopEmbeddedPlayback"
        @closed="stopEmbeddedPlayback"
      >
        <div v-if="videoEmbedSrc" class="iframe-shell">
          <div class="iframe-wrapper" :style="{ aspectRatio: videoAspectRatioCss }">
            <iframe
              :src="videoEmbedSrc"
              scrolling="no"
              border="0"
              frameborder="no"
              framespacing="0"
              allowfullscreen="true"
            ></iframe>
          </div>
        </div>
        <div v-else class="video-hint">暂无可播放视频</div>
      </el-dialog>
      <!-- 新增：视频播放框 -->
      <!-- <el-form :model="videoPlayerForm" label-width="200px" class="my-form">
        <p class="center-text">视频播放模块</p>

        <el-form-item label="视频地址">
          <el-input v-model="videoUrl" placeholder="videoUrl"></el-input>
        </el-form-item>    
        <div>
            <el-button type="primary" @click="openVideo">跳转播放</el-button>
        </div>
      </el-form> -->
    </div>

    <div class="right-content">
      <el-header class="header">
        <img :src="logoImage" alt="科技飞鸟" class="header-image" />
        <span class="header-text">情绪判别结果</span>
      </el-header>
      <el-card class="box-card">
        <template #header>
          <img v-if="dictImg[emotionText]" :src="dictImg[emotionText]" alt="emoji" class="emotion-image" />
          <span v-else class="header-text">EEG采集设备暂离</span>
        </template>
        <el-form>
          <el-text class="emotion-text">
            {{ emotionText }}
          </el-text>
        </el-form>
      </el-card>
    </div>
  </div>
</template>

<script>
import axios from "axios";
import { getApiBaseUrl } from "../../api/baseUrl";
import logoImage from "../../assets/images/logo.jpg";
import Happy from "../../assets/images/emoji/Happy.webp";
import Sad from "../../assets/images/emoji/Sad.webp";
import Calm from "../../assets/images/emoji/Calm.webp";
import Angry from "../../assets/images/emoji/Angry.webp";

export default {
  components: {},
  data() {
    return {
      //   表单数据
      apiBaseUrl: getApiBaseUrl(),
      formData: {
        season: [], // 修改为数组类型
        movie: [], // 修改为数组类型
        music: [], // 修改为数组类型
        customTags: '', // 自定义标签（逗号分隔）
      }, // 用于存储表单输入结果

      // 标签来源：后端 report.xlsx -> catalog.json -> tags_summary.json
      // 说明：后端匹配是“精确字符串匹配”，所以这里的 label 需要与表格中的 tag 尽量一致。
      seasonTags: [
        '大自然',
        '森林',
        '风景',
        '海浪',
        '雨声',
        '夜晚',
        '街景',
      ],
      movieTags: [
        '生活记录',
        '日常',
        'Vlog',
        '散步',
        '美食',
        '旅游',
        '收纳',
        '学习'
      ],
      musicTags: [
        '放松',
        '助眠',
        '白噪音',
        '治愈',
        '冥想',
        '纯音乐',
        '催眠',
        '减压',
        '环境音',
        '轻音乐',
        '沉浸式'
      ],

      // B站播放：保存“原始链接”，再转换成可嵌入 iframe 的 player 链接
      videoUrl: localStorage.getItem("videoUrl") || "",
      videoEmbedSrc: "",
      videoAspectRatioCss: "16 / 9",
      formVisible: true, // 控制表单的显示
      logoImage: logoImage,
      emotionText: "等待情绪结果...",
      imgSources: [],
      dictImg: { Happy: Happy, Sad: Sad, Calm: Calm, Angry: Angry },
      playerOptions: {
        autoplay: false,
        controls: true,
        sources: [],
      },

      recommendVisible: false,
      recommendations: [],

      playerVisible: false,
      resumeRecommendAfterPlayer: false,
    };
  },

  computed: {
    // 保留 computed 接口，避免改动过大
    serverIp() {
      return this.apiBaseUrl;
    },
    // 判断是否至少选择了一个选项或填写了自定义标签
    hasAnySelection() {
      const { season, movie, music, customTags } = this.formData;
      const hasCheckbox = (season && season.length > 0) ||
                          (movie && movie.length > 0) ||
                          (music && music.length > 0);
      const hasCustom = customTags && customTags.trim().length > 0;
      return hasCheckbox || hasCustom;
    },
  },

  methods: {
    stopEmbeddedPlayback() {
      // 关闭弹窗后必须清空 iframe src，否则可能继续后台播放声音
      this.videoEmbedSrc = "";
      this.videoAspectRatioCss = "16 / 9";

      // 如果视频是从“推荐弹窗”打开的，则关闭后恢复推荐弹窗
      if (this.resumeRecommendAfterPlayer) {
        this.recommendVisible = true;
        this.resumeRecommendAfterPlayer = false;
      }
    },

    async fetchBiliMetaAndApply(rawUrl) {
      try {
        const resp = await axios.get(`${this.apiBaseUrl}/api/video-rec/bili-meta`, {
          params: { url: String(rawUrl || '').trim() },
        });
        const data = resp?.data?.data;
        if (data?.aspectRatioCss) {
          this.videoAspectRatioCss = String(data.aspectRatioCss);
        }
        if (data?.embedUrl) {
          this.videoEmbedSrc = String(data.embedUrl);
        }
      } catch (e) {
        // ignore: 失败则继续使用前端本地转换的默认 16:9
      }
    },

    toBilibiliEmbedUrl(rawUrl) {
      const u = String(rawUrl || '').trim();
      if (!u) return '';

      // 已是 B 站播放器链接：直接使用
      if (u.includes('player.bilibili.com/player.html')) {
        return u.startsWith('http://') ? u.replace('http://', 'https://') : u;
      }

      // 兼容 catalog.json：一般是 https://www.bilibili.com/video/BVxxxx
      const bvidMatch = u.match(/\/video\/(BV[0-9A-Za-z]+)\/?/i);
      if (bvidMatch && bvidMatch[1]) {
        const bvid = bvidMatch[1];
        return `https://player.bilibili.com/player.html?bvid=${encodeURIComponent(bvid)}&page=1`;
      }

      // 兼容 av 号
      const avMatch = u.match(/\bav(\d+)\b/i);
      if (avMatch && avMatch[1]) {
        const aid = avMatch[1];
        return `https://player.bilibili.com/player.html?aid=${encodeURIComponent(aid)}&page=1`;
      }

      // 其他链接（比如 b23.tv 短链）无法在前端稳定解析为 bvid/aid，这里返回空表示不可嵌入
      return '';
    },

    applyVideoUrl() {
      const raw = String(this.videoUrl || '').trim();
      localStorage.setItem('videoUrl', raw);
      this.videoEmbedSrc = this.toBilibiliEmbedUrl(raw);
    },

    //情绪模块
    showEmotion() {
      axios
        .post(`${this.apiBaseUrl}/api/music-gen/emotion`, {
          filePath: "public/toy.edf",
        })
        .then((response) => {
          const data = response.data;
          this.emotionText = data.emotionText;
          this.imgSources = data.imgSources;
        })
        .catch((error) => {
          console.log("Error: ", error);
        });
    },
    // 提交表单
    async submitForm() {
      try {
        // 提交表单数据
        await this.submitFormData();

        // 获取视频匹配结果（3 个备选）
        const options = await this.getVideoMatching(3);
        this.recommendations = options;
        this.recommendVisible = true;
      } catch (error) {
        console.error("提交失败:", error);
      }
    },
    
    // 提交表单数据
    async submitFormData() {
      try {
        // 注意：不要直接把 formData（checkbox-group 依赖数组）改成字符串。
        // 否则第一次提交后 v-model 类型会变，第二次再点会报 value.join is not a function。
        const custom = String(this.formData.customTags || '')
          .replace(/，/g, ',')
          .split(',')
          .map((s) => s.trim())
          .filter(Boolean)
          .join(', ')

        const payload = {
          season: Array.isArray(this.formData.season) ? this.formData.season.join(', ') : (this.formData.season || ''),
          movie: Array.isArray(this.formData.movie) ? this.formData.movie.join(', ') : (this.formData.movie || ''),
          music: Array.isArray(this.formData.music) ? this.formData.music.join(', ') : (this.formData.music || ''),
          // 复用 Question.musicInstrument 存储自定义标签；后端 match 会把它一起纳入 tokens
          musicInstrument: custom,
        }

        // const formDataStringArray = Object.values(this.formData).map(category => category.join(', '));
        // alert("提交成功：" + JSON.stringify(formDataStringArray)); // 显示来自后端的响应
        // 将formData中的表单数据存储为一个字符串数组
        const response = await axios.post(
          `${this.apiBaseUrl}/api/question`,
          payload,
          {
            headers: {
              "Content-Type": "application/json", // 确保设置正确的内容类型
            },
          }
        );
        return response.data;
      } catch (error) {
        console.error("提交表单数据失败:", error);
        throw error;
      }
    },
    
    // 获取视频匹配结果
    async getVideoMatching(k = 1) {
      try {
        const response = await axios.get(`${this.apiBaseUrl}/api/video-rec/match`, {
          params: { k }
        });
        const data = response?.data?.data;
        if (k === 1) {
          const url = data?.url;
          return url ? [{ url, score: data?.score ?? 0, tags: data?.tags || [] }] : [];
        }
        // 兼容旧后端：如果还没重启导致仍返回 data.url，则至少给 1 个选项。
        const options = Array.isArray(data?.options) ? data.options : [];
        const normalized = options.filter((x) => x && x.url);
        if (normalized.length > 0) return normalized;
        const fallbackUrl = data?.url;
        return fallbackUrl ? [{ url: fallbackUrl, score: data?.score ?? 0, tags: data?.tags || [] }] : [];
      } catch (error) {
        console.error("获取视频匹配结果失败:", error);
        throw error;
      }
    },
    
    normalizePlayUrl(url) {
      const u = String(url || '');
      if (!u) return u;
      if (u.startsWith('http://') || u.startsWith('https://')) return u;
      // 兼容后端返回相对路径（如 /static/video/xxx.mp4）
      if (u.startsWith('/')) return `${this.apiBaseUrl}${u}`;
      return `${this.apiBaseUrl}/${u}`;
    },

    openVideo(videoUrl) {
      // 需求：关闭视频弹窗后，推荐弹窗仍可继续选
      if (this.recommendVisible) {
        this.resumeRecommendAfterPlayer = true;
        this.recommendVisible = false;
      }
      const raw = String(videoUrl || '').trim();
      this.videoUrl = raw;
      this.applyVideoUrl();

      // 尝试从后端获取真实宽高，自动适配横竖屏（不新增UI）
      this.fetchBiliMetaAndApply(raw);

      // 可嵌入：直接弹窗播放
      if (this.videoEmbedSrc) {
        this.playerVisible = true;
        return;
      }

      // 若无法转换为可嵌入链接，则仍保留兜底：新窗口打开
      if (!this.videoEmbedSrc) {
        const normalized = this.normalizePlayUrl(raw);
        window.open(normalized, '_blank', 'noopener,noreferrer');
      }
    }
  },

  mounted() {
    // 页面刷新后恢复上次播放
    this.applyVideoUrl();
  },
};
</script>

<style scoped>
.el-carousel__item:nth-child(2n) {
  background-color: #99a9bf;
}

.el-carousel__item:nth-child(2n + 1) {
  background-color: #d3dce6;
}

/* 父容器，设置为 flex 布局 */
.container {
  display: flex;
  justify-content: space-between; /* 左右内容间留出空间 */
  align-items: flex-start;
  gap: var(--app-gap);
}

/* 左侧内容占据大部分空间 */
.left-content {
  flex: 1 1 520px;
  min-width: 0;
}

/* 图片样式 */
.carousel-image {
  width: 100%;
  height: 100%;
  object-fit: cover; /* 保证图片不变形 */
}

/* 右侧留出的空间放置表单 */
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

/* 调整走马灯样式 */
.carousel-item-title {
  font-size: 1.5rem;
  display: flex;
  justify-content: center;
  color: #475669;
  opacity: 0.75;
  line-height: 300px;
  margin: 0;
  text-align: center;
}

/* 修改按钮的样式 */
.start-button {
  font-size: 18px; /* 设置按钮文字大小 */
  border-radius: 5px; /* 设置圆角 */
  font-weight: 700; /* 加粗 */
  color: #fff; /* 按钮文字颜色 */
  background-color: #529a55; /* 自定义按钮背景颜色 */
  border: none; /* 去掉边框 */
  border-radius: 5px; /* 设置圆角 */
  padding: 10px 20px; /* 设置内边距 */
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1); /* 添加阴影 */
  display: block;
  margin-bottom: 20px; /* 按钮和走马灯之间的间距 */
}

/* 视频播放按钮样式 */
.play-button {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  background-color: rgba(0, 0, 0, 0.5); /* 半透明背景 */
  border-radius: 50%;
  width: 60px;
  height: 60px;
  display: flex;
  justify-content: center;
  align-items: center;
  cursor: pointer;
}

.play-button i {
  font-size: 28px;
  color: white;
}

.play-button:hover {
  background-color: rgba(0, 0, 0, 0.7); /* 鼠标悬停时加深背景色 */
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
  letter-spacing: 0.5px; /* 字母间距 */
  margin-left: 10px;
  margin-top: auto;
  text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.2); /* 文字阴影 */
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
}

.center-text {
  text-align: center;
  font-size: 18px;
  margin-bottom: 10px;
}


/* 新增样式 */
.video-player-container {
  margin-top: 40px;
  padding: 20px;
  border: 1px solid #dcdcdc;
  background-color: #f5f5f5;
  border-radius: 8px;
}

.video-wrapper {
  margin-top: 20px;
  text-align: center;
}

.iframe-shell {
  margin-top: 12px;
  display: flex;
  justify-content: center;
}

.iframe-wrapper {
  width: 100%;
  max-height: 70vh;
  background: #000;
  overflow: hidden;
}

.iframe-wrapper iframe {
  width: 100%;
  height: 100%;
  border: 0;
}

.video-hint {
  margin-top: 10px;
  color: #666;
  font-size: 14px;
}

.center-text {
  text-align: center;
  font-size: 18px;
  margin-bottom: 10px;
}

/* Dialog widths on mobile portrait */
:deep(.recommend-dialog) {
  width: min(92vw, 520px) !important;
}

:deep(.player-dialog) {
  width: min(96vw, 1100px) !important;
}

@media (max-width: 768px) {
  .container {
    flex-direction: column;
  }
  .right-content {
    align-items: stretch;
  }
  .box-card {
    height: auto;
    padding: 10px 0;
  }
  :deep(.player-dialog) {
    margin-top: 8vh;
  }
}
</style>

<style scoped>
.recommend-row {
  display: flex;
  align-items: flex-start;
  margin-bottom: 12px;
}

.recommend-btn {
  flex: 0 0 auto;
  min-width: 72px;
}

.recommend-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-left: 10px;
}
</style>
