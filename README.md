# 🤖 LLM 智能客服系统

基于大语言模型（LLM）的企业级智能客服系统，集成 RAG 检索增强生成、多轮对话记忆、意图识别等核心功能。

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                        客户端层                              │
│          Vue3 前端  ──  WebSocket  ──  REST API             │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                      API 网关层 (FastAPI)                    │
│        认证中间件  │  限流中间件  │  日志中间件              │
└──────┬──────────────┬──────────────┬──────────────┬─────────┘
       │              │              │              │
┌──────▼──────┐ ┌──────▼──────┐ ┌──────▼──────┐ ┌──▼────────┐
│  对话服务   │ │  知识库服务 │ │  用户服务   │ │  评估服务 │
└──────┬──────┘ └──────┬──────┘ └──────┬──────┘ └──────────┘
       │              │              │
┌──────▼──────────────▼──────────────▼──────────────────────┐
│                      核心引擎层                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │ LLM客户端 │  │ RAG检索  │  │ 意图识别 │  │ 记忆管理 │  │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘  │
└──────────────────────┬─────────────────────────────────────┘
                       │
┌──────────────────────▼─────────────────────────────────────┐
│                      存储层                                 │
│   PostgreSQL    │    Redis    │    ChromaDB    │  文件存储  │
│  (用户/对话)    │   (缓存)    │  (向量数据库)  │  (文档)   │
└────────────────────────────────────────────────────────────┘
```

## 🛠️ 技术栈

| 层级 | 技术 | 版本 |
|------|------|------|
| 后端框架 | FastAPI | 0.115+ |
| LLM 编排 | LangChain | 0.3+ |
| LLM 模型 | OpenAI / DeepSeek / Ollama / Azure OpenAI | - |
| Embedding | OpenAI / 千问 DashScope / Ollama（按 LLM 方案切换） | - |
| 向量数据库 | ChromaDB | 0.5+ |
| 关系数据库 | PostgreSQL | 15+ |
| 缓存 | Redis | 7+ |
| 前端框架 | Vue 3 + Vite | - |
| 认证 | JWT (python-jose) | - |
| 容器化 | Docker + Docker Compose | - |
| 测试 | Pytest | 7+ |

## 📁 项目结构

```
aics-tt/
├── backend/                    # 后端服务
│   ├── main.py                 # FastAPI 入口
│   ├── config.py               # 全局配置
│   ├── api/                    # API 路由层
│   │   ├── routes/
│   │   │   ├── chat.py         # 对话接口
│   │   │   ├── auth.py         # 认证接口
│   │   │   ├── knowledge.py    # 知识库接口
│   │   │   └── admin.py        # 管理后台接口
│   │   └── middleware/
│   │       ├── auth.py         # 认证中间件
│   │       └── rate_limit.py   # 限流中间件
│   ├── core/                   # 核心业务逻辑
│   │   ├── llm/
│   │   │   ├── client.py       # LLM 客户端 (OpenAI/DeepSeek/Ollama/Azure)
│   │   │   └── prompt_manager.py # Prompt 模板管理
│   │   ├── rag/
│   │   │   ├── retriever.py    # RAG 检索（向量化+相似度检索）
│   │   │   └── vector_store.py # ChromaDB 管理
│   │   ├── memory/
│   │   │   └── conversation_memory.py # 对话上下文记忆
│   │   └── intent/
│   │       └── classifier.py   # 意图识别分类器
│   ├── models/                 # 数据模型 (SQLAlchemy)
│   │   ├── user.py
│   │   ├── conversation.py
│   │   └── knowledge.py
│   ├── services/               # 业务服务层
│   │   ├── chat_service.py     # 对话编排服务
│   │   └── auth_service.py     # 用户认证
│   ├── db/                     # 数据库连接
│   │   └── database.py
│   └── utils/                  # 工具类
│       ├── logger.py           # 结构化日志+审计
│       └── performance.py      # 多级缓存+性能优化
├── frontend/                   # Vue3 前端
│   ├── index.html
│   ├── vite.config.js
│   ├── nginx.conf              # Nginx 生产配置
│   ├── Dockerfile              # 多阶段构建
│   ├── package.json
│   └── src/
│       ├── App.vue
│       ├── components/
│       │   ├── ChatWindow.vue  # 聊天主窗口
│       │   ├── MessageBubble.vue # 消息气泡
│       │   └── KnowledgeAdmin.vue # 知识库管理
│       ├── store/
│       │   └── chat.js         # Pinia 状态管理
│       └── api/
│           └── index.js        # API 请求封装
├── tests/
│   ├── conftest.py             # pytest 公共 fixtures
│   ├── unit/                   # 单元测试
│   │   ├── test_intent_classifier.py
│   │   ├── test_conversation_memory.py
│   │   └── test_chat_service.py
│   └── integration/            # 集成测试
│       └── test_api.py
├── docs/
│   ├── architecture.md         # 系统架构文档
│   └── api.md                  # 完整 API 接口文档
├── scripts/                    # 可选脚本（按需添加）
├── data/
│   ├── knowledge/              # 知识库文档（放入待导入文件）
│   └── chroma_db/              # 向量数据库持久化
├── logs/                       # 运行日志（自动创建）
├── docker-compose.yml
├── .env                        # 环境变量（复制 .env.example 或从文档配置）
├── backend/requirements.txt
└── frontend/package.json
```

## 🔌 LLM 与 Embedding 方案说明

| `LLM_PROVIDER` | 聊天模型 | RAG 向量化（Embedding） |
|----------------|----------|--------------------------|
| `openai` | OpenAI（如 gpt-4o-mini） | OpenAI（如 text-embedding-3-small） |
| `deepseek` | DeepSeek（deepseek-chat） | **千问 DashScope**（text-embedding-v3），需配置 `DASHSCOPE_API_KEY` |
| `ollama` | Ollama 本地模型（如 qwen2.5:7b） | Ollama（nomic-embed-text） |
| `azure_openai` | Azure OpenAI 部署 | Azure OpenAI Embeddings |

选择 DeepSeek 时，RAG 知识库检索使用阿里云通义千问的 Embedding 接口（DashScope），需在 [阿里云百炼](https://dashscope.aliyun.com/) 开通并配置 `DASHSCOPE_API_KEY` 与 `DASHSCOPE_EMBEDDING_MODEL`。

---

## 🚀 快速开始

### 方式一：Ollama + Docker Compose（免费推荐）

使用本地 Ollama 模型，完全免费，无需 OpenAI API Key。

```bash
# 1. 安装 Ollama
curl -fsSL https://ollama.com/install.sh | sh

# 2. 拉取模型（聊天模型 ~4.7GB + 嵌入模型 ~274MB）
ollama pull qwen2.5:7b
ollama pull nomic-embed-text

# 3. 配置 Ollama 监听所有接口（让 Docker 容器可访问）
sudo mkdir -p /etc/systemd/system/ollama.service.d
echo -e '[Service]\nEnvironment="OLLAMA_HOST=0.0.0.0"' | sudo tee /etc/systemd/system/ollama.service.d/override.conf
sudo systemctl daemon-reload && sudo systemctl restart ollama

# 4. 克隆项目并进入目录
git clone <你的仓库地址> aics-tt
cd aics-tt

# 5. 配置环境变量
cp .env.example .env   # 若无 .env.example 则复制项目内 .env 并改名为备份后编辑 .env
# 设置 LLM_PROVIDER=ollama，并配置数据库密码等必填项

# 6. 启动所有服务
docker compose up -d

# 7. 查看服务状态
docker compose ps

# 8. 访问系统
# 前端界面:    http://localhost
# API 文档:   http://localhost:8000/docs
```

### 方式二：DeepSeek（聊天）+ 千问 DashScope（RAG 向量化）+ Docker Compose

聊天使用 DeepSeek，RAG 知识库检索使用阿里云通义千问 Embedding（需 DashScope API Key）。

```bash
# 1. 克隆项目并进入目录
git clone <你的仓库地址> aics-tt
cd aics-tt

# 2. 配置环境变量
# 编辑 .env，设置：
#   LLM_PROVIDER=deepseek
#   DEEPSEEK_API_KEY=sk-xxx          # DeepSeek 开放平台 API Key
#   DASHSCOPE_API_KEY=sk-xxx          # 阿里云百炼 / DashScope API Key（千问 Embedding）
#   DASHSCOPE_EMBEDDING_MODEL=text-embedding-v3
#   POSTGRES_PASSWORD=your-password
#   DATABASE_URL=postgresql+asyncpg://cs_user:your-password@postgres:5432/customer_service

# 3. 启动所有服务
docker compose up -d

# 4. 访问系统
# 前端界面:    http://localhost
# API 文档:   http://localhost:8000/docs
```

### 方式三：OpenAI API + Docker Compose

```bash
# 1. 克隆项目并进入目录
git clone <你的仓库地址> aics-tt
cd aics-tt

# 2. 配置环境变量
# 编辑 .env：
#   LLM_PROVIDER=openai
#   OPENAI_API_KEY=sk-your-key
#   POSTGRES_PASSWORD=your-password
#   DATABASE_URL=...

# 3. 启动所有服务
docker compose up -d

# 4. 访问系统
# 前端界面:    http://localhost
# API 文档:   http://localhost:8000/docs
```

### 方式四：本地开发模式（不使用 Docker）

```bash
# 环境要求：Python 3.11+、Node.js 20+、PostgreSQL 15+、Redis 7+

# 1. 安装 Python 依赖
cd backend && pip install -r requirements.txt

# 2. 配置环境变量
# 复制并编辑 .env，设置数据库连接、LLM_PROVIDER 及对应 API Key

# 3. 初始化数据库（创建表 + 默认管理员账号）
# 使用 Alembic 或项目提供的初始化方式（见 backend 文档）

# 4. 知识库文档可通过前端「知识库管理」上传，或放入 data/ 后由后端导入

# 5. 启动后端
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 6. 启动前端（新终端）
cd frontend
npm install && npm run dev
# 访问 http://localhost:5173
```

### 默认账号

| 账号 | 密码 | 角色 |
|------|------|------|
| admin | Admin@123456 | 管理员 |

> ⚠️ 首次登录后请立即修改密码

---

## 📡 API 接口摘要

| 方法 | 路径 | 描述 | 认证 |
|------|------|------|------|
| POST | `/auth/register` | 用户注册 | ❌ |
| POST | `/auth/login` | 用户登录 | ❌ |
| GET  | `/auth/me` | 当前用户信息 | ✅ |
| POST | `/chat/message` | 发送消息（REST） | 可选 |
| GET  | `/chat/history/{session_id}` | 对话历史 | ✅ |
| POST | `/chat/end/{session_id}` | 结束会话 | ✅ |
| POST | `/chat/feedback` | 消息评分 | ✅ |
| WS   | `/ws/chat/{session_id}` | WebSocket 流式对话 | ✅ |
| POST | `/knowledge/upload` | 上传知识文档 | agent+ |
| GET  | `/knowledge/list` | 文档列表 | agent+ |
| DELETE | `/knowledge/{id}` | 删除文档 | admin |
| POST | `/knowledge/search` | 语义搜索 | ✅ |
| GET  | `/admin/stats` | 系统统计 | admin |
| GET  | `/admin/conversations` | 对话列表 | admin |
| GET  | `/admin/users` | 用户列表 | admin |
| GET  | `/health` | 健康检查 | ❌ |

📖 完整接口文档可访问 `http://localhost:8000/docs`（开发环境下）

---

## ⚙️ 主要环境变量

| 变量 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `LLM_PROVIDER` | ❌ | `openai` | `openai` / `ollama` / `azure_openai` / `deepseek` |
| `OLLAMA_BASE_URL` | Ollama 时 | `http://host.docker.internal:11434` | Docker 内访问宿主机 Ollama |
| `OLLAMA_MODEL` | ❌ | `qwen2.5:7b` | Ollama 聊天模型名 |
| `OPENAI_API_KEY` | OpenAI 时 | - | OpenAI API 密钥 |
| `OPENAI_EMBEDDING_MODEL` | ❌ | `text-embedding-3-small` | OpenAI 向量模型（LLM=openai 时 RAG 使用） |
| `DEEPSEEK_API_KEY` | DeepSeek 时 | - | DeepSeek 开放平台 API Key（聊天） |
| `DEEPSEEK_API_BASE` | ❌ | `https://api.deepseek.com` | DeepSeek API 地址（勿加 `/v1`） |
| `DASHSCOPE_API_KEY` | DeepSeek 时 | - | 阿里云 DashScope API Key（千问 Embedding，RAG 向量化） |
| `DASHSCOPE_EMBEDDING_MODEL` | ❌ | `text-embedding-v3` | 千问 Embedding 模型（仅当 LLM=deepseek 时生效） |
| `POSTGRES_PASSWORD` | ✅ | - | PostgreSQL 密码 |
| `DATABASE_URL` | ✅ | - | PostgreSQL 连接串 |
| `REDIS_URL` | ❌ | `redis://redis:6379/0` | Redis 连接串 |
| `SECRET_KEY` | ✅ | - | 应用密钥（生产必须修改） |
| `JWT_SECRET_KEY` | ✅ | - | JWT 签名密钥（生产必须修改） |

---

## 🔑 核心特性

- ✅ **多轮对话** — Redis 滑动窗口上下文管理，支持 N 轮记忆
- ✅ **RAG 检索增强** — ChromaDB 向量检索 + 多级缓存（L1 内存 + L2 Redis）
- ✅ **意图识别** — 规则优先 + LLM 兜底，自动识别 6 类用户意图
- ✅ **流式输出** — WebSocket 实时 Token 流式传输，毫秒级首字节响应
- ✅ **多模型支持** — OpenAI / DeepSeek / Ollama / Azure OpenAI 无缝切换；DeepSeek 可选搭配千问 Embedding 做 RAG
- ✅ **JWT 认证** — Access Token（1h）+ Refresh Token（7d），登录锁定保护
- ✅ **性能优化** — Embedding 批量缓存（TTL 24h）、热点知识预热、DB 连接池
- ✅ **结构化日志** — request_id 传播、LLM 调用追踪、JSON Lines 审计日志
- ✅ **质量监控** — P95 延迟、RAG 命中率、意图分布、用户满意度指标
- ✅ **容器化部署** — 多阶段 Dockerfile、Nginx 反向代理、Docker Compose 编排

---

## 🎓 模型训练与微调

> 对于大多数客服场景，推荐先通过**充实知识库 + 调优 Prompt** 提升效果，再考虑微调。

### 方案对比

| 方案 | 成本 | 效果提升 | 难度 |
|------|------|----------|------|
| 上传知识库文档（RAG） | 免费 | ⭐⭐⭐ | 低 |
| 调优系统 Prompt | 免费 | ⭐⭐ | 低 |
| LoRA 微调 | 需要 GPU | ⭐⭐⭐⭐ | 中 |
| 全量微调 / 预训练 | 需要多卡 | ⭐⭐⭐⭐⭐ | 高 |

---

### 方案一：充实知识库（无需训练，推荐优先尝试）

将业务文档放入知识库，模型会自动检索后回答：

```bash
# 支持格式：PDF、DOCX、TXT、MD
mkdir -p data/knowledge
cp your-docs/*.pdf data/knowledge/

# 批量导入
python scripts/load_knowledge.py --dir data/knowledge

# 或通过前端界面上传（管理员账号登录后操作）
```

---

### 方案二：调优系统 Prompt

修改 [backend/core/llm/prompt_manager.py](backend/core/llm/prompt_manager.py) 中的系统提示词，让模型更贴合你的业务场景：

```python
SYSTEM_PROMPT = """你是XX公司的智能客服助手，专注于处理售后、退款、物流等问题。
回答风格：简洁、礼貌、专业。
当无法回答时，引导用户联系人工客服：400-xxx-xxxx。"""
```

---

### 方案三：LoRA 微调 qwen2.5:7b

使用自己的对话数据对模型进行微调，效果最好。

#### 硬件要求
| 方法 | 显存需求 | 说明 |
|------|----------|------|
| QLoRA（4-bit 量化） | 10~16 GB | RTX 3080/4070/3090 可用 |
| LoRA（bf16） | 24 GB+ | RTX 4090 / A100 |
| CPU 训练 | 无 GPU 要求 | 极慢，不推荐 |

#### 1. 准备训练数据

创建 `data/finetune/train.json`，格式如下：

```json
[
  {
    "instruction": "你是一名专业客服，请回答用户问题",
    "input": "我的订单还没到，怎么查物流？",
    "output": "您好！您可以通过以下方式查询物流：\n1. 登录官网「我的订单」页面点击「查看物流」\n2. 在快递公司官网输入运单号查询\n如有疑问请提供订单号，我为您进一步查询。"
  },
  {
    "instruction": "你是一名专业客服，请回答用户问题",
    "input": "如何申请退款？",
    "output": "退款申请步骤：\n1. 登录账号进入「我的订单」\n2. 找到对应订单点击「申请退款」\n3. 选择退款原因并提交\n收到申请后1-3个工作日内审核，退款将原路返回。"
  }
]
```

数据量建议：**300条以上**效果明显，1000条以上效果稳定。

#### 2. 使用 LLaMA-Factory 微调

```bash
# 安装 LLaMA-Factory
git clone https://github.com/hiyouga/LLaMA-Factory.git
cd LLaMA-Factory
pip install -e ".[torch,metrics]"

# 启动 Web UI（推荐，可视化配置训练参数）
llamafactory-cli webui

# 或直接命令行训练（QLoRA，适合消费级 GPU）
llamafactory-cli train \
  --model_name_or_path Qwen/Qwen2.5-7B-Instruct \
  --method lora \
  --quantization_bit 4 \
  --dataset your_dataset \
  --template qwen \
  --output_dir ./output/qwen2.5-7b-customer-service \
  --num_train_epochs 3 \
  --per_device_train_batch_size 2 \
  --gradient_accumulation_steps 4 \
  --learning_rate 1e-4 \
  --fp16
```

#### 3. 导出并加载到 Ollama

```bash
# 合并 LoRA 权重并导出为 GGUF 格式
llamafactory-cli export \
  --model_name_or_path Qwen/Qwen2.5-7B-Instruct \
  --adapter_name_or_path ./output/qwen2.5-7b-customer-service \
  --template qwen \
  --export_dir ./output/merged \
  --export_quantization_bit 4

# 转换为 GGUF（需要 llama.cpp）
git clone https://github.com/ggerganov/llama.cpp && cd llama.cpp
python convert_hf_to_gguf.py ../output/merged --outfile qwen2.5-cs.gguf --outtype q4_k_m

# 创建 Ollama 模型
cat > Modelfile << EOF
FROM ./qwen2.5-cs.gguf
SYSTEM "你是专业的客服助手，负责解答售后、退款、物流等问题。"
EOF
ollama create qwen2.5-customer-service -f Modelfile

# 修改 .env 使用微调后的模型
# OLLAMA_MODEL=qwen2.5-customer-service
```

---

## 🧪 运行测试

```bash
# 在项目根目录
cd backend
pip install -r requirements.txt   # 已含 pytest 等

# 运行全部测试（需设置 PYTHONPATH 或从项目根执行）
pytest ../tests/ -v

# 仅运行单元测试
pytest ../tests/unit/ -v

# 仅运行集成测试
pytest ../tests/integration/ -v

# 生成覆盖率报告
pytest ../tests/ --cov=. --cov-report=html
```

---

## 📄 License

MIT

