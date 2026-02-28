<template>
  <div class="flex flex-col h-screen" style="background: #f7f8fc;">

    <!-- 顶部栏 -->
    <header class="bg-white border-b flex items-center justify-between px-6 py-3.5 flex-shrink-0" style="border-color: #eef0f6; box-shadow: 0 1px 3px rgba(0,0,0,0.04);">
      <div class="flex items-center gap-3">
        <div class="relative">
          <div class="w-9 h-9 rounded-xl flex items-center justify-center"
            style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="white"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 15v-4H7l5-8v4h4l-5 8z"/></svg>
          </div>
          <span class="absolute -bottom-0.5 -right-0.5 w-3 h-3 rounded-full border-2 border-white" style="background: #22c55e;"></span>
        </div>
        <div>
          <h1 class="font-semibold text-gray-800 text-sm leading-tight">智能客服助手</h1>
          <p class="text-xs" style="color: #22c55e;">● 在线 · 随时为您服务</p>
        </div>
      </div>

      <div class="flex items-center gap-2">
        <!-- 对话轮数 -->
        <span v-if="store.messages.length" class="text-xs px-2.5 py-1 rounded-full"
          style="background: #f0f0ff; color: #667eea;">
          {{ Math.ceil(store.messages.length / 2) }} 轮对话
        </span>
        <button @click="store.clearConversation"
          class="flex items-center gap-1.5 text-xs text-gray-400 hover:text-gray-600 px-3 py-1.5 rounded-lg hover:bg-gray-100 transition-all">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
          清空
        </button>
      </div>
    </header>

    <!-- 消息列表 -->
    <div ref="messageContainer" class="flex-1 overflow-y-auto py-6 px-4 space-y-1" style="scrollbar-width: thin; scrollbar-color: #e5e7eb transparent;">

      <!-- 欢迎屏 -->
      <div v-if="!store.messages.length" class="flex flex-col items-center justify-center h-full pb-10 select-none">
        <div class="w-20 h-20 rounded-3xl flex items-center justify-center mb-5 shadow-lg"
          style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);">
          <svg width="38" height="38" viewBox="0 0 24 24" fill="white"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 15v-4H7l5-8v4h4l-5 8z"/></svg>
        </div>
        <h2 class="text-xl font-bold text-gray-800 mb-2">您好，有什么可以帮您？</h2>
        <p class="text-sm text-gray-400 mb-8 text-center max-w-xs leading-relaxed">
          我是 AI 智能客服助手，可以帮您解答问题、处理售后、排查故障。
        </p>
        <!-- 快捷问题 -->
        <div class="grid grid-cols-2 gap-2.5 w-full max-w-sm">
          <button v-for="q in quickQuestions" :key="q"
            @click="sendQuick(q)"
            class="text-left text-sm px-4 py-3 rounded-xl border transition-all hover:shadow-md group"
            style="background: white; border-color: #eef0f6; color: #374151;">
            <span class="block text-base mb-0.5">{{ q.icon }}</span>
            <span class="font-medium group-hover:text-indigo-600 transition-colors" style="font-size: 13px;">{{ q.text }}</span>
          </button>
        </div>
      </div>

      <!-- 消息 -->
      <MessageBubble
        v-for="msg in store.messages"
        :key="msg.id"
        :message="msg"
        @feedback="handleFeedback"
      />

      <!-- 打字动画 -->
      <div v-if="store.isLoading && !store.isStreaming" class="flex items-end gap-2.5 px-2">
        <div class="w-8 h-8 rounded-xl flex items-center justify-center flex-shrink-0"
          style="background: linear-gradient(135deg, #667eea, #764ba2);">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="white"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 15v-4H7l5-8v4h4l-5 8z"/></svg>
        </div>
        <div class="px-4 py-3 rounded-2xl rounded-bl-sm bg-white shadow-sm border" style="border-color: #eef0f6;">
          <div class="flex gap-1.5 items-center h-4">
            <span class="w-2 h-2 rounded-full animate-bounce" style="background: #667eea; animation-delay: 0ms;"></span>
            <span class="w-2 h-2 rounded-full animate-bounce" style="background: #764ba2; animation-delay: 160ms;"></span>
            <span class="w-2 h-2 rounded-full animate-bounce" style="background: #667eea; animation-delay: 320ms;"></span>
          </div>
        </div>
      </div>

      <div ref="bottomAnchor" class="h-2"></div>
    </div>

    <!-- 输入区 -->
    <div class="flex-shrink-0 px-4 pb-4 pt-2">
      <div class="max-w-3xl mx-auto">
        <div class="bg-white rounded-2xl shadow-sm border transition-shadow focus-within:shadow-md"
          style="border-color: #eef0f6;">
          <textarea
            v-model="inputText"
            @keydown.enter.exact.prevent="sendMessage"
            @keydown.enter.shift.exact="inputText += '\n'"
            placeholder="输入您的问题... （Enter 发送，Shift+Enter 换行）"
            rows="1"
            class="w-full resize-none bg-transparent px-4 pt-3.5 text-sm text-gray-700 focus:outline-none placeholder-gray-300 max-h-32 overflow-y-auto block"
            :disabled="store.isLoading || store.isStreaming"
            @input="autoResize"
            ref="textareaRef"
          ></textarea>
          <div class="flex items-center justify-between px-4 pb-3 pt-1">
            <span class="text-xs text-gray-300">AI 生成内容仅供参考</span>
            <button @click="sendMessage"
              :disabled="!inputText.trim() || store.isLoading || store.isStreaming"
              class="flex items-center gap-1.5 px-4 py-2 rounded-xl text-sm font-semibold text-white transition-all disabled:opacity-40 disabled:cursor-not-allowed"
              style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);">
              <span v-if="store.isStreaming">
                <svg class="animate-spin" width="14" height="14" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="10" stroke="rgba(255,255,255,0.3)" stroke-width="4"/><path d="M12 2a10 10 0 0 1 10 10" stroke="white" stroke-width="4" stroke-linecap="round"/></svg>
              </span>
              <span v-else>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.5"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
              </span>
              {{ store.isStreaming ? '生成中' : '发送' }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick, watch } from 'vue'
import { useChatStore } from '../store/chat.js'
import MessageBubble from './MessageBubble.vue'

const store = useChatStore()
const inputText = ref('')
const messageContainer = ref(null)
const textareaRef = ref(null)
const bottomAnchor = ref(null)

const quickQuestions = [
  { icon: '💸', text: '如何申请退款？' },
  { icon: '🛡️', text: '售后保障政策' },
  { icon: '👤', text: '联系人工客服' },
  { icon: '🔧', text: '产品质量问题处理' },
]

function scrollToBottom() {
  nextTick(() => {
    bottomAnchor.value?.scrollIntoView({ behavior: 'smooth' })
  })
}

watch(() => store.messages.length, scrollToBottom)
watch(() => store.isStreaming, (val) => { if (val) scrollToBottom() })

function sendMessage() {
  const text = inputText.value.trim()
  if (!text || store.isLoading || store.isStreaming) return
  inputText.value = ''
  resetTextarea()
  store.sendMessageStream(text, () => scrollToBottom(), () => scrollToBottom(), (err) => console.error(err))
}

function sendQuick(q) {
  inputText.value = q.text
  sendMessage()
}

function handleFeedback(msgId, isHelpful) {
  console.log('feedback', msgId, isHelpful)
}

function autoResize() {
  const ta = textareaRef.value
  if (!ta) return
  ta.style.height = 'auto'
  ta.style.height = Math.min(ta.scrollHeight, 128) + 'px'
}
function resetTextarea() {
  if (textareaRef.value) textareaRef.value.style.height = 'auto'
}
</script>
