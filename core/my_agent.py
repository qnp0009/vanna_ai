import os
import requests
import sqlite3
import pandas as pd
from core.base import VannaBase
from core.milvus_store import MilvusVectorDB
import json
import re

class MyVanna(VannaBase, MilvusVectorDB):
    def __init__(self, config):
        VannaBase.__init__(self)
        MilvusVectorDB.__init__(self, config=config)
        if config is None:
            raise ValueError("Config must include base_url, api_key, model, and milvus settings")

        # Check required LLM keys
        for key in ["base_url", "api_key", "model"]:
            if key not in config:
                raise ValueError(f"Missing '{key}' in config")

        # Store LLM config
        self.base_url = config["base_url"].rstrip("/")
        self.api_key = config["api_key"]
        self.model = config["model"]
        
        # Database connection
        self.db_path = None
        self.connection = None
        
        # Vanna compatibility attributes
        self.run_sql_is_set = True

    def connect_to_sqlite(self, db_path):
        """Connect to SQLite database"""
        self.db_path = db_path
        self.connection = sqlite3.connect(db_path)
        print(f"Connected to SQLite database: {db_path}")

    def run_sql(self, sql: str) -> pd.DataFrame:
        """Execute SQL query and return results as DataFrame"""
        if self.connection is None:
            raise ValueError("Not connected to database. Call connect_to_sqlite() first.")
        
        try:
            df = pd.read_sql_query(sql, self.connection)
            return df
        except Exception as e:
            print(f"Error executing SQL: {e}")
            return pd.DataFrame()
    def extract_sql_from_response(self, response: str) -> str:

        # 1. Loại bỏ phần <think>...</think>
        response = re.sub(r"<think>.*?</think>", "", response, flags=re.DOTALL)

        # 2. Nếu có ```sql ... ```, lấy phần trong đó
        code_blocks = re.findall(r"```sql(.*?)```", response, re.DOTALL)
        if code_blocks:
            return code_blocks[0].strip()

        # 3. Nếu có dòng nào bắt đầu bằng A: SELECT ..., tách bỏ A:
        for line in response.splitlines():
            line = line.strip()
            if line.upper().startswith("A: SELECT") or line.upper().startswith("A:WITH"):
                return line[2:].strip()  # Bỏ "A:" ở đầu dòng

        # 4. Nếu có dòng bắt đầu bằng SELECT hoặc WITH
        for line in response.splitlines():
            line = line.strip()
            if line.upper().startswith("SELECT") or line.upper().startswith("WITH"):
                return line

        # 5. Trả về toàn bộ nếu không biết cách cắt
        return response.strip()


    def generate_sql(self, question: str, **kwargs) -> str:
    # Format training data as context
        training_context = ""
        for item in self.training_data:
            if "question" in item and "sql" in item:
                training_context += f"Q: {item['question']}\nA: {item['sql']}\n\n"
            elif "ddl" in item:
                training_context += f"-- Schema definition:\n{item['ddl']}\n\n"
            elif "documentation" in item:
                training_context += f"-- Documentation:\n{item['documentation']}\n\n"

        prompt = [
            self.system_message("You are an assistant that generates SQL from natural language questions."),
            self.user_message(f"Use the following context to generate the SQL query:\n{training_context}\nNow answer this question:\n{question}")
        ]
        sql_raw = self.submit_prompt(prompt)

        # Remove non-SQL parts (e.g. <think>...</think>)
        sql_clean = self.extract_sql_from_response(sql_raw)
        sql = sql_clean
        return sql.replace("\\_", "_")

    def ask(self, question: str, **kwargs):
        """Process a question and return the result"""
        try:
            # Generate SQL from question
            sql = self.generate_sql(question)
            print(f"Generated SQL: {sql}")
            
            # Check if SQL is valid (not an error message)
            if sql.startswith("Error:") or sql.startswith("HTTP Error:") or sql.startswith("Connection Error:") or sql.startswith("Timeout Error:"):
                print("LLM server error - cannot generate valid SQL")
                return (None, None, question)
            
            # Execute SQL if database connection exists
            if self.connection is not None:
                try:
                    df = self.run_sql(sql)
                    return (sql, df, question)
                except Exception as e:
                    print(f"Error executing SQL: {e}")
                    return (sql, None, question)
            else:
                return (sql, None, question)
                
        except Exception as e:
            print(f"Error in ask method: {e}")
            return (None, None, question)

    # Override training methods to save to both memory and Milvus
    def add_training_pair(self, question, sql):
        """Save question-SQL pair to both memory and Milvus"""
        # Save to memory (from VannaBase)
        super().add_training_pair(question, sql)
        # Save to Milvus
        self.add_question_sql(question, sql)

    def add_ddl(self, ddl):
        """Save DDL to both memory and Milvus"""
        # Save to memory (from VannaBase)
        super().add_ddl(ddl)
        # Save to Milvus
        MilvusVectorDB.add_ddl(self, ddl)

    def add_documentation(self, doc):
        """Save documentation to both memory and Milvus"""
        # Save to memory (from VannaBase)
        super().add_documentation(doc)
        # Save to Milvus
        MilvusVectorDB.add_documentation(self, doc)

    # Message formatting
    def system_message(self, message: str) -> dict:
        return {"role": "system", "content": message}

    def user_message(self, message: str) -> dict:
        return {"role": "user", "content": message}

    def assistant_message(self, message: str) -> dict:
        return {"role": "assistant", "content": message}

    # Send prompt to LLM
    def submit_prompt(self, prompt, **kwargs) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": prompt,
            "temperature": 0.7,
        }

        try:
            response = requests.post(
                url=f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return result["choices"][0]["message"]["content"]
            else:
                print(f"Error Response Text: {response.text}")
                return f"Error: Server returned {response.status_code}"
                
        except requests.exceptions.HTTPError as e:
            print(f"\n=== HTTP Error ===")
            print(f"Error: {e}")
            print(f"Response status: {response.status_code if 'response' in locals() else 'Unknown'}")
            print(f"Response text: {response.text if 'response' in locals() else 'Unknown'}")
            return f"HTTP Error: {e}"
            
        except requests.exceptions.ConnectionError as e:
            print(f"\n=== Connection Error ===")
            print(f"Error: {e}")
            return "Connection Error: Cannot connect to LLM server"
            
        except requests.exceptions.Timeout as e:
            print(f"\n=== Timeout Error ===")
            print(f"Error: {e}")
            return "Timeout Error: Request timed out"
            
        except Exception as e:
            print(f"\n=== Unexpected Error ===")
            print(f"Error type: {type(e).__name__}")
            print(f"Error: {e}")
            return f"Unexpected Error: {str(e)}"

    def save_training_data(self, filename="training.json"):
        folder = "training_data"
        if not os.path.exists(folder):
            os.makedirs(folder)
        filepath = os.path.join(folder, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.training_data, f, ensure_ascii=False, indent=2)
        print(f"Training data saved to {filepath}")

    def load_training_data(self, filename="training.json"):
        folder = "training_data"
        filepath = os.path.join(folder, filename)
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                self.training_data = json.load(f)
            print(f"Training data loaded from {filepath}")
        else:
            self.training_data = []
            print(f"No training data found at {filepath}, starting fresh.")

        
