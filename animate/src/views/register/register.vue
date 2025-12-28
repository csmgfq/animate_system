<template>
  <div class="register">
    <el-card class="box-card">
      <template #header>
        <div class="header">
          <img :src="logoImage" alt="科技飞鸟" class="header-image" />
          <span class="header-text">欢迎注册</span>
        </div>
      </template>

      <el-form ref="formRef" :model="form" :rules="rules" label-width="0px">
        <el-form-item prop="username">
          <el-input v-model="form.username" placeholder="用户名" autocomplete="on" class="input">
            <template #prefix>
              <el-icon><User /></el-icon>
            </template>
          </el-input>
        </el-form-item>

        <el-form-item prop="password">
          <el-input v-model="form.password" type="password" placeholder="密码" autocomplete="on" class="input">
            <template #prefix>
              <el-icon><Lock /></el-icon>
            </template>
          </el-input>
        </el-form-item>

        <el-form-item prop="confirmPassword">
          <el-input v-model="form.confirmPassword" type="password" placeholder="确认密码" autocomplete="on" class="input">
            <template #prefix>
              <el-icon><Lock /></el-icon>
            </template>
          </el-input>
        </el-form-item>

        <el-form-item>
          <div class="actions">
            <el-button :loading="loading" type="primary" class="register-button" @click="handleRegister">
              注册
            </el-button>
            <el-link class="login-link" @click="goToLogin">返回登录</el-link>
          </div>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script>
import axios from 'axios'
import { ElMessage } from 'element-plus'
import { getApiBaseUrl } from '../../api/baseUrl'
import logoImage from '../../assets/images/logo.jpg'
import { User, Lock } from '@element-plus/icons-vue'

export default {
  data() {
    const validateUserName = (rule, value, callback) => {
      if (!value) return callback(new Error('用户名不能为空'))
      callback()
    }

    const validatePassword = (rule, value, callback) => {
      if (!value) return callback(new Error('密码不能为空'))
      callback()
    }

    const validateConfirm = (rule, value, callback) => {
      if (!value) return callback(new Error('请再次输入密码'))
      if (value !== this.form.password) return callback(new Error('两次密码不一致'))
      callback()
    }

    return {
      loading: false,
      apiBaseUrl: getApiBaseUrl(),
      logoImage,
      form: {
        username: '',
        password: '',
        confirmPassword: ''
      },
      rules: {
        username: [{ validator: validateUserName, trigger: 'blur' }],
        password: [{ validator: validatePassword, trigger: 'blur' }],
        confirmPassword: [{ validator: validateConfirm, trigger: 'blur' }]
      }
    }
  },
  components: {
    User,
    Lock
  },
  methods: {
    goToLogin() {
      this.$router.push({ name: 'login' })
    },
    handleRegister() {
      this.$refs.formRef.validate(async (valid) => {
        if (!valid) return
        this.loading = true
        try {
          await axios.post(`${this.apiBaseUrl}/api/users/register`, {
            username: this.form.username,
            password: this.form.password,
            account: this.form.username
          })
          ElMessage({ type: 'success', message: '注册成功，请登录', duration: 2000 })
          this.goToLogin()
        } catch (e) {
          const msg = e?.response?.data?.msg || e?.response?.data?.message || '注册失败'
          ElMessage({ type: 'error', message: msg, duration: 2500 })
        } finally {
          this.loading = false
        }
      })
    }
  }
}
</script>

<style scoped>
.register {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
}

.box-card {
  width: 380px;
  border-radius: 10px;
}

.header {
  display: flex;
  align-items: center;
}

.header-image {
  width: 80px;
  height: auto;
  margin-right: 20px;
}

.header-text {
  font-size: 28px;
  font-weight: 700;
}

.input {
  width: 300px;
}

.actions {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.register-button {
  width: 120px;
}

.login-link {
  margin-left: 12px;
}
</style>