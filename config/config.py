import os
from dotenv import load_dotenv
from core.my_agent import MyVanna
load_dotenv()
# Cấu hình Vanna
vn = MyVanna(config={
    "base_url": "https://vibe-agent-gateway.eternalai.org/v1",
    "api_key": os.getenv("LLM_API_KEY"),  
    "model": "gpt-4o-mini", 
    "uri": "./milvus_demo.db" 
})