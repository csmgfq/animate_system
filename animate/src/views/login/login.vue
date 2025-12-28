<template>
    <div class="login-page">
        <CursorParticles/>
        <ClickBoom/>
        <div class="parallax">
            <img src="../../assets/parallax/hill1.png" id="hill1" :style="{ top: hill1Top + 'px' }">
            <img src="../../assets/parallax/hill2.png" id="hill2">
            <img src="../../assets/parallax/hill3.png" id="hill3">
            <img src="../../assets/parallax/hill4.png" id="hill4" :style="{ left: hill4Left + 'px' }">
            <img src="../../assets/parallax/hill5.png" id="hill5" :style="{ left: hill5Left + 'px' }">
            <img src="../../assets/parallax/tree.png" id="tree">
            <h2 @click="scrollToNextPage" id="text" :style="{ marginTop: textMarginTop + 'px', opacity: buttonOpacity }">
                EEG System
            </h2>
            <img src="../../assets/parallax/leaf.png" id="leaf" :style="{ top: leafTop + 'px', left: leafLeft + 'px' }">
            <img src="../../assets/parallax/plant.png" id="plant">
        </div>
        <div id="nextPage" class="sec">
            <h2>生态化智能调控系统</h2>
            <LoginFormV2/>
        </div>
    </div>
</template>

<script>
import CursorParticles from '../../components/mouse/cursor-particles.vue'
import ClickBoom from '../../components/mouse/click-boom.vue'
import LoginFormV2 from '../../components/login/login-form-v2.vue'

export default {
    components: {
        CursorParticles, 
        ClickBoom, 
        LoginFormV2
    }, 
    data() {
        return {
            textMarginTop: 0,
            buttonOpacity: 1,  // 新增透明度属性
            leafTop: 0,
            leafLeft: 0,
            hill1Top: 0,
            hill4Left: 0,
            hill5Left: 0
        }
    },
    methods: {
        handleScroll() {
            const value = window.scrollY
            this.textMarginTop = value * 1.5
            this.leafTop = value * -1.5
            this.leafLeft = value * 1.5
            this.hill1Top = value * 0.5
            this.hill4Left = value * -1.5
            this.hill5Left = value * 1.5

            // 根据滚动的距离调整透明度
            const maxScroll = 300; // 设置最大滚动距离
            this.buttonOpacity = Math.max(0, 1 - value / maxScroll); // 计算透明度
        }, 
        scrollToNextPage() {
            const nextPage = document.getElementById("nextPage")
            nextPage.scrollIntoView({behavior: "smooth"})
        }
    }, 
    mounted() {
        window.addEventListener('scroll', this.handleScroll)
    },
    beforeUnmount() {
        window.removeEventListener('scroll', this.handleScroll)
    }
}
</script>

<style scoped>
/* 全局样式设置 */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box; /* 使内边距和边框包含在元素的总宽度和高度内 */
  font-family: 'Poppins', sans-serif;
} 

/* 防止动画元素撑开页面宽度 */
.login-page {
  overflow-x: hidden;
  width: 100%;
}

.parallax {
  position: relative; /* 作为定位参考的祖先元素 */
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100vh;
  height: 100svh;
  height: 100dvh;
  overflow: hidden; /* 隐藏移出视口的图片 */
}

/* 鼠标悬停时的效果 */
#text:hover {
  color: #3498db !important; /* 改变颜色为蓝色 */
  text-shadow: 2px 2px 5px rgba(0, 0, 0, 0.3); /* 添加阴影效果 */
}

#text {
  position: absolute; /* 相对于 .parallax 进行定位 */
  font-size: clamp(36px, 10vw, 88px);
  color: #fff;
  text-shadow: 2px 2px 4px rgba(0, 0, 0, .2);
  cursor: pointer !important; /* 鼠标悬停显示为手形 */
  transition: color 0.3s ease, opacity 0.3s ease; /* 添加过渡效果 */
  z-index: 1;
}

.parallax img {
  position: absolute; /* 相对于 .parallax 进行定位 */
  width: 100%; /* 确保图片的宽度填满容器 */
  height: 100%; /* 确保图片的高度填满容器 */
  object-fit: cover; /* 确保图片按照容器大小裁剪和缩放 */
}

.sec {
    display: flex;
    justify-content: center;
    flex-direction: column;
    align-items: center;
    position: relative;
    background: var(--app-aside-bg);
    padding: clamp(24px, 7vw, 96px);
}

.sec h2 {
    font-size: clamp(22px, 5vw, 44px);
    color: #fff;
    margin-bottom: 10px;
}

@media (max-width: 768px) {
  .sec h2 {
    text-align: center;
    margin-bottom: 14px;
  }
}
</style>
