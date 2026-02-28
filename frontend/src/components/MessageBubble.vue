<template>
  <div :class="['flex items-end gap-2.5 px-2 mb-1', isUser ? 'flex-row-reverse' : 'flex-row']">

    <!-- 头像 -->
    <div class="w-8 h-8 rounded-xl flex items-center justify-center flex-shrink-0 mb-1"
      :style="isUser
        ? 'background: linear-gradient(135deg, #f093fb, #f5576c);'
        : 'background: linear-gradient(135deg, #667eea, #764ba2);'">
      <svg v-if="!isUser" width="14" height="14" viewBox="0 0 24 24" fill="white"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 15v-4H7l5-8v4h4l-5 8z"/></svg>
      <svg v-else width="14" height="14" viewBox="0 0 24 24" fill="white"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4" fill="white"/></svg>
    </div>

    <!-- 气泡 + 元信息 -->
    <div :class="['flex flex-col max-w-[72%]', isUser ? 'items-end' : 'items-start']">
      <!-- 气泡 -->
      <div :class="[
        'relative px-4 py-3 text-sm leading-relaxed break-words',
        isUser
          ? 'text-white rounded-2xl rounded-br-sm'
          : 'text-gray-800 rounded-2xl rounded-bl-sm bg-white shadow-sm border',
      ]"
      :style="isUser
        ? 'background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);'
        : 'border-color: #eef0f6;'">

        <!-- AI 消息：Markdown 渲染 -->
        <div v-if="!isUser" v-html="renderedContent" class="prose-custom"></div>
        <!-- 用户消息：纯文本 -->
        <span v-else class="whitespace-pre-wrap">{{ message.content }}</span>

        <!-- 流式光标 -->
        <span v-if="message.streaming"
          class="inline-block w-0.5 h-4 ml-0.5 align-middle animate-blink"
          style="background: #667eea;"></span>
      </div>

      <!-- 底部元信息（AI 消息完成后显示） -->
      <div v-if="!isUser && !message.streaming && (message.intent || message.sources?.length || message.latency_ms)"
        class="flex flex-wrap items-center gap-1.5 mt-1.5 px-1">

        <!-- 意图标签 -->
        <span v-if="message.intent && message.intent !== 'unknown'"
          :style="intentStyle"
          class="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full font-medium">
          <span class="w-1.5 h-1.5 rounded-full" :style="dotStyle"></span>
          {{ intentLabel }}
        </span>

        <!-- 知识来源 -->
        <span v-if="message.sources?.length"
          class="text-xs flex items-center gap-1 px-2 py-0.5 rounded-full"
          style="background: #f0fdf4; color: #16a34a;">
          <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/></svg>
          {{ message.sources.length }} 条知识来源
        </span>

        <!-- 延迟 -->
        <span v-if="message.latency_ms" class="text-xs" style="color: #9ca3af;">
          {{ message.latency_ms }}ms
        </span>

        <!-- 反馈按钮 -->
        <div class="flex gap-1 ml-auto">
          <button @click="$emit('feedback', message.id, true)"
            :class="feedbackGiven === true ? 'text-green-500' : 'text-gray-300 hover:text-green-500'"
            class="w-6 h-6 rounded-lg flex items-center justify-center hover:bg-green-50 transition-all"
            @click.stop="giveFeedback(true)">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3H14z"/><path d="M7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3"/></svg>
          </button>
          <button @click="$emit('feedback', message.id, false)"
            :class="feedbackGiven === false ? 'text-red-400' : 'text-gray-300 hover:text-red-400'"
            class="w-6 h-6 rounded-lg flex items-center justify-center hover:bg-red-50 transition-all"
            @click.stop="giveFeedback(false)">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M10 15v4a3 3 0 0 0 3 3l4-9V2H5.72a2 2 0 0 0-2 1.7l-1.38 9a2 2 0 0 0 2 2.3H10z"/><path d="M17 2h2.67A2.31 2.31 0 0 1 22 4v7a2.31 2.31 0 0 1-2.33 2H17"/></svg>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { marked } from 'marked'

const props = defineProps({ message: { type: Object, required: true } })
defineEmits(['feedback'])

const isUser = computed(() => props.message.role === 'user')
const feedbackGiven = ref(null)

const renderedContent = computed(() => {
  try { return marked(props.message.content || '') }
  catch { return props.message.content || '' }
})

function giveFeedback(val) { feedbackGiven.value = val }

const INTENT_MAP = {
  inquiry:     { label: '咨询',   bg: '#eff6ff', color: '#2563eb', dot: '#3b82f6' },
  complaint:   { label: '投诉',   bg: '#fef2f2', color: '#dc2626', dot: '#ef4444' },
  after_sales: { label: '售后',   bg: '#fff7ed', color: '#c2410c', dot: '#f97316' },
  chitchat:    { label: '闲聊',   bg: '#f9fafb', color: '#6b7280', dot: '#9ca3af' },
  escalate:    { label: '转人工', bg: '#faf5ff', color: '#7c3aed', dot: '#8b5cf6' },
}

const intentLabel = computed(() => INTENT_MAP[props.message.intent]?.label || '')
const intentStyle = computed(() => {
  const m = INTENT_MAP[props.message.intent]
  return m ? `background: ${m.bg}; color: ${m.color};` : ''
})
const dotStyle = computed(() => {
  const m = INTENT_MAP[props.message.intent]
  return m ? `background: ${m.dot};` : ''
})
</script>

<style scoped>
@keyframes blink { 0%, 100% { opacity: 1 } 50% { opacity: 0 } }
.animate-blink { animation: blink 1s infinite; }

/* Prose 样式 */
.prose-custom :deep(p) { margin: 0.3rem 0; line-height: 1.65; }
.prose-custom :deep(p:first-child) { margin-top: 0; }
.prose-custom :deep(p:last-child) { margin-bottom: 0; }
.prose-custom :deep(ul), .prose-custom :deep(ol) { padding-left: 1.3rem; margin: 0.4rem 0; }
.prose-custom :deep(li) { margin: 0.15rem 0; }
.prose-custom :deep(strong) { font-weight: 600; color: #1e293b; }
.prose-custom :deep(em) { color: #475569; }
.prose-custom :deep(code) {
  background: #f1f5f9;
  color: #7c3aed;
  padding: 0.1em 0.35em;
  border-radius: 4px;
  font-size: 0.82em;
  font-family: 'SFMono-Regular', Consolas, monospace;
}
.prose-custom :deep(pre) {
  background: #0f172a;
  color: #e2e8f0;
  padding: 1rem;
  border-radius: 10px;
  overflow-x: auto;
  margin: 0.5rem 0;
  font-size: 0.8em;
}
.prose-custom :deep(pre code) {
  background: transparent;
  color: inherit;
  padding: 0;
  border-radius: 0;
}
.prose-custom :deep(blockquote) {
  border-left: 3px solid #667eea;
  padding-left: 0.75rem;
  margin: 0.5rem 0;
  color: #64748b;
  font-style: italic;
}
.prose-custom :deep(h1), .prose-custom :deep(h2), .prose-custom :deep(h3) {
  font-weight: 600;
  color: #1e293b;
  margin: 0.5rem 0 0.25rem;
}
.prose-custom :deep(a) { color: #667eea; text-decoration: underline; }
.prose-custom :deep(hr) { border-color: #e5e7eb; margin: 0.5rem 0; }
</style>
