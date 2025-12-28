<template>
  <div class="header-container">
    <el-button
      v-if="showMenuToggle"
      class="menu-button"
      text
      type="primary"
      aria-label="打开菜单"
      @click="$emit('toggle-menu')"
    >
      <el-icon><Menu /></el-icon>
    </el-button>
    <img :src="logoImage" class="logo" alt="Logo" />
    <el-text class="text">生态化调控系统</el-text>
    <el-popover
      v-model:visible="logoutVisible"
      trigger="click"
      placement="bottom-end"
      :width="compact ? 128 : 140"
      @show="goInfo"
    >
      <template #reference>
        <el-button :size="compact ? 'small' : 'default'" type="success" class="info-button">个人信息</el-button>
      </template>
      <el-button type="danger" size="small" class="logout-button" @click="logout">退出登录</el-button>
    </el-popover>
  </div>
</template>

<script>
import logoImage from '../../assets/images/logo.jpg'
import { Menu } from '@element-plus/icons-vue'
export default {
  components: {
    Menu
  },
  emits: ['toggle-menu'],
  props: {
    showMenuToggle: { type: Boolean, default: false },
    compact: { type: Boolean, default: false }
  },
  data() {
    return {
      logoImage,
      logoutVisible: false,
    }
  },
  methods: {
    goInfo() {
      // 点击个人信息按钮：先进入个人信息页，再弹出“退出登录”按钮
      try {
        const p = this.$router.push('/home/info')
        if (p && typeof p.catch === 'function') p.catch(() => {})
      } catch (e) {
        // ignore
      }
    },
    logout() {
      try {
        localStorage.removeItem('currentUser')
        localStorage.removeItem('lastMusicFilePath')
      } catch (e) {
        // ignore
      }
      this.logoutVisible = false
      try {
        const p = this.$router.replace('/login')
        if (p && typeof p.catch === 'function') p.catch(() => {})
      } catch (e) {
        // ignore
      }
    }
  }
}
</script>

<style scoped>
.header-container {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  height: 100%;
  padding: 0 var(--app-gap);
  background: var(--app-surface);
  border-bottom: 1px solid var(--app-border);
}

.menu-button {
  margin-left: -8px;
  padding: 8px 10px;
}

.logo {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  object-fit: cover;
  box-shadow: var(--app-shadow-sm);
}

.text {
  color: var(--app-text);
  line-height: 1.1;
  font-size: clamp(18px, 2.2vw, 28px);
  font-weight: 700;
  letter-spacing: 0.4px;
  white-space: nowrap;
}

.info-button {
  margin-left: auto;
}

.logout-button {
  width: 100%;
}

@media (max-width: 768px) {
  .header-container {
    gap: 10px;
    padding: 0 var(--app-gap);
  }
  .logo {
    width: 34px;
    height: 34px;
    border-radius: 9px;
  }
}
</style>
