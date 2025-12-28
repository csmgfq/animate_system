<template>
  <div class="container">
    <el-row :gutter="20">
      <el-col :xs="24" :sm="12">
        <el-card class="box" style="background-color: #f5f5f5;">
          <img
            :src="getImageUrl(0)"
            alt="Image"
            class="image"
          />
          <el-button type="primary" >{{ items[0].buttonText }}</el-button>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="12">
        <el-card class="box" style="background-color: #f5f5f5;">
          <img
            :src="getImageUrl(1)"
            alt="Image"
            class="image"
          />
          <el-button type="primary">{{ items[1].buttonText }}</el-button>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script>
export default {
  data() {
    return {
      items: [
        { buttonText: '运动式游戏调控--星海寻真' },
        { buttonText: '呼吸式游戏调控--呼吸放松' },
      ],
    };
  },
  methods: {
    getImageUrl(index) {
      return require(`@/assets/ARandVRPhoto/game${index + 1}.jpg`);
    },
  },
};
</script>

<style scoped>
.container {
  padding: var(--app-gap);
  width: 100%; /* 确保容器宽度为100% */
  box-sizing: border-box;
}

.box {
  text-align: center;
  border-radius: 20px;
  border: 1px solid var(--app-border);
  box-shadow: var(--app-shadow-sm);
  margin: 0; /* 使用 el-row gutter 控制间距，避免额外 margin 撑出横向滚动 */
  width: 100%;
  min-width: 0;
  max-width: 100%;
  min-height: 320px;
  height: auto;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  gap: 14px;
  padding: var(--app-gap);
  box-sizing: border-box;
}

.image {
  width: 100%;
  border-radius: 20px;
  height: auto;
  max-width: 100%;
  margin-bottom: 0;
}

@media (max-width: 768px) {
  .box {
    min-height: 240px;
    border-radius: 16px;
  }
  .image {
    border-radius: 16px;
  }
}
</style>
