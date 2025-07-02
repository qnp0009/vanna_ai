import sqlite3
import pandas as pd
import os

DB_PATH = "db/DIEM.db"
TABLE_NAME = "DIEM"

def debug_sqlite(db_path, table_name):
    if not os.path.exists(db_path):
        print(f"❌ Database file not found: {db_path}")
        return

    try:
        conn = sqlite3.connect(db_path)
        print(f"✅ Connected to database: {db_path}\n")

        # 1. Danh sách các bảng
        tables = pd.read_sql_query("SELECT name FROM sqlite_master WHERE type='table'", conn)
        print("📋 Tables in database:")
        print(tables)

        if table_name not in tables["name"].values:
            print(f"\n❌ Table '{table_name}' not found in database.")
            return
        
        # 2. Số lượng dòng
        count_df = pd.read_sql_query(f"SELECT COUNT(*) as total FROM {table_name}", conn)
        total_rows = count_df['total'].iloc[0]
        print(f"\n🔢 Total rows in '{table_name}': {total_rows}")

        # 3. In 3 dòng đầu
        if total_rows > 0:
            sample_df = pd.read_sql_query(f"SELECT * FROM {table_name} LIMIT 3", conn)
            print(f"\n👀 Sample rows from '{table_name}':")
            print(sample_df)
        else:
            print(f"\n⚠️ Table '{table_name}' is empty.")
        
    except Exception as e:
        print(f"❌ Error while accessing database: {e}")

if __name__ == "__main__":
    debug_sqlite(DB_PATH, TABLE_NAME)
