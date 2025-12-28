<!-- Click-Boom.vue 实现点击出现爆炸-->
<template>
    <canvas ref="fireworkCanvas" class="firework-canvas"></canvas>
</template>

<script>
export default {
    data() {
        return {
            balls: [], 
            longPressed: false, 
            longPressTimeout: null, 
            multiplier: 0, 
            colors: ["#F73859", "#14FFEC", "#00E0FF", "#FF99FE", "#FAF15D"],
            ctx: null, 
            rafId: null,
        }
    }, 

    methods: {
        showEffect() {
            this.ctx = this.$refs.fireworkCanvas.getContext("2d")
            this.updateSize()
            window.addEventListener("resize", this.updateSize, false)
            this.loop()
        }, 
        updateSize() {
            const canvas = this.$refs.fireworkCanvas
            canvas.width = window.innerWidth * 2
            canvas.height = window.innerHeight * 2
            canvas.style.width = window.innerWidth + 'px'
            canvas.style.height = window.innerHeight + 'px'
            // 避免 resize 时重复 scale 导致坐标系被累计放大
            this.ctx.setTransform(1, 0, 0, 1, 0, 0)
            this.ctx.scale(2, 2)
        }, 
        handleMouseDown(e) {
            this.pushBalls(this.randBetween(10, 20), e.clientX, e.clientY)
            document.body.classList.add("is-pressed")
            this.longPressTimeout = setTimeout(() => {
                this.longPressed = true
            }, 500)
        }, 
        handleMouseUp(e) {
            clearTimeout(this.longPressTimeout)
            if (this.longPressed) {
                document.body.classList.remove("is-longpress")
                this.pushBalls(
                    this.randBetween(50 + Math.ceil(this.multiplier), 100 + Math.ceil(this.multiplier)), 
                    e.clientX, 
                    e.clientY
                )
                this.longPressed = false
            }
            document.body.classList.remove("is-pressed")
        }, 
        // handleMouseMove(e) {
        //     const pointer = this.$refs.pointer
        //     pointer.style.top = e.clientY + 'px'
        //     pointer.style.left = e.clientX + 'px'
        // }, 
        pushBalls(count, x, y) {
            for (let i = 0; i < count; i++) {
                this.balls.push(this.createBall(x, y))
            }
        }, 
        createBall(x, y) {
            const angle = Math.PI * 2 * Math.random()
            const multiplier = this.longPressed 
            ? this.randBetween(10 + this.multiplier, 12 + this.multiplier)
            : this.randBetween(4, 8) // 调整为更小的粒子
            return {
                x, 
                y, 
                vx: (multiplier + Math.random() * 0.5) * Math.cos(angle), 
                vy: (multiplier + Math.random() * 0.5) * Math.sin(angle), 
                r: this.randBetween(3, 6) + Math.random(), // 粒子的半径范围减小
                color: this.colors[Math.floor(Math.random() * this.colors.length)], 
                angle
            }
        }, 
        updateBalls() {
            this.balls = this.balls.filter(ball => {
                if (ball.r <= 0) return false // 如果半径小于等于0，删除粒子
                
                // 更新粒子位置和速度
                ball.x += ball.vx
                ball.y += ball.vy
                ball.vx *= 0.9
                ball.vy *= 0.9
                ball.r -= 0.3

                // 检查粒子是否在画布边界内
                const isInsideCanvas = (ball.x - ball.r > 0 && ball.x + ball.r < window.innerWidth &&
                                        ball.y - ball.r > 0 && ball.y + ball.r < window.innerHeight)
                
                return isInsideCanvas // 只保留在画布内的粒子
            })
        }, 
        randBetween(min, max) {
            return Math.floor(Math.random() * (max - min + 1)) + min
        }, 
        loop() {
            this.ctx.clearRect(0, 0, window.innerWidth, window.innerHeight) // 清除画布
            this.balls.forEach(ball => {
                // 只绘制半径大于 0 的粒子
                if (ball.r > 0) {
                    this.ctx.fillStyle = ball.color
                    this.ctx.beginPath()
                    this.ctx.arc(ball.x, ball.y, ball.r, 0, Math.PI * 2, false)
                    this.ctx.fill()
                }
            })
            if (this.longPressed) this.multiplier += 0.2
            else if (this.multiplier > 0) this.multiplier -= 0.4
            this.updateBalls()
            this.rafId = requestAnimationFrame(() => this.loop())
        }
    }, 
    mounted() {
        try {
            const isTouch = window.matchMedia && window.matchMedia('(hover: none), (pointer: coarse)').matches
            if (isTouch) return
        } catch (e) {
            // ignore
        }
        this.showEffect()
        window.addEventListener("mousedown", this.handleMouseDown)
        window.addEventListener("mouseup", this.handleMouseUp)
        // window.addEventListener("mousemove", this.handleMouseMove)
    }, 
    beforeUnmount() {
        window.removeEventListener("mousedown", this.handleMouseDown)
        window.removeEventListener("mouseup", this.handleMouseUp)
        // window.removeEventListener("mousemove", this.handleMouseMove)
        window.removeEventListener("resize", this.updateSize)

        if (this.rafId) {
            cancelAnimationFrame(this.rafId)
            this.rafId = null
        }
    }
}
</script>

<style scoped>
.firework-canvas {
    position: fixed;
    top: 0;
    left: 0;
    z-index: 99999;
    pointer-events: none;
}
</style>
