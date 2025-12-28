<template>
    <div class="parallax-container" @scroll="onScroll">
      <div class="parallax-background" :style="{ backgroundPositionY: backgroundPositionY }"></div>
      <div class="parallax-content">
        <slot></slot>
      </div>
    </div>
  </template>
  
  <script>
  export default {
    data() {
      return {
        scrollPosition: 0,
      };
    },
    computed: {
      backgroundPositionY() {
        return `${this.scrollPosition * 0.5}px`; // 调整背景图像的滚动速度
      },
    },
    methods: {
      onScroll() {
        this.scrollPosition = window.scrollY; // 获取当前滚动位置
      },
    },
    mounted() {
      window.addEventListener('scroll', this.onScroll); // 添加滚动事件监听
    },
    beforeUnmount() {
      window.removeEventListener('scroll', this.onScroll); // 清理事件监听
    },
  };
  </script>
  
  <style scoped>
  .parallax-container {
    position: relative;
    height: 100vh;
    overflow: hidden;
  }
  .parallax-background {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 100%;
    background-image: url('../../assets/images/login-bg.jpg'); /* 替换为你的背景图像 */
    background-size: cover;
    background-repeat: no-repeat;
    transition: background-position 0.1s ease-out;
  }
  .parallax-content {
    position: relative;
    z-index: 1;
    color: white;
    padding: 20px;
  }
  </style>