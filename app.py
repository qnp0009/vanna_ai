from my_agent import MyVanna, vn  # Lớp kết hợp OpenAI + Milvus
import pandas as pd
from vanna.flask import VannaFlaskApp

vn.connect_to_sqlite("db/sales.db")

#Lauch the app
app = VannaFlaskApp(vn, allow_llm_to_see_data=True)
app.run()
