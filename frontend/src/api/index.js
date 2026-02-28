/**
 * API 请求封装
 * 封装 axios，统一处理 baseURL、JWT Token、错误拦截
 */
import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

// 请求拦截：自动附加 JWT Token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// 响应拦截：统一错误处理
api.interceptors.response.use(
  (res) => res.data,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('access_token')
      window.location.reload()
    }
    return Promise.reject(err.response?.data?.detail || '请求失败')
  }
)

// ── 认证 API ────────────────────────────────────────────────
export const authAPI = {
  login:    (data) => api.post('/auth/login', data),
  register: (data) => api.post('/auth/register', data),
  me:       ()     => api.get('/auth/me'),
  changePassword: (data) => api.post('/auth/change-password', data),
}

// ── 对话 API ────────────────────────────────────────────────
export const chatAPI = {
  sendMessage: (data) => api.post('/chat/message', data),
  getHistory:  (sid)  => api.get(`/chat/history/${sid}`),
  endSession:  (sid)  => api.post(`/chat/end/${sid}`),
  feedback:    (data) => api.post('/chat/feedback', data),
}

// ── 知识库 API ───────────────────────────────────────────────
export const knowledgeAPI = {
  list:   (params) => api.get('/knowledge/list', { params }),
  upload: (formData) => api.post('/knowledge/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }),
  delete: (id)    => api.delete(`/knowledge/${id}`),
  search: (query, topK = 5) => api.post('/knowledge/search', null, {
    params: { query, top_k: topK },
  }),
}

// ── 管理 API ─────────────────────────────────────────────────
export const adminAPI = {
  stats:         () => api.get('/admin/stats'),
  conversations: (params) => api.get('/admin/conversations', { params }),
  users:         (params) => api.get('/admin/users', { params }),
}

export default api
