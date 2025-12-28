<template>
  <el-menu
    :default-active="activeMenu"
    router
    class="aside-menu"
  >
    <el-menu-item :index="resolvePath('eeg')">
      脑电采集
    </el-menu-item>

    <el-menu-item :index="resolvePath('video')">
      视频调控
    </el-menu-item>

    <el-menu-item :index="resolvePath('game')">
      游戏调控
    </el-menu-item>

    <el-menu-item :index="resolvePath('music')">
      音乐调控
    </el-menu-item>
  </el-menu>
</template>

<script>
export default {
    methods: {
        resolvePath(subRoute) {
            return `/home/${subRoute}`
        }
    },

    computed: {
        activeMenu() {
            return this.$route.path // 动态获取当前激活的路由路径
        }
    }
}
</script>

<style scoped>
.aside-menu {
  border-right: none;
  background: transparent;
  --el-menu-bg-color: transparent;
  --el-menu-text-color: var(--app-aside-text);
  --el-menu-active-color: var(--app-aside-active);
  --el-menu-hover-bg-color: rgba(255, 255, 255, 0.07);
}

:deep(.el-menu-item) {
  height: 48px;
  margin: 6px 10px;
  border-radius: 12px;
  justify-content: flex-start;
  padding: 0 14px;
}

:deep(.el-menu-item.is-active) {
  background: rgba(125, 220, 147, 0.16);
}
</style>
