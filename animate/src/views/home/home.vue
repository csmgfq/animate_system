<template>
  <div class="app-shell safe-area">
    <el-container class="app-shell__container">
      <el-header class="app-shell__header">
        <Header
          :compact="isMobile"
          :showMenuToggle="isMobile"
          @toggle-menu="sidebarOpen = true"
        />
      </el-header>

      <el-container class="app-shell__body">
        <el-aside v-show="!isMobile" width="240px" class="app-shell__aside">
          <Aside />
        </el-aside>

        <el-main class="app-shell__main">
          <CursorParticles v-if="!isTouch" />
          <ClickBoom v-if="!isTouch" />
          <router-view v-slot="{ Component }">
            <keep-alive include="EegControl">
              <component :is="Component" />
            </keep-alive>
          </router-view>
        </el-main>
      </el-container>
    </el-container>

    <el-drawer
      v-model="sidebarOpen"
      :with-header="false"
      direction="ltr"
      size="78%"
      class="app-shell__drawer"
    >
      <div class="drawer-head">
        <div class="drawer-title">菜单</div>
        <el-button class="drawer-close" text type="primary" aria-label="关闭菜单" @click="sidebarOpen = false">
          <el-icon><Close /></el-icon>
        </el-button>
      </div>
      <Aside />
    </el-drawer>
  </div>
</template>

<script>
import CursorParticles from '../../components/mouse/cursor-particles.vue'
import ClickBoom from '../../components/mouse/click-boom.vue'
import Aside from '../../components/layout/aside.vue'
import Header from '../../components/layout/header.vue'
import { Close } from '@element-plus/icons-vue'

export default {
    components: {
        CursorParticles,
        ClickBoom,
        Aside,
        Header,
        Close
    },
    data() {
      return {
        isMobile: false,
        isTouch: false,
        sidebarOpen: false,
      }
    },
    watch: {
      '$route.path'() {
        if (this.isMobile) this.sidebarOpen = false
      }
    },
    methods: {
      updateViewport() {
        try {
          // 断点调大到 1024px，让导航栏更早隐藏
          this.isMobile = window.matchMedia('(max-width: 1024px)').matches
          this.isTouch = window.matchMedia('(hover: none), (pointer: coarse)').matches
        } catch (e) {
          this.isMobile = window.innerWidth <= 1024
          this.isTouch = false
        }
        if (!this.isMobile) this.sidebarOpen = false
      },
    },
    mounted() {
      this.updateViewport()
      window.addEventListener('resize', this.updateViewport, { passive: true })
      window.addEventListener('orientationchange', this.updateViewport, { passive: true })
    },
    beforeUnmount() {
      window.removeEventListener('resize', this.updateViewport)
      window.removeEventListener('orientationchange', this.updateViewport)
    }
}
</script>

<style scoped>
.app-shell {
  min-height: 100vh;
  min-height: 100dvh;
}

.app-shell__container {
  min-height: 100vh;
  min-height: 100dvh;
}

.app-shell__header {
  height: var(--app-header-h) !important;
  padding: 0;
  background: transparent;
}

.app-shell__body {
  min-height: 0;
}

.app-shell__aside {
  background: var(--app-aside-bg);
  color: var(--app-aside-text);
  border-right: 1px solid rgba(255, 255, 255, 0.08);
  overflow: auto;
}

.app-shell__main {
  background: transparent;
  padding: var(--app-gap);
  overflow: auto;
  min-height: 0;
}

.drawer-head {
  height: var(--app-header-h);
  display: flex;
  align-items: center;
  padding: 0 var(--app-gap);
  border-bottom: 1px solid var(--app-border);
  background: var(--app-surface);
}

.drawer-title {
  font-weight: 700;
  color: var(--app-text);
  letter-spacing: 0.2px;
}

.drawer-close {
  margin-left: auto;
  padding: 8px 10px;
}

:deep(.app-shell__drawer .el-drawer__body) {
  padding: 0;
  background: var(--app-aside-bg);
}
</style>
