import requests
import sqlite3
import pandas as pd
import re

def query_data(sql, db_path):
    """Chạy câu lệnh SQL trên SQLite DB và trả về CSV string."""
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query(sql, conn)
    conn.close()
    return df.to_csv(index=False)


def remove_think_blocks(text):
    """Loại bỏ phần <think>...</think> nếu có từ phản hồi LLM."""
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()


def generate_report(question, sql, data_csv, llm_api_url):
    content = f"""
Câu hỏi của người dùng: {question}

SQL được sinh ra:
{sql}

Kết quả dữ liệu (chỉ xem trước 1000 ký tự):
{data_csv[:1000]}

👉 Viết một báo cáo ngắn gọn, rõ ràng, dựa trên câu hỏi và dữ liệu trên.
"""

    headers = {
        "Content-Type": "application/json",
        # "Authorization": f"Bearer {os.getenv('LLM_API_KEY')}"  # Bật nếu cần
    }

    payload = {
        "model": "gpt-4o-mini",  # hoặc model khác tùy backend
        "messages": [
            {"role": "system", "content": "Bạn là một nhà phân tích dữ liệu giỏi."},
            {"role": "user", "content": content}
        ],
        "temperature": 0.1
    }

    try:
        response = requests.post(
            f"{llm_api_url}/chat/completions",
            headers=headers,
            json=payload,
            timeout=200
        )
        result = response.json()

        if "choices" in result and result["choices"]:
            raw_text = result["choices"][0]["message"]["content"]
            clean_text = remove_think_blocks(raw_text)
            return clean_text

        elif "error" in result:
            raise RuntimeError(f"LLM API Error: {result['error']}")

        else:
            raise RuntimeError(f"Invalid LLM response: {result}")

    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"❌ Connection error: {e}")
    except Exception as e:
        raise RuntimeError(f"❌ Unexpected error: {e}")
