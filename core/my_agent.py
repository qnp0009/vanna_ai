import os
import requests
import pandas as pd
from core.adapter import DBAdapter
from vanna.base import VannaBase
from core.milvus_store import MilvusVectorDB
import json
import re

class MyVanna(MilvusVectorDB, VannaBase):
    def __init__(self, config, db_adapter: DBAdapter | None = None):
        self.training_data = [] 
        MilvusVectorDB.__init__(self, config=config)
        VannaBase.__init__(self)
        if config is None:
            raise ValueError("Config must include base_url, api_key, model, and milvus settings")

        for key in ["base_url", "api_key", "model"]:
            if key not in config:
                raise ValueError(f"Missing '{key}' in config")

        self.base_url = config["base_url"].rstrip("/")
        self.api_key = config["api_key"]
        self.model = config["model"]
        self.db_adapter = db_adapter

    def run_sql(self, sql: str) -> pd.DataFrame:
        """Open a new connection per-thread to execute SQL safely"""
        if self.db_adapter is None:
            raise ValueError("Database path not set. Call connect_to_sqlite() first.")

        try:
            # Use the db_adapter's run_sql method instead of direct sqlite connection
            return self.db_adapter.run_sql(sql)
        except Exception as e:
            print(f"Error executing SQL: {e}")
            return pd.DataFrame()

    def extract_sql_from_response(self, response: str) -> str:
        response = re.sub(r"<think>.*?</think>", "", response, flags=re.DOTALL)
        code_blocks = re.findall(r"```sql(.*?)```", response, re.DOTALL)
        if code_blocks:
            return code_blocks[0].strip()
        for line in response.splitlines():
            line = line.strip()
            if line.upper().startswith("A: SELECT") or line.upper().startswith("A:WITH"):
                return line[2:].strip()
        for line in response.splitlines():
            line = line.strip()
            if line.upper().startswith("SELECT") or line.upper().startswith("WITH"):
                return line
        return response.strip()

    def extract_table_schema(self, table_name: str) -> str:
        if not self.db_adapter or not table_name:
            return ""
        try:
            df = self.db_adapter.run_sql(f"PRAGMA table_info({table_name})")
            if df.empty:
                return f"Table {table_name} not found."
            schema = f"Table: {table_name}\nColumns:\n"
            for _, row in df.iterrows():
                schema += f"  - {row['name']}: {row['type']}\n"
            return schema
        except Exception as e:
            print(f"Error extracting schema: {e}")
            return ""

    def extract_all_tables_schema(self) -> str:
        """Extract schema for all tables in the database"""
        if not self.db_adapter:
            return ""
        try:
            # Get all table names
            df_tables = self.db_adapter.run_sql("SELECT name FROM sqlite_master WHERE type='table'")
            if df_tables.empty:
                return "No tables found in database."
            
            all_schema = "Database Schema:\n"
            for _, table_row in df_tables.iterrows():
                table_name = str(table_row['name'])
                table_schema = self.extract_table_schema(table_name)
                if table_schema:
                    all_schema += f"\n{table_schema}\n"
            
            return all_schema
        except Exception as e:
            print(f"Error extracting all tables schema: {e}")
            return ""

    def generate_sql(self, question: str, table_name: str | None = None, **kwargs) -> str:
        # Get schema for all tables instead of just one table
        print(f"🧾 Using schema for all tables in database")
        schema = self.extract_all_tables_schema()
        print("📄 Schema used in prompt:")
        print(schema)

        training_context = f"-- Database schema:\n{schema}\n\n"
        for item in self.training_data:
            if "question" in item and "sql" in item:
                training_context += f"Q: {item['question']}\nA: {item['sql']}\n\n"
            elif "ddl" in item:
                training_context += f"-- Schema definition:\n{item['ddl']}\n\n"
            elif "documentation" in item:
                training_context += f"-- Documentation:\n{item['documentation']}\n\n"

        prompt = [
            self.system_message("You are an assistant that generates SQL from natural language questions. You can use any table in the database schema provided."),
            self.user_message(f"Use the following context to generate the SQL query:\n{training_context}\nNow answer this question:\n{question}")
        ]
        sql_raw = self.submit_prompt(prompt)
        sql_clean = self.extract_sql_from_response(sql_raw)
        return sql_clean.replace("\\_", "_")


    def ask(self, question: str, **kwargs):
        try:
            table_name = kwargs.get("table_name")
            if table_name:
                question = f"The data is stored in a SQL table named `{table_name}`.\n{question}"
            sql = self.generate_sql(question, table_name=table_name)
            print(f"Generated SQL: {sql}")
            if any(sql.startswith(prefix) for prefix in ["Error:", "HTTP Error:", "Connection Error:", "Timeout Error:"]):
                print("LLM server error - cannot generate valid SQL")
                return (None, None, question)
            if self.db_adapter is not None:
                try:
                    df = self.db_adapter.run_sql(sql)
                    return (sql, df, question)
                except Exception as e:
                    print(f"Error executing SQL: {e}")
                    return (sql, None, question)
            else:
                return (sql, None, question)
        except Exception as e:
            print(f"Error in ask method: {e}")
            return (None, None, question)


    def system_message(self, message: str) -> dict:
        return {"role": "system", "content": message}

    def user_message(self, message: str) -> dict:
        return {"role": "user", "content": message}

    def assistant_message(self, message: str) -> dict:
        return {"role": "assistant", "content": message}

    def submit_prompt(self, prompt, **kwargs) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": prompt,
            "temperature": 0.1,
        }

        try:
            response = requests.post(
                url=f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=100
            )
            if response.status_code == 200:
                result = response.json()
                return result["choices"][0]["message"]["content"]
            else:
                print(f"Error Response Text: {response.text}")
                return f"Error: Server returned {response.status_code}"
        except requests.exceptions.HTTPError as e:
            print(f"\n=== HTTP Error ===\nError: {e}")
            return f"HTTP Error: {e}"
        except requests.exceptions.ConnectionError as e:
            print(f"\n=== Connection Error ===\nError: {e}")
            return "Connection Error: Cannot connect to LLM server"
        except requests.exceptions.Timeout as e:
            print(f"\n=== Timeout Error ===\nError: {e}")
            return "Timeout Error: Request timed out"
        except Exception as e:
            print(f"\n=== Unexpected Error ===\nError type: {type(e).__name__}\nError: {e}")
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
