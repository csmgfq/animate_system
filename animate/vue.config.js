const { defineConfig } = require('@vue/cli-service')
module.exports = defineConfig({
  // Electron 需要使用相对路径
  publicPath: './',
  // 避免对所有 node_modules 做 Babel 转译（会显著拖慢 serve/build）
  // 如确有需要，仅把需要转译的依赖名加到数组里。
  transpileDependencies: [],
  lintOnSave: false,
  // 关闭生产 sourcemap 可明显提升 build 速度（如需线上排查再开启）
  productionSourceMap: false,
  configureWebpack: {
    watchOptions: {
      ignored: /(^|[\\/])(node_modules|dist|audiocraft|musicgenmodel|models|__pycache__|\.ipynb_checkpoints|disusable|4\.36\.0|4\})($|[\\/])/,
    },
  },
  devServer: {
    proxy: {
      '/api': {
        target: process.env.VUE_APP_PROXY_TARGET || 'http://localhost:8088',
        changeOrigin: true,
      },
      '/static': {
        target: process.env.VUE_APP_PROXY_TARGET || 'http://localhost:8088',
        changeOrigin: true,
      },
    },
  },
})
