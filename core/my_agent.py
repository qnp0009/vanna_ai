from vanna.openai import OpenAI_Chat
from core.milvus_store import MilvusVectorDB

class MyVanna(MilvusVectorDB, OpenAI_Chat):
    def __init__(self, config):
        MilvusVectorDB.__init__(self, config=config)
        OpenAI_Chat.__init__(self, config=config)
