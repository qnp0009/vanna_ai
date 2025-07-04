import os
import requests
import sqlite3
import pandas as pd
from vanna.base import VannaBase
from core.milvus_store import MilvusVectorDB
from core.db_adapter import DatabaseAdapter
import json
import re
from urllib.parse import urlparse

class MyVanna(MilvusVectorDB, VannaBase):
    def __init__(self, config):
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

        # Initialize database adapter
        self.db_adapter = DatabaseAdapter()
        self.connection_string = None
        self.db_name = None
        self.run_sql_is_set = True
        self.training_data = []

    def get_db_name(self, connection_string):
        if connection_string.startswith("sqlite:///"):
            file_path = connection_string.replace("sqlite:///", "")
            base = os.path.basename(file_path)
            return os.path.splitext(base)[0]
        elif connection_string.startswith("postgresql://"):
            parsed = urlparse(connection_string)
            return parsed.path[1:] if parsed.path.startswith("/") else parsed.path
        else:
            return "default"

    def connect_to_database(self, connection_string: str):
        """
        Connect to database using connection string.
        
        Args:
            connection_string: 
                - SQLite: "sqlite:///path/to/file.db" or "sqlite:///C:/path/to/file.db"
                - PostgreSQL: "postgresql://user:password@host:port/database"
        """
        self.connection_string = connection_string
        self.db_adapter.connect(connection_string)
        self.db_name = self.get_db_name(connection_string)
        self.load_training_data()  # Always load per-DB training data
        self.schema_context = self.extract_schema_context()  # Extract schema for LLM
        print(f"✅ Connected to database: {connection_string}")

    def connect_to_sqlite(self, db_path):
        """Legacy method for backward compatibility"""
        connection_string = f"sqlite:///{db_path}"
        self.connect_to_database(connection_string)

    def run_sql(self, sql: str) -> pd.DataFrame:
        """Execute SQL query using the database adapter"""
        if not self.db_adapter.connection:
            raise ValueError("Database not connected. Call connect_to_database() first.")

        return self.db_adapter.execute_query(sql)

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

    def extract_schema_context(self):
        """
        Extract schema (table and columns) from the connected DB and return as a string for LLM context.
        """
        if not self.db_adapter.connection:
            return ""
        try:
            tables = self.db_adapter.get_tables()
            schema_lines = []
            for table in tables:
                df_schema = self.db_adapter.get_table_schema(table)
                if not df_schema.empty:
                    if self.db_adapter.db_type == "sqlite":
                        # SQLite PRAGMA table_info
                        columns = [f"{row['name']} {row['type']}" for _, row in df_schema.iterrows()]
                    else:
                        # PostgreSQL info
                        columns = [f"{row['column_name']} {row['data_type']}" for _, row in df_schema.iterrows()]
                    schema_lines.append(f"Table {table}:\n  " + ", ".join(columns))
            return "\n".join(schema_lines)
        except Exception as e:
            print(f"Error extracting schema context: {e}")
            return ""

    def generate_sql(self, question: str, **kwargs) -> str:
        # Always use schema context for LLM
        schema_context = self.schema_context if hasattr(self, 'schema_context') else ""
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
            self.user_message(f"Database schema:\n{schema_context}\n\nUse the following context to generate the SQL query:\n{training_context}\nNow answer this question:\n{question}")
        ]
        sql_raw = self.submit_prompt(prompt)
        sql_clean = self.extract_sql_from_response(sql_raw)
        return sql_clean.replace("\\_", "_")

    def ask(self, question: str, **kwargs):
        try:
            sql = self.generate_sql(question)
            print(f"Generated SQL: {sql}")
            if sql.startswith("Error:") or sql.startswith("HTTP Error:") or sql.startswith("Connection Error:") or sql.startswith("Timeout Error:"):
                print("LLM server error - cannot generate valid SQL")
                return (None, None, question)
            if self.db_adapter.connection is not None:
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
                timeout=30
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

    def save_training_data(self, filename=None):
        folder = "training_data"
        if not os.path.exists(folder):
            os.makedirs(folder)
        if filename is None:
            if self.db_name:
                filename = f"{self.db_name}.json"
            else:
                filename = "default.json"
        filepath = os.path.join(folder, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.training_data, f, ensure_ascii=False, indent=2)
        print(f"Training data saved to {filepath}")

    def load_training_data(self, filename=None):
        folder = "training_data"
        if filename is None:
            if self.db_name:
                filename = f"{self.db_name}.json"
            else:
                filename = "default.json"
        filepath = os.path.join(folder, filename)
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                self.training_data = json.load(f)
            print(f"Training data loaded from {filepath}")
        else:
            self.training_data = []
            print(f"No training data found at {filepath}, starting fresh.")
