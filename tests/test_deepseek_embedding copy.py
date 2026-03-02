import requests
# from langchain_openai import OpenAIEmbeddings
from langchain_community.embeddings import DashScopeEmbeddings
# from langchain_community.llms import Tongyi

# DEEPSEEK_API_URL = "https://api.deepseek.com/v1/embeddings"
API_KEY = ""



# llm = Tongyi(
#     api_key=API_KEY, 
#     model="qwen-max",
#     max_tokens=2048,
#     temperature=0.7,
#     streaming=True,
# )

embeddings = DashScopeEmbeddings(
    dashscope_api_key=API_KEY,
    model="text-embedding-v3"
)

# 使用示例
text = "DeepSeek的Embedding模型怎么用？"
embedding_vector = embeddings.embed_query(text)
print(f"生成的向量维度是：{len(embedding_vector)}")  # 应该输出1024

# print(llm.invoke(text))