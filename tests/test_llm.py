from langchain_openai import ChatOpenAI
# DeepSeek 官方文档: POST https://api.deepseek.com/chat/completions（无 /v1）
# OpenAI 客户端会拼接 /chat/completions，故 base 不要带 /v1
# base = (settings.deepseek_api_base or "https://api.deepseek.com").rstrip("/")
base = "https://api.deepseek.com"
# logger.info(f"使用 DeepSeek 模型: {settings.deepseek_chat_model} base_url={base}")
llm = ChatOpenAI(
        api_key="sk-56cf967e46bd40a3bdc5d67fce67384f",
        base_url=base,
        model="deepseek-chat",
        max_tokens=2048,
        temperature=0.7,
        streaming=True,
        )

print(llm.invoke("请介绍一下你自己。"))