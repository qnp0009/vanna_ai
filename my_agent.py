from vanna.openai import OpenAI_Chat
from milvus_store import MilvusVectorDB
import os
from dotenv import load_dotenv

load_dotenv()

class MyVanna(MilvusVectorDB, OpenAI_Chat):
    def __init__(self, config):
        MilvusVectorDB.__init__(self, config=config)
        OpenAI_Chat.__init__(self, config=config)

# Cấu hình Vanna
vn = MyVanna(config={
    "api_key": os.getenv("OPENAI_API_KEY"),  
    "model": "gpt-4o-mini", 
    "db_connection": "sqlite:///db/sales.db"
})