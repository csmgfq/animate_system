<!-- CursorParticles.vue 实现移动出现花火-->
<template>
    <div ref="container" class="js-cursor-container"></div>
</template>

<script>
class Particle {
        constructor(x, y, color, containerEl) {
        this.character = '*' // 粒子的字符样式
        this.lifeSpan = 50  // 粒子的生命周期
        this.initialStyles = {
            position: 'fixed', // 固定位置，不随滚动条移动
            display: 'inline-block', 
            top: '0px',
            left: '0px',
            pointerEvents: 'none', // 禁用鼠标交互
            touchAction: 'none', // 禁用触摸交互
            zIndex: '10000000', // 设置高的z-index，使其显示在最上层
            fontSize: '25px', // 粒子大小
            willChange: 'transform', // 优化CSS性能
        }
        this.velocity = { // 粒子的初始速度，x方向随机，y方向下落
            x: (Math.random() < 0.5 ? -1 : 1) * (Math.random() / 2),
            y: 1,
        }
        this.position = { x: x + 10, y: y + 10 }
        this.initialStyles.color = color
        this.element = document.createElement('span')
        this.element.innerHTML = this.character
        this.applyProperties(this.element, this.initialStyles)

        // 容器可能在路由切换/组件卸载后不存在，必须保护
        this.containerEl = containerEl
        if (this.containerEl && this.containerEl.appendChild) {
            this.containerEl.appendChild(this.element)
        }
    }

    update() {
        this.position.x += this.velocity.x
        this.position.y += this.velocity.y
        this.lifeSpan--
        this.element.style.transform = `translate3d(${this.position.x}px, ${this.position.y}px, 0) scale(${this.lifeSpan / 120})`
    }

    die() {
        if (this.element.parentNode) {
        this.element.parentNode.removeChild(this.element)
        }
    }

    applyProperties(target, properties) {
        for (let key in properties) {
        target.style[key] = properties[key]
        }
    }
}

export default {
    data() {
        return {
            particles: [],
            // 显示的粒子的颜色
            possibleColors: ['#D61C59', '#E7D84B', '#1B8798'],
            // window是浏览器中全局的 JavaScript 对象，代表浏览器窗口
            width: window.innerWidth,
            height: window.innerHeight,
            cursor: {
                x: 0,
                y: 0,
            },
            particlesInitialized: false,
            isActive: false,
            rafId: null,
        }
    },

    methods: {
        handleMouseMove(e) {
            this.cursor.x = e.clientX
            this.cursor.y = e.clientY

            if (!this.particlesInitialized) {
                this.show() // 只在第一次移动时初始化粒子效果
                this.particlesInitialized = true
            }

            this.addParticle(this.cursor.x, this.cursor.y, this.getRandomColor())
        },
        getRandomColor() {
            return this.possibleColors[Math.floor(Math.random() * this.possibleColors.length)]
        },
        show() {
            this.bindEvents()
            this.loop()
        },
        // 监听窗口变化事件，当浏览器窗口大小发生变化时，会调用onWindowResize方法
        bindEvents() {
            window.addEventListener('resize', this.onWindowResize)
        },
        onWindowResize() {
            this.width = window.innerWidth
            this.height = window.innerHeight
        },
        addParticle(x, y, color) {
            const containerEl = this.$refs.container
            if (!containerEl) return
            const particle = new Particle(x, y, color, containerEl)
            this.particles.push(particle)
        },
        loop() {
            if (!this.isActive) return
            this.rafId = requestAnimationFrame(() => this.loop())
            this.updateParticles()
        },
        updateParticles() {
            for (let i = this.particles.length - 1; i >= 0; i--) {
                this.particles[i].update()
                if (this.particles[i].lifeSpan < 0) {
                    this.particles[i].die()
                    this.particles.splice(i, 1)
                }
            }
        },
    },
    mounted() {// 生命周期钩子，会在组件挂载和销毁是自动调用
        try {
            const isTouch = window.matchMedia && window.matchMedia('(hover: none), (pointer: coarse)').matches
            if (isTouch) return
        } catch (e) {
            // ignore
        }
        this.isActive = true
        window.addEventListener('mousemove', this.handleMouseMove)
    },
    beforeUnmount() {
        this.isActive = false
        if (this.rafId) {
            cancelAnimationFrame(this.rafId)
            this.rafId = null
        }
        window.removeEventListener('mousemove', this.handleMouseMove)
        window.removeEventListener('resize', this.onWindowResize)

        // 清理残留粒子节点
        try {
            const containerEl = this.$refs.container
            if (containerEl) containerEl.innerHTML = ''
        } catch (e) {
            // ignore
        }
    },
}

</script>

<style scoped>
.js-cursor-container {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    pointer-events: none;
    overflow: hidden;
    z-index: 10000000;
}
</style>
