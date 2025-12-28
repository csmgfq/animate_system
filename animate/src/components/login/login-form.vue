<template>
  <div>
    <el-card class="box-card">
      <!-- 头部logo图片+文字部分 -->
      <template #header>
        <div class="header">
          <img :src="logoImage" alt="科技飞鸟" class="header-image" />
          <span class="header-text">欢迎登录</span>
        </div>
      </template>
      <!-- 登录表单部分 -->
      <el-form ref="form" :model="form" :rules="rules" label-width="0px">
        <!-- 用户名 -->
        <el-form-item label="" prop="username">
          <el-row>
            <el-col :span="4">
              <!-- 用户头像 -->
              <img :src="userImage" class="username-image" alt="用户名图标" />
            </el-col>
            <el-col :span="20">
              <!-- 用户名输入框 -->
              <el-input
                v-model="form.username"
                placeholder="用户名"
                autocomplete="on"
                class="input"
              ></el-input>
            </el-col>
          </el-row>
        </el-form-item>
        <!-- 密码 -->
        <el-form-item label="" prop="password">
          <el-row>
            <el-col :span="4">
              <!-- 密码图像 -->
              <img :src="lockImage" class="password-image" alt="密码图标" />
            </el-col>
            <el-col :span="20">
              <!-- 密码输入框 -->
              <el-input
                v-model="form.password"
                type="password"
                placeholder="密码"
                autocomplete="on"
                @keyup.enter.native="handleLogin"
                class="input"
              ></el-input>
            </el-col>
          </el-row>
        </el-form-item>
        <!-- 还没有账号？注册 -->
        <el-form-item>
          <div class="register">
            <span class="register-text">还没有账号?&nbsp;</span>
            <el-link class="register-link" @click="goToRegister">注册</el-link>
          </div>
        </el-form-item>
        <!-- 登录按钮 -->
        <el-form-item>
          <el-button
            type="primary"
            @click.native.prevent="handleLogin"
            class="login-button"
            >登录</el-button
          >
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script>
import { ElMessage } from 'element-plus'
import logoImage from '../../assets/images/logo.jpg'
import userImage from '../../assets/images/user.svg'
import lockImage from '../../assets/images/lock.svg'

export default {
  components: {},

    data() {
        // 验证用户名
        const validateUserName = (rule, value, callback) => {
            if (!value) {
                callback(new Error('用户名不能为空！'))
            } else {
                callback()
            }
        }
        // 验证密码
        const validatePassword = (rule, value, callback) => {
            if (!value) {
                callback(new Error('密码不能为空！'));
            } else {
                callback()
            }
        }
        return {
            logoImage: logoImage,
            userImage: userImage,
            lockImage: lockImage,
            // 初始化输入格式
            form: {
                username: '',
            password: ''
            },
            // 验证输入规则
            rules: {
                username: [{ validator: validateUserName, trigger: 'blur' }],
            password: [{ validator: validatePassword, trigger: 'blur' }]
            }
        }
    },

    methods: {
        // 点击登录按钮进行校验
        handleLogin() {
            this.$refs.form.validate((valid) => {
                if (valid) {
                    ElMessage({
                        message: '登录成功',
                        type: 'success',
                        showClose: true,
                        duration: 2000,
                        center: true
                    })
                } else {
                    ElMessage({
                        message: '登录失败，请检查输入！',
                        type: 'error',
                        showClose: true,
                        duration: 2000,
                        center: true
                    })
                }
            })
        },
        // 点击登录进行跳转进行注册
        goToRegister() {
          this.$router.push({ name: 'login' })
        }
    }
}
</script>

<style scoped>
.login {
    display: flex;
    justify-content: flex-end;
    align-items: center;
    text-align: center;
    margin: 20px;
    width: 350px;
    border-radius: 10px;
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
}

.header {
    display: flex;
    align-items: center; /* 垂直居中对齐 */
}

.header-image {
    width: 80px;
    height: auto;
    margin-right: 50px;
    margin-top: 0px;
}

.header-text {
    font-size: 28px;
    font-weight: 700;
    color: #544d4d;
    letter-spacing: 0.5px; /* 字母间距 */
    margin-left: -10px;
    text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.2); /* 文字阴影 */
}

.username-image {
    width: 32px;
    height: auto;
    margin-right: 0px;
}

.password-image {
    width: 32px;
    height: auto;
    margin-right: 0px;
}

.input {
    height: 40px;
    width: 220px;
}

.captcha-input {
    height: 40px;
    width: 100px;
    margin-left: 40px;
}

.captcha-image {
    display: flex;
    align-items: center;
    justify-content: center;
}

.register {
    display: flex;
    align-items: center;
}

.register-text {
    margin-top: -10px;
    margin-left: 40px;
    font-size: 14px; /* 设置字体大小 */
    color: #544d4d; /* 设置字体颜色 */
}

.register-link {
    margin-top: -10px;
    font-size: 14px; /* 设置字体大小 */
    color: #5045e5; /* 设置字体颜色 */
}

/* 修改按钮的样式 */
.login-button {
    font-size: 18px; /* 设置按钮文字大小 */
    font-weight: 700; /* 加粗 */
    color: #fff; /* 按钮文字颜色 */
    background-color: #529a55; /* 自定义按钮背景颜色 */
    border: none; /* 去掉边框 */
    border-radius: 5px; /* 设置圆角 */
    padding: 10px 20px; /* 设置内边距 */
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1); /* 添加阴影 */
    display: block;
    margin: 0 auto;
}

/* 使用深度选择器确保覆盖 Element Plus 的样式 */
:deep(.el-form-item__error) {
  color: #F56C6C;
  font-size: 12px;
  line-height: 1;
  padding: 4px;
  margin-left: 40px; /* 调整错误提示距离左侧的间距 */
  position: absolute;
}
</style>
