/**
 * Pinia 对话状态管理 Store
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { chatAPI, authAPI } from '../api/index.js'

export const useChatStore = defineStore('chat', () => {
  // ── 状态 ──────────────────────────────────────────────────
  const messages     = ref([])          // 当前会话消息列表
  const sessionId    = ref(null)        // 当前会话 ID
  const isLoading    = ref(false)       // 是否等待回复
  const isStreaming  = ref(false)       // 是否正在流式接收
  const currentUser  = ref(null)        // 当前登录用户
  const accessToken  = ref(localStorage.getItem('access_token'))

  // 流式输出暂存
  const streamingMessage = ref('')

  // ── Getters ───────────────────────────────────────────────
  const isLoggedIn  = computed(() => !!accessToken.value)
  const allMessages = computed(() => messages.value)

  // ── Actions ───────────────────────────────────────────────

  /** 登录 */
  async function login(username, password) {
    const res = await authAPI.login({ username, password })
    accessToken.value = res.access_token
    currentUser.value = res.user
    localStorage.setItem('access_token', res.access_token)
    return res
  }

  /** 登出 */
  function logout() {
    accessToken.value = null
    currentUser.value = null
    localStorage.removeItem('access_token')
    messages.value = []
    sessionId.value = null
  }

  /** 获取当前用户信息 */
  async function fetchMe() {
    if (!accessToken.value) return
    try {
      currentUser.value = await authAPI.me()
    } catch {
      logout()
    }
  }

  /** 发送消息（WebSocket 流式） */
  function sendMessageStream(text, onToken, onDone, onError) {
    if (!text.trim()) return

    // 添加用户消息
    messages.value.push({ role: 'user', content: text, id: Date.now() })

    // 创建 AI 回复占位
    const aiMsgId = Date.now() + 1
    messages.value.push({ role: 'assistant', content: '', id: aiMsgId, streaming: true })
    isStreaming.value = true
    streamingMessage.value = ''

    const wsUrl = `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws/chat/${sessionId.value || generateSessionId()}`
    const ws = new WebSocket(wsUrl)

    ws.onopen = () => {
      ws.send(JSON.stringify({
        message: text,
        token: accessToken.value || undefined,
      }))
    }

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data)
      if (data.type === 'token') {
        streamingMessage.value += data.content
        // 更新最后一条 AI 消息
        const lastMsg = messages.value.find(m => m.id === aiMsgId)
        if (lastMsg) lastMsg.content = streamingMessage.value
        onToken?.(data.content)
      } else if (data.type === 'done') {
        sessionId.value = data.session_id
        const lastMsg = messages.value.find(m => m.id === aiMsgId)
        if (lastMsg) lastMsg.streaming = false
        isStreaming.value = false
        ws.close()
        onDone?.()
      } else if (data.type === 'error') {
        isStreaming.value = false
        ws.close()
        onError?.(data.detail)
      }
    }

    ws.onerror = () => {
      isStreaming.value = false
      onError?.('WebSocket 连接失败')
    }

    return ws
  }

  /** 发送消息（REST 普通模式，兜底） */
  async function sendMessageRest(text) {
    if (!text.trim()) return
    messages.value.push({ role: 'user', content: text, id: Date.now() })
    isLoading.value = true
    try {
      const res = await chatAPI.sendMessage({
        message: text,
        session_id: sessionId.value,
      })
      sessionId.value = res.session_id
      messages.value.push({
        role: 'assistant',
        content: res.reply,
        intent: res.intent,
        sources: res.rag_sources,
        id: Date.now(),
      })
      return res
    } finally {
      isLoading.value = false
    }
  }

  /** 清空当前对话 */
  async function clearConversation() {
    if (sessionId.value) {
      try { await chatAPI.endSession(sessionId.value) } catch {}
    }
    messages.value = []
    sessionId.value = null
    streamingMessage.value = ''
  }

  /** 提交消息反馈 */
  async function submitFeedback(conversationId, messageId, isHelpful) {
    await chatAPI.feedback({ conversation_id: conversationId, message_id: messageId, is_helpful: isHelpful })
  }

  // ── 工具 ──────────────────────────────────────────────────
  function generateSessionId() {
    const id = 'sess_' + Math.random().toString(36).slice(2, 11)
    sessionId.value = id
    return id
  }

  return {
    messages, sessionId, isLoading, isStreaming, currentUser, accessToken,
    isLoggedIn, allMessages,
    login, logout, fetchMe,
    sendMessageStream, sendMessageRest, clearConversation, submitFeedback,
  }
})
