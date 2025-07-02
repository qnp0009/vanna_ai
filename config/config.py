import os
from dotenv import load_dotenv
from core.my_agent import MyVanna
load_dotenv()
# Cấu hình Vanna
vn = MyVanna(config={
    "api_key": os.getenv("OPENAI_API_KEY"),  
    "model": "gpt-4o-mini", 
    "db_connection": "sqlite:///db/sales.db"
})