import { createRouter, createWebHistory } from 'vue-router'

/**
 * 路由权限映射：每个路由需要的权限 { role?: [...], permission?: { module, feature } }
 * 满足任一条件即可访问
 */
const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Login.vue'),
    meta: { requiresAuth: false },
  },
  {
    path: '/',
    name: 'Dashboard',
    component: () => import('../views/Dashboard.vue'),
    meta: {
      requiresAuth: true,
      // 全部登录用户可见（基础权限已在外层守卫保证）
      minRole: ['admin', 'dispatcher', 'operator', 'user'],
    },
  },
  {
    path: '/devices',
    name: 'Devices',
    component: () => import('../views/Devices.vue'),
    meta: {
      requiresAuth: true,
      minRole: ['admin', 'dispatcher', 'operator', 'user'],
    },
  },
  {
    path: '/tariff',
    name: 'Tariff',
    component: () => import('../views/Tariff.vue'),
    meta: {
      requiresAuth: true,
      roles: ['admin', 'dispatcher'],
      permission: { module: 'scheduling', feature: 'config' },
    },
  },
  {
    path: '/alerts',
    name: 'Alerts',
    component: () => import('../views/Alerts.vue'),
    meta: {
      requiresAuth: true,
      minRole: ['admin', 'dispatcher', 'operator', 'user'],
    },
  },
  {
    path: '/reports',
    name: 'AgentReports',
    component: () => import('../views/AgentReports.vue'),
    meta: {
      requiresAuth: true,
      roles: ['admin', 'dispatcher'],
      permission: { module: 'reports', feature: 'view' },
      altPermission: { module: 'ai_analysis', feature: 'view' },
    },
  },
  {
    path: '/schedule',
    name: 'ScheduleOptimize',
    component: () => import('../views/ScheduleOptimize.vue'),
    meta: {
      requiresAuth: true,
      roles: ['admin', 'dispatcher'],
      permission: { module: 'scheduling', feature: 'execute' },
    },
  },
  {
    path: '/reports-center',
    name: 'ReportCenter',
    component: () => import('../views/ReportCenter.vue'),
    meta: {
      requiresAuth: true,
      roles: ['admin', 'dispatcher'],
      permission: { module: 'reports', feature: 'view' },
    },
  },
  {
    path: '/cost-allocation',
    name: 'CostAllocation',
    component: () => import('../views/CostAllocation.vue'),
    meta: {
      requiresAuth: true,
      roles: ['admin', 'dispatcher'],
      permission: { module: 'scheduling', feature: 'view' },
      altPermission: { module: 'reports', feature: 'export' },
    },
  },
  {
    path: '/users',
    name: 'UserManagement',
    component: () => import('../views/UserManagement.vue'),
    meta: {
      requiresAuth: true,
      roles: ['admin'],
      permission: { module: 'system', feature: 'user_manage' },
    },
  },
  {
    path: '/ai-config',
    name: 'AIConfig',
    component: () => import('../views/AIConfig.vue'),
    meta: {
      requiresAuth: true,
      roles: ['admin'],
      permission: { module: 'system', feature: 'config' },
    },
  },
]

// 首次加载标志：确保每次刷新都从登录页开始
let _isFirstNavigation = true

// 角色 → 默认首页路由映射
const roleDefaultRoutes = {
  admin: '/',
  dispatcher: '/',
  operator: '/devices',
  viewer: '/',
  user: '/',
}

const router = createRouter({
  history: createWebHistory(),
  routes,
})

/**
 * 读取用户的权限映射（从 localStorage 缓存）
 * @returns {{ [key: string]: boolean }}
 */
function getUserPermissions() {
  try {
    const raw = localStorage.getItem('user_permissions')
    return raw ? JSON.parse(raw) : {}
  } catch {
    return {}
  }
}

/**
 * 检查用户是否有权限访问该路由
 * 规则：
 *   1. admin 角色 → 全部通过
 *   2. 路由有 minRole 且用户角色在其中 → 通过
 *   3. 路由有 roles 且用户角色在其中 → 通过
 *   4. 路由有 permission 且用户拥有该权限 → 通过
 *   5. 路由有 altPermission 且用户拥有该替代权限 → 通过
 *   6. 以上都不满足 → 拒绝
 */
function canAccessRoute(user, routeMeta) {
  if (!user) return false
  if (user.role === 'admin') return true

  if (routeMeta.minRole && routeMeta.minRole.includes(user.role)) return true
  if (routeMeta.roles && routeMeta.roles.includes(user.role)) return true

  const perms = getUserPermissions()
  if (routeMeta.permission) {
    const key = `${routeMeta.permission.module}.${routeMeta.permission.feature}`
    if (perms[key]) return true
  }
  if (routeMeta.altPermission) {
    const key = `${routeMeta.altPermission.module}.${routeMeta.altPermission.feature}`
    if (perms[key]) return true
  }

  return false
}

router.beforeEach((to, from, next) => {
  // ════════════════════════════════════════════════════════════
  // 规则 1：首次加载（刷新/新开标签页），无论是否已登录，
  //         均强制跳转登录页，并将目标路径保存为 redirect 参数
  // ════════════════════════════════════════════════════════════
  if (_isFirstNavigation) {
    _isFirstNavigation = false
    if (to.path !== '/login') {
      next({ path: '/login', query: { redirect: to.fullPath } })
      return
    }
    next()
    return
  }

  const token = localStorage.getItem('token')
  const userStr = localStorage.getItem('user')
  const user = userStr ? JSON.parse(userStr) : null
  const isAuthenticated = !!token && !!user

  // ════════════════════════════════════════════════════════════
  // 规则 2：未登录用户尝试访问需要认证的页面 → 拦截到登录页
  //         （同时保存目标路径，登录后跳回）
  // ════════════════════════════════════════════════════════════
  if (to.meta.requiresAuth !== false && !isAuthenticated) {
    next({ path: '/login', query: { redirect: to.fullPath } })
    return
  }

  // ════════════════════════════════════════════════════════════
  // 规则 3：已登录用户访问登录页 → 根据角色跳转到对应首页
  //         如果 URL 带有 redirect 参数则优先跳转到该路径
  // ════════════════════════════════════════════════════════════
  if (to.path === '/login' && isAuthenticated) {
    const redirect = to.query.redirect
    if (redirect && typeof redirect === 'string' && !redirect.startsWith('/login')) {
      next(redirect)
      return
    }
    const defaultRoute = roleDefaultRoutes[user.role] || '/'
    next(defaultRoute)
    return
  }

  // ════════════════════════════════════════════════════════════
  // 规则 4：防止无限重定向循环
  // ════════════════════════════════════════════════════════════
  if (to.path === from.path) {
    next()
    return
  }

  // ════════════════════════════════════════════════════════════
  // 规则 5：已登录用户 — 细粒度权限校验（角色 / 权限点）
  //         不满足权限的，降级跳转到首页；首页都无法访问则登出
  // ════════════════════════════════════════════════════════════
  if (to.meta.requiresAuth !== false && isAuthenticated) {
    if (!canAccessRoute(user, to.meta)) {
      if (to.path === '/') {
        localStorage.removeItem('token')
        localStorage.removeItem('user')
        localStorage.removeItem('user_permissions')
        next('/login')
        return
      }
      next('/')
      return
    }
  }

  next()
})

export { roleDefaultRoutes }
export default router
