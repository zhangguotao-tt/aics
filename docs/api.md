# API 接口文档

> 基础 URL：`http://localhost:8000`
> 所有需要认证的接口须在请求头携带：`Authorization: Bearer <access_token>`

---

## 目录

- [认证 Auth](#认证-auth)
- [对话 Chat](#对话-chat)
- [知识库 Knowledge](#知识库-knowledge)
- [管理后台 Admin](#管理后台-admin)
- [WebSocket 实时对话](#websocket-实时对话)
- [错误码说明](#错误码说明)

---

## 认证 Auth

### POST `/auth/register` — 用户注册

**请求体**

```json
{
  "username": "demo_user",
  "email": "demo@example.com",
  "password": "Demo@1234"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| username | string | ✅ | 3-32 位，字母数字下划线 |
| email | string | ✅ | 有效邮箱地址 |
| password | string | ✅ | 8-64 位，需含大小写字母和数字 |

**响应 200**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "username": "demo_user",
  "email": "demo@example.com",
  "role": "user",
  "access_token": "eyJhbGci...",
  "refresh_token": "eyJhbGci...",
  "token_type": "bearer"
}
```

---

### POST `/auth/login` — 用户登录

**请求体**

```json
{
  "username": "demo_user",
  "password": "Demo@1234"
}
```

**响应 200** — 同注册响应结构

**错误情况**

| 状态码 | 原因 |
|--------|------|
| 401 | 用户名或密码错误 |
| 423 | 账号已锁定（连续5次错误后锁定30分钟） |

---

### GET `/auth/me` — 获取当前用户信息

**需要认证** ✅

**响应 200**

```json
{
  "id": "550e8400-...",
  "username": "demo_user",
  "email": "demo@example.com",
  "role": "user",
  "created_at": "2024-01-01T08:00:00"
}
```

---

### POST `/auth/change-password` — 修改密码

**需要认证** ✅

**请求体**

```json
{
  "old_password": "Demo@1234",
  "new_password": "NewPass@5678"
}
```

---

## 对话 Chat

### POST `/chat/message` — 发送消息（REST 方式）

**需要认证** ✅（可选，访客也可使用）

**请求体**

```json
{
  "session_id": "session-uuid-001",
  "message": "如何申请退款？",
  "stream": false
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| session_id | string | ✅ | 会话唯一标识（客户端生成 UUID） |
| message | string | ✅ | 用户消息，最长 2000 字符 |
| stream | boolean | ❌ | false=完整响应（默认），true=SSE流式 |

**响应 200**

```json
{
  "session_id": "session-uuid-001",
  "reply": "您好！退款申请步骤如下：\n1. 进入订单中心...",
  "intent": "after_sales",
  "intent_confidence": 0.92,
  "rag_sources": [
    {
      "id": "chunk-001",
      "content": "退款流程：进入订单页面...",
      "source": "退款政策.pdf",
      "score": 0.87
    }
  ],
  "latency_ms": 1240,
  "usage": {
    "prompt_tokens": 320,
    "completion_tokens": 180,
    "total_tokens": 500
  }
}
```

---

### GET `/chat/history/{session_id}` — 获取对话历史

**需要认证** ✅

**路径参数**

| 参数 | 说明 |
|------|------|
| session_id | 会话 ID |

**查询参数**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| limit | int | 20 | 返回消息数量上限 |
| offset | int | 0 | 偏移量（分页） |

**响应 200**

```json
{
  "session_id": "session-uuid-001",
  "messages": [
    {
      "id": "msg-001",
      "role": "user",
      "content": "如何申请退款？",
      "created_at": "2024-01-01T10:00:00"
    },
    {
      "id": "msg-002",
      "role": "assistant",
      "content": "您好！退款申请步骤如下...",
      "intent": "after_sales",
      "rag_sources": [...],
      "latency_ms": 1240,
      "created_at": "2024-01-01T10:00:01"
    }
  ],
  "total": 2
}
```

---

### POST `/chat/end/{session_id}` — 结束会话

**需要认证** ✅

**响应 200**

```json
{
  "session_id": "session-uuid-001",
  "status": "ended",
  "turn_count": 5,
  "total_tokens": 1200
}
```

---

### POST `/chat/feedback` — 消息反馈

**需要认证** ✅

**请求体**

```json
{
  "message_id": "msg-002",
  "rating": 5,
  "is_helpful": true,
  "comment": "回答准确，很有帮助"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| message_id | string | ✅ | 被评价的消息 ID |
| rating | int | ❌ | 1-5 星评分 |
| is_helpful | boolean | ❌ | 是否有帮助 |
| comment | string | ❌ | 文字评价，最长 500 字符 |

---

## 知识库 Knowledge

### POST `/knowledge/upload` — 上传知识文档

**需要认证** ✅（需要 agent 或 admin 角色）

**请求**：`multipart/form-data`

| 字段 | 类型 | 说明 |
|------|------|------|
| file | File | 支持格式：PDF / DOCX / TXT / MD |
| description | string | 文档描述（可选） |
| tags | string | 逗号分隔的标签（可选） |

**响应 202**（异步处理）

```json
{
  "document_id": "doc-uuid-001",
  "filename": "退款政策.pdf",
  "status": "processing",
  "message": "文档已提交，正在后台向量化处理"
}
```

**文档状态流转**：`processing` → `completed` / `failed`

---

### GET `/knowledge/list` — 获取文档列表

**需要认证** ✅（需要 agent 或 admin 角色）

**查询参数**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| page | int | 1 | 页码 |
| page_size | int | 20 | 每页数量 |
| status | string | all | 过滤状态：processing/completed/failed |

**响应 200**

```json
{
  "items": [
    {
      "id": "doc-uuid-001",
      "filename": "退款政策.pdf",
      "description": "退款退货相关政策文档",
      "status": "completed",
      "chunk_count": 24,
      "file_size": 102400,
      "created_at": "2024-01-01T08:00:00"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 20
}
```

---

### DELETE `/knowledge/{document_id}` — 删除文档

**需要认证** ✅（需要 admin 角色）

**响应 200**

```json
{
  "document_id": "doc-uuid-001",
  "deleted": true
}
```

---

### POST `/knowledge/search` — 语义搜索

**需要认证** ✅

**请求体**

```json
{
  "query": "如何申请退款",
  "top_k": 5,
  "score_threshold": 0.6
}
```

**响应 200**

```json
{
  "query": "如何申请退款",
  "results": [
    {
      "id": "chunk-001",
      "content": "退款流程：1. 登录账户 2. 进入订单中心...",
      "source": "退款政策.pdf",
      "score": 0.89,
      "metadata": {
        "document_id": "doc-uuid-001",
        "chunk_index": 3
      }
    }
  ]
}
```

---

## 管理后台 Admin

> 以下接口均需要 **admin** 角色

### GET `/admin/stats` — 系统统计概览

**响应 200**

```json
{
  "period_days": 7,
  "total_conversations": 1250,
  "total_messages": 6800,
  "avg_latency_ms": 1320,
  "p95_latency_ms": 3200,
  "rag_hit_rate": 0.73,
  "intent_distribution": {
    "inquiry": 0.45,
    "after_sales": 0.28,
    "complaint": 0.12,
    "chitchat": 0.10,
    "escalate": 0.05
  },
  "avg_satisfaction": 4.2,
  "helpful_rate": 0.85
}
```

---

### GET `/admin/conversations` — 对话列表

**查询参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| page | int | 页码 |
| page_size | int | 每页数量 |
| intent | string | 过滤意图类型 |
| date_from | string | 开始日期 YYYY-MM-DD |
| date_to | string | 结束日期 YYYY-MM-DD |

---

### GET `/admin/users` — 用户列表

**查询参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| page | int | 页码 |
| role | string | 过滤角色：user/agent/admin |
| is_active | boolean | 是否激活 |

---

## WebSocket 实时对话

### `WS /ws/chat/{session_id}` — 流式对话

**连接参数**

```
ws://localhost:8000/ws/chat/{session_id}?token={access_token}
```

**发送消息**（JSON 字符串）

```json
{
  "message": "如何申请退款？"
}
```

**接收消息类型**

| type | 说明 | data 字段 |
|------|------|-----------|
| `token` | 流式 token（逐字输出） | `{"token": "您"}` |
| `done` | 响应完成 | `{"intent": "after_sales", "latency_ms": 1240, ...}` |
| `error` | 发生错误 | `{"message": "错误信息"}` |

**示例接收序列**

```
{"type": "token", "data": {"token": "您"}}
{"type": "token", "data": {"token": "好"}}
{"type": "token", "data": {"token": "！"}}
...
{"type": "done", "data": {"intent": "after_sales", "latency_ms": 1240, "rag_sources": [...]}}
```

---

## 错误码说明

| HTTP 状态码 | 说明 |
|-------------|------|
| 400 | 请求参数错误 |
| 401 | 未认证或 Token 过期 |
| 403 | 权限不足 |
| 404 | 资源不存在 |
| 409 | 冲突（如用户名已存在） |
| 422 | 请求体格式校验失败 |
| 423 | 账号已锁定 |
| 429 | 请求频率超限（默认 60次/分钟） |
| 500 | 服务器内部错误 |
| 503 | LLM 服务不可用 |

**错误响应格式**

```json
{
  "detail": "用户名已存在",
  "code": "USERNAME_TAKEN",
  "request_id": "a1b2c3d4"
}
```

---

> 📘 FastAPI 自动生成的交互式文档：
> - Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
> - ReDoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)
