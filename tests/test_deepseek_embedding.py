"""
DeepSeek Embedding 接口测试

用于确认正确的 base_url、模型名和请求格式。

运行方式（在项目根目录 d:\\my_project\\aics-tt）：
  1）本机：会从项目根 .env 加载 DEEPSEEK_API_KEY（若有）
     python tests/test_deepseek_embedding.py
    或先设置： set DEEPSEEK_API_KEY=你的key

  2）Docker 内（使用容器环境变量）：
     docker compose exec backend python tests/test_deepseek_embedding.py
     （需确保镜像内包含 tests 或挂载进容器）
"""
import os

# 从项目根 .env 加载（可选）
_env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
if os.path.isfile(_env_path):
    with open(_env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                k, v = k.strip(), v.strip().strip('"').strip("'")
                if k == "DEEPSEEK_API_KEY" and v:
                    os.environ.setdefault("DEEPSEEK_API_KEY", v)
                    break

API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
if not API_KEY:
    print("请设置环境变量 DEEPSEEK_API_KEY，或在脚本中填写 API_KEY")
    print("示例: set DEEPSEEK_API_KEY=sk-xxx")
    exit(1)
TEST_TEXT = "你好，这是一段测试文本。"


def test_raw_http():
    """方式 1：直接用 HTTP 请求，明确控制 URL（使用 httpx）"""
    try:
        import httpx
    except ImportError:
        print("跳过 raw_http：未安装 httpx")
        return None

    endpoints = [
        ("https://api.deepseek.com/v1/embeddings", "deepseek-embedding"),
        ("https://api.deepseek.com/v1/embeddings", "deepseek-embedding-v2"),
        ("https://api.deepseek.com/embeddings", "deepseek-embedding"),
        ("https://api.deepseek.com/embeddings", "deepseek-embedding-v2"),
    ]
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }
    for url, model in endpoints:
        try:
            r = httpx.post(
                url,
                json={"input": TEST_TEXT, "model": model},
                headers=headers,
                timeout=30,
            )
            if r.status_code == 200:
                data = r.json()
                emb = data.get("data", [{}])[0].get("embedding", [])
                print(f"[OK] {url} model={model} -> 向量维度 {len(emb)}")
                return (url, model)
            else:
                print(f"[{r.status_code}] {url} model={model} -> {r.text[:200]}")
        except Exception as e:
            print(f"[ERR] {url} model={model} -> {e}")
    return None


def test_langchain(base_url: str, model: str):
    """方式 2：用 LangChain OpenAIEmbeddings（与项目一致）"""
    try:
        from langchain_openai import OpenAIEmbeddings
    except ImportError:
        print("跳过 langchain：未安装 langchain-openai")
        return False
    try:
        emb = OpenAIEmbeddings(
            api_key=API_KEY,
            base_url=base_url.rstrip("/"),
            model=model,
        )
        vec = emb.embed_query(TEST_TEXT)
        print(f"[OK] LangChain base_url={base_url} model={model} -> 维度 {len(vec)}")
        return True
    except Exception as e:
        print(f"[ERR] LangChain base_url={base_url} model={model} -> {e}")
        return False


if __name__ == "__main__":
    print("=== DeepSeek Embedding 测试 ===\n")
    print("1. 直接 HTTP 请求（尝试不同 endpoint + 模型名）")
    result = test_raw_http()
    print()
    print("2. LangChain OpenAIEmbeddings")
    if result:
        base, model = result
        test_langchain(base, model)
    else:
        # 常见组合各试一次
        for base in ["https://api.deepseek.com/v1", "https://api.deepseek.com"]:
            for model in ["deepseek-embedding-v2", "deepseek-embedding"]:
                if test_langchain(base, model):
                    break
            else:
                continue
            break
    print("\n=== 测试结束 ===")
