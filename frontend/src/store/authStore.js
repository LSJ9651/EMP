import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { login as loginApi, logout as logoutApi } from '../api/api.js'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('token') || '')
  const user = ref(JSON.parse(localStorage.getItem('user') || 'null'))

  const isAuthenticated = computed(() => !!token.value && !!user.value)

  async function login(username, password) {
    const res = await loginApi({ username, password })
    if (res.code === 200) {
      const data = res.data
      // 生成认证 token 格式: "role:user_id"，用于后端权限中间件解析
      const authToken = data.token || `${data.role}:${data.id}`
      token.value = authToken
      user.value = data

      localStorage.setItem('token', authToken)
      localStorage.setItem('user', JSON.stringify(user.value))

      if (data.permissions) {
        localStorage.setItem('user_permissions', JSON.stringify(data.permissions))
      }

      return data
    } else {
      throw new Error(res.message || '登录失败')
    }
  }

  function logout() {
    token.value = ''
    user.value = null
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    localStorage.removeItem('user_permissions')
    logoutApi().catch(() => {})
  }

  return {
    token,
    user,
    isAuthenticated,
    login,
    logout,
  }
})
