<template>
    <div class="captcha-container">
        <canvas ref="captchaCanvas" width="120" height="40" @click="generateCaptcha"></canvas>
    </div>
</template>

<script>
export default {
    data() {
        return {
            captchaText: '' // 验证码文本
        }
    }, 
    mounted() {
        this.generateCaptcha() // 初始化时生成验证码
    }, 
    methods: {
        generateCaptcha() {
            const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
            this.captchaText = ''

            for (let i = 0; i < 4; i++) {
                this.captchaText += chars.charAt(Math.floor(Math.random() * chars.length))
            }

            this.drawCaptcha()
        }, 
        drawCaptcha() {
            const canvas = this.$refs.captchaCanvas
            const ctx = canvas.getContext('2d')

            // 清空canvas
            ctx.clearRect(0, 0, canvas.width, canvas.height)

            // 随机背景颜色
            const bgColor = `rgb(${Math.random() * 255}, ${Math.random() * 255}, ${Math.random() * 255})`
            ctx.fillStyle = bgColor
            ctx.fillRect(0, 0, canvas.width, canvas.height)

            // 逐个字符绘制
            ctx.font = '24px Arial'
            for (let i = 0; i < this.captchaText.length; i++) {
                ctx.fillStyle = `rgb(${Math.random() * 255}, ${Math.random() * 255}, ${Math.random() * 255})`
                const x = 15 + i * 25 + Math.random() * 5; 
                const y = 30 + Math.random() * 10; 
                ctx.fillText(this.captchaText[i], x, y);
            }

            // 添加更多复杂的干扰图案
            for (let i = 0; i < 10; i++) {
                const shapeType = Math.random() > 0.5 ? 'line' : 'circle';
                ctx.strokeStyle = `rgba(0, 0, 0, ${Math.random()})`;

                if (shapeType === 'line') {
                    ctx.lineWidth = Math.random() * 2; // 随机线条宽度
                    ctx.beginPath();
                    ctx.moveTo(Math.random() * canvas.width, Math.random() * canvas.height);
                    ctx.lineTo(Math.random() * canvas.width, Math.random() * canvas.height);
                    ctx.stroke();
                } else {
                    ctx.lineWidth = Math.random() * 2;
                    ctx.beginPath();
                    const x = Math.random() * canvas.width;
                    const y = Math.random() * canvas.height;
                    const radius = Math.random() * 15 + 5; // 随机半径
                    ctx.arc(x, y, radius, 0, Math.PI * 2);
                    ctx.stroke();
                }
            }
        }
    }
}
</script>

<style scoped>
.captcha-container {
  display: flex;
  align-items: center;
  margin-left: 60px;
  /* margin-top: 10px; */
}

canvas {
  border: 0px solid #ddd;
  margin-left: 20px;
  /* margin-top: -15px; */
}
</style>