<template>
  <!-- 知识库管理后台 -->
  <div class="min-h-screen bg-gray-50">
    <!-- 顶部导航 -->
    <header class="bg-white border-b px-6 py-4 flex items-center justify-between">
      <h1 class="text-xl font-bold text-gray-800">📚 知识库管理</h1>
      <button @click="showUpload = true"
        class="bg-blue-500 text-white px-4 py-2 rounded-lg text-sm hover:bg-blue-600 transition-colors">
        + 上传文档
      </button>
    </header>

    <div class="p-6 max-w-6xl mx-auto">
      <!-- 统计卡片 -->
      <div class="grid grid-cols-4 gap-4 mb-6" v-if="stats">
        <div v-for="(val, key) in statsDisplay" :key="key" class="bg-white rounded-xl p-4 shadow-sm border">
          <p class="text-sm text-gray-500">{{ val.label }}</p>
          <p class="text-2xl font-bold text-gray-800 mt-1">{{ val.value }}</p>
        </div>
      </div>

      <!-- 搜索框 -->
      <div class="bg-white rounded-xl p-4 shadow-sm border mb-4 flex gap-3">
        <input v-model="searchQuery" type="text" placeholder="语义搜索知识库..."
          class="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400" />
        <button @click="doSearch" class="bg-blue-500 text-white px-4 py-2 rounded-lg text-sm hover:bg-blue-600">
          搜索
        </button>
      </div>

      <!-- 搜索结果 -->
      <div v-if="searchResults.length" class="bg-white rounded-xl p-4 shadow-sm border mb-4">
        <h3 class="font-medium text-gray-700 mb-3">搜索结果（{{ searchResults.length }} 条）</h3>
        <div v-for="r in searchResults" :key="r.id" class="border-b border-gray-100 py-3 last:border-0">
          <div class="flex justify-between items-start">
            <p class="text-sm text-gray-800 flex-1">{{ r.content }}</p>
            <span class="ml-4 text-xs bg-green-50 text-green-600 px-2 py-0.5 rounded-full flex-shrink-0">
              {{ (r.score * 100).toFixed(1) }}%
            </span>
          </div>
          <p class="text-xs text-gray-400 mt-1">来源: {{ r.source }}</p>
        </div>
      </div>

      <!-- 文档列表 -->
      <div class="bg-white rounded-xl shadow-sm border overflow-hidden">
        <table class="w-full text-sm">
          <thead class="bg-gray-50 border-b">
            <tr>
              <th class="text-left px-4 py-3 text-gray-600 font-medium">文档名称</th>
              <th class="text-left px-4 py-3 text-gray-600 font-medium">状态</th>
              <th class="text-left px-4 py-3 text-gray-600 font-medium">分类</th>
              <th class="text-left px-4 py-3 text-gray-600 font-medium">分块数</th>
              <th class="text-left px-4 py-3 text-gray-600 font-medium">创建时间</th>
              <th class="text-left px-4 py-3 text-gray-600 font-medium">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="doc in documents" :key="doc.id" class="border-b border-gray-50 hover:bg-gray-50 transition-colors">
              <td class="px-4 py-3 font-medium text-gray-800">{{ doc.title }}</td>
              <td class="px-4 py-3">
                <span :class="statusClass(doc.status)" class="text-xs px-2 py-0.5 rounded-full">
                  {{ statusLabel(doc.status) }}
                </span>
              </td>
              <td class="px-4 py-3 text-gray-500">{{ doc.category || '-' }}</td>
              <td class="px-4 py-3 text-gray-500">{{ doc.chunk_count }}</td>
              <td class="px-4 py-3 text-gray-400 text-xs">{{ formatDate(doc.created_at) }}</td>
              <td class="px-4 py-3">
                <button @click="deleteDoc(doc.id)"
                  class="text-red-400 hover:text-red-600 text-xs transition-colors">删除</button>
              </td>
            </tr>
            <tr v-if="!documents.length">
              <td colspan="6" class="text-center py-12 text-gray-400">暂无文档，请上传知识库文件</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- 上传弹窗 -->
    <div v-if="showUpload" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div class="bg-white rounded-2xl p-6 w-full max-w-md shadow-xl">
        <h3 class="text-lg font-semibold mb-4">上传知识文档</h3>
        <div class="space-y-3">
          <input v-model="uploadForm.title" type="text" placeholder="文档标题 *"
            class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400" />
          <input v-model="uploadForm.category" type="text" placeholder="分类（可选）"
            class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400" />
          <div @drop.prevent="handleDrop" @dragover.prevent
            class="border-2 border-dashed border-gray-300 rounded-xl p-6 text-center cursor-pointer hover:border-blue-400 transition-colors"
            @click="$refs.fileInput.click()">
            <p class="text-gray-500 text-sm">{{ uploadFile ? uploadFile.name : '点击或拖拽上传文件' }}</p>
            <p class="text-xs text-gray-400 mt-1">支持 PDF / Word / TXT / Markdown，最大 10MB</p>
          </div>
          <input ref="fileInput" type="file" accept=".pdf,.docx,.txt,.md" class="hidden" @change="onFileChange" />
        </div>
        <div class="flex gap-3 mt-5">
          <button @click="showUpload = false; uploadFile = null; uploadForm = {}"
            class="flex-1 border border-gray-300 text-gray-600 py-2 rounded-lg text-sm hover:bg-gray-50">取消</button>
          <button @click="doUpload" :disabled="uploading || !uploadFile || !uploadForm.title"
            class="flex-1 bg-blue-500 text-white py-2 rounded-lg text-sm hover:bg-blue-600 disabled:bg-gray-300 disabled:cursor-not-allowed">
            {{ uploading ? '上传中...' : '确认上传' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { knowledgeAPI, adminAPI } from '../api/index.js'

const documents = ref([])
const stats = ref(null)
const searchQuery = ref('')
const searchResults = ref([])
const showUpload = ref(false)
const uploading = ref(false)
const uploadFile = ref(null)
const uploadForm = ref({ title: '', category: '' })

onMounted(async () => {
  await loadDocuments()
  try { stats.value = await adminAPI.stats() } catch {}
})

const statsDisplay = computed(() => ({
  docs:  { label: '知识文档', value: stats.value?.knowledge_documents ?? '-' },
  convs: { label: '总对话数', value: stats.value?.conversations ?? '-' },
  msgs:  { label: '总消息数', value: stats.value?.messages ?? '-' },
  users: { label: '用户数',   value: stats.value?.users ?? '-' },
}))

async function loadDocuments() {
  try { documents.value = (await knowledgeAPI.list()).items || [] } catch {}
}

async function doSearch() {
  if (!searchQuery.value.trim()) return
  searchResults.value = (await knowledgeAPI.search(searchQuery.value)).results || []
}

async function deleteDoc(id) {
  if (!confirm('确定删除该文档？此操作会同时删除相关向量。')) return
  await knowledgeAPI.delete(id)
  await loadDocuments()
}

function onFileChange(e) {
  uploadFile.value = e.target.files[0]
}
function handleDrop(e) {
  uploadFile.value = e.dataTransfer.files[0]
}

async function doUpload() {
  if (!uploadFile.value || !uploadForm.value.title) return
  uploading.value = true
  try {
    const fd = new FormData()
    fd.append('file', uploadFile.value)
    fd.append('title', uploadForm.value.title)
    if (uploadForm.value.category) fd.append('category', uploadForm.value.category)
    await knowledgeAPI.upload(fd)
    showUpload.value = false
    uploadFile.value = null
    uploadForm.value = {}
    await loadDocuments()
  } catch (e) {
    alert('上传失败：' + e)
  } finally {
    uploading.value = false
  }
}

const STATUS_MAP = {
  active:     { label: '已激活', cls: 'bg-green-50 text-green-600' },
  processing: { label: '处理中', cls: 'bg-yellow-50 text-yellow-600' },
  pending:    { label: '待处理', cls: 'bg-gray-50 text-gray-500' },
  failed:     { label: '失败',   cls: 'bg-red-50 text-red-600' },
  archived:   { label: '已归档', cls: 'bg-gray-50 text-gray-400' },
}
const statusLabel = (s) => STATUS_MAP[s]?.label || s
const statusClass = (s) => STATUS_MAP[s]?.cls || ''
const formatDate = (d) => d ? new Date(d).toLocaleDateString('zh-CN') : '-'
</script>
