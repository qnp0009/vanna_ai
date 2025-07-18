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

        system_msg = """You are an expert SQL assistant that generates SQL from natural language questions. 

CRITICAL RULES:
1. ALWAYS use table names in your SQL queries
2. NEVER write column names without table prefixes when multiple tables are involved
3. Use proper table aliases (e.g., o for orders, p for products)
4. Always specify the table name before the column name: table_name.column_name
5. Use JOINs with explicit table names and conditions
6. When aggregating data, always specify which table the data comes from

Examples of CORRECT usage:
- SELECT orders.customer_name FROM orders WHERE orders.status = 'active'
- SELECT o.total_amount, p.product_name FROM orders o JOIN products p ON o.product_id = p.id
- SELECT COUNT(*) as order_count FROM orders WHERE orders.date_created >= '2024-01-01'

Examples of INCORRECT usage:
- SELECT customer_name FROM orders (missing table prefix)
- SELECT total_amount, product_name FROM orders JOIN products (missing table aliases)
- SELECT COUNT(*) FROM orders WHERE date_created >= '2024-01-01' (missing table prefix)

Use the database schema provided to understand table structures and relationships."""

        prompt = [
            self.system_message(system_msg),
            self.user_message(f"Use the following context to generate the SQL query:\n{training_context}\nNow answer this question:\n{question}\n\nPlease provide:\n1. The SQL query (in a code block)\n2. A brief explanation of your reasoning and how you mapped the question to the SQL (in plain text, after the code block)")
        ]
        response = self.submit_prompt(prompt)
        # Extract SQL and reasoning
        import re
        sql_blocks = re.findall(r"```sql(.*?)```", response, re.DOTALL)
        sql_clean = sql_blocks[0].strip() if sql_blocks else response.strip()
        reasoning = re.sub(r"```sql.*?```", "", response, flags=re.DOTALL).strip()
        self.last_reasoning = reasoning
        return sql_clean

    def get_last_reasoning(self):
        return getattr(self, 'last_reasoning', None)


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

    def train(self, ddl: str | None = None, documentation: str | None = None, question: str | None = None, sql: str | None = None):
        """Add training data to the knowledge base"""
        if ddl:
            self.training_data.append({"ddl": ddl})
            print(f"✅ Added DDL training data")
        elif documentation:
            self.training_data.append({"documentation": documentation})
            print(f"✅ Added documentation training data")
        elif question and sql:
            self.training_data.append({"question": question, "sql": sql})
            print(f"✅ Added Q&A training data: {question[:50]}...")
        else:
            print("❌ Invalid training data. Must provide ddl, documentation, or both question and sql.")
