<template>
  <div class="min-h-screen font-sans" style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">

    <!-- ── 登录 / 注册页 ── -->
    <div v-if="!store.isLoggedIn && showAuth"
      class="min-h-screen flex items-center justify-center relative overflow-hidden"
      style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);">

      <!-- 背景装饰圆 -->
      <div class="absolute inset-0 pointer-events-none overflow-hidden">
        <div class="absolute -top-40 -right-40 w-80 h-80 rounded-full opacity-20"
          style="background: radial-gradient(circle, #fff 0%, transparent 70%)"></div>
        <div class="absolute -bottom-40 -left-40 w-96 h-96 rounded-full opacity-10"
          style="background: radial-gradient(circle, #fff 0%, transparent 70%)"></div>
      </div>

      <div class="relative w-full max-w-sm mx-4">
        <!-- Logo -->
        <div class="text-center mb-8">
          <div class="inline-flex items-center justify-center w-16 h-16 rounded-2xl shadow-xl mb-4"
            style="background: rgba(255,255,255,0.25); backdrop-filter: blur(10px);">
            <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
              <circle cx="16" cy="16" r="14" fill="white" opacity="0.9"/>
              <path d="M10 12h12M10 16h8M10 20h10" stroke="#764ba2" stroke-width="2" stroke-linecap="round"/>
              <circle cx="23" cy="20" r="3" fill="#667eea"/>
            </svg>
          </div>
          <h1 class="text-2xl font-bold text-white">智能客服助手</h1>
          <p class="text-white text-sm mt-1" style="opacity:0.75">AI-Powered Customer Service</p>
        </div>

        <!-- 卡片 -->
        <div class="rounded-2xl shadow-2xl p-8" style="background: rgba(255,255,255,0.95); backdrop-filter: blur(20px);">
          <!-- Tab 切换 -->
          <div class="flex bg-gray-100 rounded-xl p-1 mb-6">
            <button @click="authMode = 'login'"
              :class="authMode === 'login' ? 'shadow text-gray-800 bg-white' : 'text-gray-500'"
              class="flex-1 py-2 rounded-lg text-sm font-semibold transition-all duration-200">登录</button>
            <button @click="authMode = 'register'"
              :class="authMode === 'register' ? 'shadow text-gray-800 bg-white' : 'text-gray-500'"
              class="flex-1 py-2 rounded-lg text-sm font-semibold transition-all duration-200">注册账号</button>
          </div>

          <!-- 表单 -->
          <div class="space-y-4">
            <div class="relative">
              <span class="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
              </span>
              <input v-model="form.username" type="text" placeholder="用户名"
                class="w-full border border-gray-200 rounded-xl pl-9 pr-4 py-3 text-sm focus:outline-none focus:ring-2 focus:border-transparent transition-all"
                style="--tw-ring-color: #667eea; focus:ring-color: #667eea" />
            </div>
            <div v-if="authMode === 'register'" class="relative">
              <span class="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="4" width="20" height="16" rx="2"/><path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"/></svg>
              </span>
              <input v-model="form.email" type="email" placeholder="邮箱地址"
                class="w-full border border-gray-200 rounded-xl pl-9 pr-4 py-3 text-sm focus:outline-none focus:ring-2 focus:border-transparent transition-all" />
            </div>
            <div class="relative">
              <span class="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
              </span>
              <input v-model="form.password" type="password" placeholder="密码"
                class="w-full border border-gray-200 rounded-xl pl-9 pr-4 py-3 text-sm focus:outline-none focus:ring-2 focus:border-transparent transition-all"
                @keyup.enter="submitAuth" />
            </div>
          </div>

          <p v-if="authError" class="mt-3 text-xs text-red-500 flex items-center gap-1">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12" stroke="white" stroke-width="2"/><line x1="12" y1="16" x2="12.01" y2="16" stroke="white" stroke-width="2"/></svg>
            {{ authError }}
          </p>

          <button @click="submitAuth" :disabled="authLoading"
            class="w-full mt-5 py-3 rounded-xl text-sm font-semibold text-white transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
            style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); box-shadow: 0 4px 15px rgba(102,126,234,0.4);">
            <span v-if="authLoading" class="flex items-center justify-center gap-2">
              <svg class="animate-spin" width="14" height="14" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="10" stroke="rgba(255,255,255,0.3)" stroke-width="4"/><path d="M12 2a10 10 0 0 1 10 10" stroke="white" stroke-width="4" stroke-linecap="round"/></svg>
              处理中...
            </span>
            <span v-else>{{ authMode === 'login' ? '登 录' : '创建账号' }}</span>
          </button>

          <div class="mt-4 flex items-center gap-3">
            <div class="flex-1 h-px bg-gray-200"></div>
            <span class="text-xs text-gray-400">或者</span>
            <div class="flex-1 h-px bg-gray-200"></div>
          </div>

          <button @click="guestMode"
            class="w-full mt-4 py-2.5 rounded-xl text-sm font-medium text-gray-600 border border-gray-200 hover:bg-gray-50 transition-colors">
            以游客身份体验
          </button>
        </div>

        <p class="text-center text-xs mt-6" style="color: rgba(255,255,255,0.6)">
          © 2026 智能客服系统 · 由 LLM 技术驱动
        </p>
      </div>
    </div>

    <!-- ── 主界面 ── -->
    <div v-else class="flex h-screen bg-gray-50">

      <!-- 深色侧边栏 -->
      <aside class="w-56 flex flex-col flex-shrink-0" style="background: #1a1d27;">
        <!-- Logo -->
        <div class="px-4 py-5 border-b" style="border-color: rgba(255,255,255,0.08);">
          <div class="flex items-center gap-2.5">
            <div class="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
              style="background: linear-gradient(135deg, #667eea, #764ba2);">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 15v-4H7l5-8v4h4l-5 8z" fill="white"/></svg>
            </div>
            <div>
              <p class="text-white text-sm font-semibold">智能客服</p>
              <p class="text-xs" style="color: rgba(255,255,255,0.45);">AI Assistant</p>
            </div>
          </div>
        </div>

        <!-- 导航 -->
        <nav class="flex-1 p-3 space-y-1 overflow-y-auto">
          <p class="text-xs font-medium px-2 py-1 mb-1" style="color: rgba(255,255,255,0.35);">功能</p>
          <button @click="currentView = 'chat'"
            :class="currentView === 'chat' ? 'text-white' : 'text-gray-400 hover:text-gray-200'"
            class="w-full text-left px-3 py-2.5 rounded-xl text-sm font-medium transition-all flex items-center gap-2.5"
            :style="currentView === 'chat' ? 'background: rgba(102,126,234,0.2);' : 'hover:background: rgba(255,255,255,0.05)'">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
            对话
          </button>
          <button v-if="store.currentUser?.role === 'admin' || store.currentUser?.role === 'agent'"
            @click="currentView = 'admin'"
            :class="currentView === 'admin' ? 'text-white' : 'text-gray-400 hover:text-gray-200'"
            class="w-full text-left px-3 py-2.5 rounded-xl text-sm font-medium transition-all flex items-center gap-2.5"
            :style="currentView === 'admin' ? 'background: rgba(102,126,234,0.2);' : ''">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>
            知识库管理
          </button>
        </nav>

        <!-- 底部用户信息 -->
        <div class="p-3 border-t" style="border-color: rgba(255,255,255,0.08);">
          <div class="flex items-center gap-2.5 px-2 py-2">
            <div class="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold text-white flex-shrink-0"
              style="background: linear-gradient(135deg, #f093fb, #f5576c);">
              {{ (store.currentUser?.username || '游')[0].toUpperCase() }}
            </div>
            <div class="flex-1 min-w-0">
              <p class="text-white text-sm font-medium truncate">{{ store.currentUser?.username || '游客' }}</p>
              <p class="text-xs truncate" style="color: rgba(255,255,255,0.4);">{{ store.currentUser?.role || 'guest' }}</p>
            </div>
            <button v-if="store.isLoggedIn" @click="store.logout" title="退出登录"
              class="flex-shrink-0 transition-colors hover:text-red-400" style="color: rgba(255,255,255,0.3);">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>
            </button>
          </div>
        </div>
      </aside>

      <!-- 主内容区 -->
      <main class="flex-1 overflow-hidden">
        <ChatWindow v-if="currentView === 'chat'" />
        <KnowledgeAdmin v-else-if="currentView === 'admin'" />
      </main>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useChatStore } from './store/chat.js'
import { authAPI } from './api/index.js'
import ChatWindow from './components/ChatWindow.vue'
import KnowledgeAdmin from './components/KnowledgeAdmin.vue'

const store = useChatStore()
const showAuth = ref(true)
const authMode = ref('login')
const authLoading = ref(false)
const authError = ref('')
const currentView = ref('chat')

const form = ref({ username: '', email: '', password: '' })

onMounted(async () => {
  if (store.accessToken) {
    await store.fetchMe()
    if (store.isLoggedIn) showAuth.value = false
  }
})

async function submitAuth() {
  authError.value = ''
  authLoading.value = true
  try {
    if (authMode.value === 'login') {
      await store.login(form.value.username, form.value.password)
    } else {
      await authAPI.register(form.value)
      await store.login(form.value.username, form.value.password)
    }
    showAuth.value = false
  } catch (e) {
    authError.value = typeof e === 'string' ? e : '操作失败，请重试'
  } finally {
    authLoading.value = false
  }
}

function guestMode() {
  showAuth.value = false
}
</script>
