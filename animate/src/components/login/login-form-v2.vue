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
        <el-form-item prop="username">
          <!-- 用户名输入框 -->
          <el-input
            v-model="form.username"
            placeholder="用户名"
            tabindex="1"
            autocomplete="on"
            class="input"
          >
            <!-- 用户矢量图 -->
            <template #prefix>
              <el-icon>
                <User></User>
              </el-icon>
            </template>
          </el-input>
        </el-form-item>

        <el-form-item prop="password">
          <!-- 密码输入框 -->
          <el-input
            v-model="form.password"
            :type="passwordType"
            placeholder="密码"
            tabindex="2"
            autocomplete="on"
            @keyup.enter.native="handleLogin"
            class="input"
          >
            <!-- 密码矢量图 -->
            <template #prefix>
              <el-icon>
                <Lock></Lock>
              </el-icon>
            </template>
            <template #suffix>
              <!-- 密码显示眼 -->
              <el-icon @click="showPassword">
                <Hide v-if="passwordType === 'password'"></Hide>
                <View v-else></View>
              </el-icon>
            </template>
          </el-input>
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
            :loading="loading"
            type="primary"
            @click.native.prevent="handleLogin"
            class="login-button"
          >
            <span v-if="!loading">登录</span>
            <span v-else>登录中...</span>
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 注册弹窗：不再使用单独的注册页面 -->
    <el-dialog v-model="registerVisible" class="register-dialog" title="注册" width="420px">
      <el-form
        ref="registerFormRef"
        :model="registerForm"
        :rules="registerRules"
        label-width="0px"
      >
        <el-form-item prop="username">
          <el-input v-model="registerForm.username" placeholder="用户名" autocomplete="on" class="input" />
        </el-form-item>
        <el-form-item prop="password">
          <el-input v-model="registerForm.password" type="password" placeholder="密码" autocomplete="on" class="input" />
        </el-form-item>
        <el-form-item prop="confirmPassword">
          <el-input
            v-model="registerForm.confirmPassword"
            type="password"
            placeholder="确认密码"
            autocomplete="on"
            class="input"
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="registerVisible = false">取消</el-button>
        <el-button type="primary" :loading="registerLoading" @click="handleRegister">注册</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { ElMessage } from 'element-plus'
import axios from 'axios'
import { getApiBaseUrl } from '../../api/baseUrl'
import logoImage from '../../assets/images/logo.jpg'
import { User, Lock, View, Hide } from '@element-plus/icons-vue'

export default {
  components: {
    User,
    Lock,
    View,
    Hide,
  },

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

            // 初始化输入格式
            form: {
              username: '',
              password: '',
            },
            // 验证输入规则
            rules: {
                username: [{ validator: validateUserName, trigger: 'blur' }],
                password: [{ validator: validatePassword, trigger: 'blur' }],
            },
            passwordType: 'password',
            loading: false,

            // 注册弹窗
            registerVisible: false,
            registerLoading: false,
            registerForm: {
              username: '',
              password: '',
              confirmPassword: ''
            },
            registerRules: {
              username: [{ validator: validateUserName, trigger: 'blur' }],
              password: [{ validator: validatePassword, trigger: 'blur' }],
              confirmPassword: [{
                validator: (rule, value, callback) => {
                  if (!value) return callback(new Error('请再次输入密码！'))
                  if (value !== this.registerForm.password) return callback(new Error('两次密码不一致！'))
                  callback()
                },
                trigger: 'blur'
              }]
            }
        }
    },

    methods: {
      openRegister() {
        this.registerForm.username = this.form.username || ''
        this.registerForm.password = ''
        this.registerForm.confirmPassword = ''
        this.registerVisible = true
      },

      handleRegister() {
        this.$refs.registerFormRef.validate(async (valid) => {
          if (!valid) return
          this.registerLoading = true
          try {
            const base = getApiBaseUrl()
            await axios.post(`${base}/api/users/register`, {
              username: this.registerForm.username,
              account: this.registerForm.username,
              password: this.registerForm.password
            })
            ElMessage({
              message: '注册成功，请登录',
              type: 'success',
              showClose: true,
              duration: 2000,
              center: true
            })
            this.form.username = this.registerForm.username
            this.registerVisible = false
          } catch (e) {
            const msg = e?.response?.data?.msg || e?.response?.data?.message || '注册失败'
            ElMessage({
              message: msg,
              type: 'error',
              showClose: true,
              duration: 2500,
              center: true
            })
          } finally {
            this.registerLoading = false
          }
        })
      },

        // 点击登录按钮进行校验
      handleLogin() {
        this.$refs.form.validate(async (valid) => {
          if (!valid) {
            ElMessage({
              message: '登录失败，请检查输入！',
              type: 'error',
              showClose: true,
              duration: 2000,
              center: true
            })
            return
          }

          this.loading = true

          // 离线管理员账户：不需要连接后端即可登录
          const offlineAdmin = {
            username: 'admin',
            password: 'admin123'
          }
          if (this.form.username === offlineAdmin.username && this.form.password === offlineAdmin.password) {
            const adminUser = {
              id: 0,
              username: 'admin',
              account: 'admin',
              is_admin: true,
              gender: '',
              occupation: '系统管理员',
              birthday: '',
              phone: '',
              email: ''
            }
            localStorage.setItem('currentUser', JSON.stringify(adminUser))
            localStorage.setItem('lastLoginUsername', 'admin')
            ElMessage({
              message: '管理员登录成功（离线模式）',
              type: 'success',
              showClose: true,
              duration: 2000,
              center: true
            })
            this.loading = false
            this.$router.push({ name: 'home' })
            return
          }

          // 正常后端登录
          try {
            const base = getApiBaseUrl()
            const resp = await axios.post(`${base}/api/users/login`, {
              username: this.form.username,
              password: this.form.password
            })
            const user = resp?.data?.data?.user
            if (user) {
              localStorage.setItem('currentUser', JSON.stringify(user))
            }
            try {
              const u = (this.form.username || '').trim()
              if (u) localStorage.setItem('lastLoginUsername', u)
            } catch (e) {
              // ignore
            }
            ElMessage({
              message: '登录成功',
              type: 'success',
              showClose: true,
              duration: 2000,
              center: true
            })
            this.$router.push({ name: 'home' })
          } catch (e) {
            const msg = e?.response?.data?.msg || e?.response?.data?.message || '登录失败，请检查账号或后端服务'
            ElMessage({
              message: msg,
              type: 'error',
              showClose: true,
              duration: 2500,
              center: true
            })
          } finally {
            this.loading = false
          }
        })
      },
        showPassword() {
            if (this.passwordType === 'password') {
                this.passwordType = ''
            } else {
                this.passwordType = 'password'
            }
        },
        // 点击注册进行跳转进行注册
        goToRegister() {
          this.openRegister()
        }
    },

    mounted() {
      try {
        const last = localStorage.getItem('lastLoginUsername')
        if (last && !this.form.username) {
          this.form.username = String(last)
        }
      } catch (e) {
        // ignore
      }
    }
}
</script>

<style scoped>
.login {
    display: flex;
    justify-content: flex-end;
    align-items: center;
    width: 100%;
    min-height: 100vh;
    position: relative;
    overflow: hidden; /* 隐藏溢出的部分 */
}

.box-card {
    padding: 20px;
    text-align: center;
    margin: 20px;
    width: min(420px, 92vw);
    border-radius: var(--app-radius);
    border: 1px solid var(--app-border);
    box-shadow: var(--app-shadow);
}

.header {
    display: flex;
    align-items: center; /* 垂直居中对齐 */
}

.header-image {
    width: 72px;
    height: auto;
    margin-right: 18px;
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

/* 输入框样式 */
.input {
    height: 40px;
    width: 100%;
    padding-left: 0;
}

.register {
    display: flex;
    align-items: center;
}

.register-text {
    margin-top: -10px;
    margin-left: 4px;
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
    border-radius: 12px; /* 设置圆角 */
    padding: 10px 20px; /* 设置内边距 */
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1); /* 添加阴影 */
    display: block;
    margin: 0 auto;
    width: 100%;
}

:deep(.register-dialog) {
   width: min(92vw, 420px) !important;
 }

@media (max-width: 768px) {
  .header-image {
    width: 60px;
  }
  .header-text {
    font-size: 24px;
  }
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
