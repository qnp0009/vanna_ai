import requests
import sqlite3
import pandas as pd

def query_data(sql, db_path):
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query(sql, conn)
    conn.close()
    return df.to_csv(index=False)

def generate_report(question, sql, data_csv, llm_api_url):
    content = f"""
Câu hỏi của người dùng: {question}
Dữ liệu lấy được từ SQL:
{sql}

Dữ liệu:
{data_csv[:1000]}  # Giới hạn để tránh overload

Viết 1 báo cáo phân tích dựa trên câu hỏi, dữ liệu SQL trên.
"""
    res = requests.post(llm_api_url, json={
        "messages": [{"role": "user", "content": content}]
    })
    return res.json()["choices"][0]["message"]["content"]
