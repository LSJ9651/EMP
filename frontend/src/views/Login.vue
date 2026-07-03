<template>
  <div class="login-page">
    <LoginBackground />

    <div class="login-wrapper">
      <div class="login-card" :class="{ 'shake': shakeForm }">
        <!-- Logo + 标题 -->
        <div class="card-header">
          <img src="@/assets/logo.svg" alt="Logo" class="logo" />
          <h1 class="title">能耗智能管理优化平台</h1>
          <p class="subtitle">欢迎回来，请登录您的账号</p>
        </div>

        <!-- 登录表单 -->
        <el-form ref="formRef" :model="form" :rules="rules" label-width="0" size="large" class="login-form">
          <el-form-item prop="username">
            <el-input
              v-model="form.username"
              placeholder="请输入用户名"
              class="login-input"
              @keydown.enter="handleLogin"
            >
              <template #prefix>
                <el-icon class="input-icon"><User /></el-icon>
              </template>
            </el-input>
          </el-form-item>

          <el-form-item prop="password">
            <el-input
              v-model="form.password"
              :type="showPassword ? 'text' : 'password'"
              placeholder="请输入密码"
              class="login-input"
              @keydown.enter="handleLogin"
            >
              <template #prefix>
                <el-icon class="input-icon"><Lock /></el-icon>
              </template>
              <template #suffix>
                <span class="password-toggle" @click="showPassword = !showPassword">
                  <el-icon :size="18">
                    <View v-if="showPassword" />
                    <Hide v-else />
                  </el-icon>
                </span>
              </template>
            </el-input>
          </el-form-item>

          <!-- 选项：记住账号 + 忘记密码 -->
          <div class="form-options">
            <el-checkbox v-model="rememberMe" size="default">记住账号</el-checkbox>
            <span class="forgot-password">忘记密码？</span>
          </div>

          <!-- 登录按钮 -->
          <el-button
            type="primary"
            size="large"
            :loading="loading"
            class="login-btn"
            @click="handleLogin"
          >
            <span v-if="!loading" class="btn-text">
              <el-icon class="btn-icon"><Lock /></el-icon>
              登 录
            </span>
            <span v-else>登录中...</span>
          </el-button>
        </el-form>

        <!-- 测试账号提示 -->
        <div class="test-account" @click="fillTestAccount">
          <el-icon class="test-icon"><InfoFilled /></el-icon>
          <span>测试账号：<em>admin</em> / <em>admin123</em></span>
        </div>

        <!-- 版本信息 -->
        <div class="version">v1.0.0</div>
      </div>
    </div>

    <!-- 底部版权 -->
    <div class="footer">© 2026 能耗智能管理优化平台 All Rights Reserved.</div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/store/authStore.js'
import { useEnergyStore } from '@/store/energyStore.js'
import LoginBackground from '@/components/LoginBackground.vue'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const energyStore = useEnergyStore()

const formRef = ref(null)
const loading = ref(false)
const showPassword = ref(false)
const rememberMe = ref(false)
const shakeForm = ref(false)

const form = reactive({
  username: '',
  password: '',
})

const rules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 2, message: '用户名至少2个字符', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 4, message: '密码至少4个字符', trigger: 'blur' },
  ],
}

// 记住账号：从 localStorage 恢复
onMounted(() => {
  const savedUsername = localStorage.getItem('remembered_username')
  if (savedUsername) {
    form.username = savedUsername
    rememberMe.value = true
  }
})

async function handleLogin() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  try {
    const userData = await authStore.login(form.username, form.password)

    // 记住账号
    if (rememberMe.value) {
      localStorage.setItem('remembered_username', form.username)
    } else {
      localStorage.removeItem('remembered_username')
    }

    // 同步旧 store 的用户数据（兼容现有组件）
    const storedUser = JSON.parse(localStorage.getItem('user') || 'null')
    if (storedUser) {
      energyStore.user = storedUser
    }

    // ── 角色路由映射 ──
    const roleRoutes = {
      admin: '/',
      dispatcher: '/',
      operator: '/devices',
      viewer: '/',
    }

    // 优先使用 redirect 参数（登录前访问的页面），否则按角色跳转
    const redirectPath = route.query.redirect || roleRoutes[userData.role] || '/'
    // 设置会话认证标志（路由守卫据此判断本次会话已登录）
    sessionStorage.setItem('session_authenticated', '1')
    ElMessage.success('登录成功')
    router.push(redirectPath)
  } catch (e) {
    // 抖动动画
    shakeForm.value = true
    setTimeout(() => { shakeForm.value = false }, 500)

    const msg = e?.response?.data?.message || e.message || '登录失败，请检查用户名和密码'
    ElMessage.error(msg)
  } finally {
    loading.value = false
  }
}

function fillTestAccount() {
  form.username = 'admin'
  form.password = 'admin123'
  ElMessage.success('已填充测试账号，点击登录按钮即可')
}
</script>

<style scoped>
.login-page {
  position: relative;
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #0a0e27 0%, #1a1040 50%, #0d2137 100%);
  overflow: hidden;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC',
    'Microsoft YaHei', 'Helvetica Neue', sans-serif;
}

/* ── 卡片容器 ── */
.login-wrapper {
  position: relative;
  z-index: 1;
  display: flex;
  justify-content: center;
  align-items: center;
  width: 100%;
  padding: 20px;
  animation: cardFadeIn 0.6s ease-out;
}

@keyframes cardFadeIn {
  from {
    opacity: 0;
    transform: translateY(30px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* ── 毛玻璃卡片 ── */
.login-card {
  width: 420px;
  padding: 44px 40px 36px;
  background: rgba(255, 255, 255, 0.06);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 24px;
  box-shadow:
    0 25px 50px -12px rgba(0, 0, 0, 0.5),
    inset 0 1px 0 rgba(255, 255, 255, 0.08);
  transition: box-shadow 0.3s ease;
}

.login-card:hover {
  box-shadow:
    0 30px 60px -12px rgba(0, 0, 0, 0.6),
    inset 0 1px 0 rgba(255, 255, 255, 0.1);
}

/* 抖动动画（登录失败） */
.shake {
  animation: shakeX 0.5s ease-in-out;
}

@keyframes shakeX {
  0%, 100% { transform: translateX(0); }
  10%, 50%, 90% { transform: translateX(-6px); }
  30%, 70% { transform: translateX(6px); }
}

/* ── 卡片头部 ── */
.card-header {
  text-align: center;
  margin-bottom: 36px;
}

.logo {
  width: 56px;
  height: 56px;
  margin-bottom: 16px;
  filter: drop-shadow(0 0 12px rgba(79, 140, 247, 0.3));
}

.title {
  font-size: 22px;
  font-weight: 700;
  color: #ffffff;
  letter-spacing: 1px;
  margin: 0 0 8px 0;
}

.subtitle {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.6);
  margin: 0;
  letter-spacing: 0.5px;
}

/* ── 表单 ── */
.login-form {
  margin-bottom: 8px;
}

:deep(.el-form-item) {
  margin-bottom: 22px;
}

:deep(.el-input__wrapper) {
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 12px;
  box-shadow: none !important;
  padding: 4px 12px;
  transition: all 0.3s ease;
}

:deep(.el-input__wrapper:hover) {
  border-color: rgba(79, 140, 247, 0.4);
  background: rgba(255, 255, 255, 0.08);
}

:deep(.el-input__wrapper.is-focus) {
  border-color: #4f8cf7;
  background: rgba(255, 255, 255, 0.1);
  box-shadow: 0 0 0 3px rgba(79, 140, 247, 0.15) !important;
}

:deep(.el-input__inner) {
  color: #ffffff;
  height: 44px;
  font-size: 15px;
}

:deep(.el-input__inner::placeholder) {
  color: rgba(255, 255, 255, 0.35);
}

.input-icon {
  color: rgba(255, 255, 255, 0.4);
  font-size: 18px;
  transition: color 0.3s ease;
}

:deep(.el-input__wrapper.is-focus) .input-icon {
  color: #4f8cf7;
}

/* 密码可见切换 */
.password-toggle {
  cursor: pointer;
  color: rgba(255, 255, 255, 0.4);
  display: flex;
  align-items: center;
  transition: color 0.2s ease;
}

.password-toggle:hover {
  color: rgba(255, 255, 255, 0.7);
}

/* ── 表单选项 ── */
.form-options {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

:deep(.el-checkbox__label) {
  color: rgba(255, 255, 255, 0.7);
  font-size: 13px;
}

:deep(.el-checkbox__input.is-checked .el-checkbox__inner) {
  background-color: #4f8cf7;
  border-color: #4f8cf7;
}

:deep(.el-checkbox__inner) {
  background: rgba(255, 255, 255, 0.1);
  border-color: rgba(255, 255, 255, 0.2);
}

.forgot-password {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.5);
  cursor: pointer;
  transition: color 0.2s ease;
}

.forgot-password:hover {
  color: #4f8cf7;
}

/* ── 登录按钮 ── */
.login-btn {
  width: 100%;
  height: 48px;
  border-radius: 12px;
  font-size: 16px;
  font-weight: 600;
  letter-spacing: 2px;
  background: linear-gradient(135deg, #4f8cf7, #6c5ce7);
  border: none;
  transition: all 0.3s ease;
}

.login-btn:hover {
  background: linear-gradient(135deg, #6c5ce7, #4f8cf7);
  transform: translateY(-1px);
  box-shadow: 0 8px 24px rgba(79, 140, 247, 0.3);
}

.login-btn:active {
  transform: translateY(0) scale(0.98);
}

.btn-text {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
}

.btn-icon {
  font-size: 18px;
}

/* ── 测试账号 ── */
.test-account {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  margin-top: 20px;
  padding: 10px 16px;
  background: rgba(79, 140, 247, 0.08);
  border: 1px solid rgba(79, 140, 247, 0.15);
  border-radius: 10px;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.6);
  cursor: pointer;
  transition: all 0.2s ease;
}

.test-account:hover {
  background: rgba(79, 140, 247, 0.15);
  border-color: rgba(79, 140, 247, 0.3);
}

.test-icon {
  color: #4f8cf7;
  font-size: 16px;
}

.test-account em {
  font-style: normal;
  color: #4f8cf7;
  font-weight: 600;
}

/* ── 版本 ── */
.version {
  text-align: center;
  margin-top: 16px;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.25);
}

/* ── 底部版权 ── */
.footer {
  position: fixed;
  bottom: 20px;
  left: 0;
  right: 0;
  text-align: center;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.25);
  z-index: 1;
}

/* ── 响应式 ── */
@media (max-width: 1023px) {
  .login-card {
    width: 380px;
    padding: 36px 32px 28px;
  }
}

@media (max-width: 767px) {
  .login-card {
    width: 90%;
    max-width: 400px;
    padding: 32px 24px 24px;
  }

  .title {
    font-size: 18px;
  }

  .subtitle {
    font-size: 13px;
  }

  .logo {
    width: 48px;
    height: 48px;
  }

  .login-btn {
    height: 44px;
    font-size: 15px;
  }
}

@media (max-width: 479px) {
  .login-card {
    width: 95%;
    padding: 28px 20px 20px;
  }

  .title {
    font-size: 16px;
  }
}
</style>
