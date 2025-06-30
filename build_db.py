import pandas as pd
import sqlite3
import os

# Đường dẫn tới file CSV và nơi tạo DB
CSV_PATH = "data/sales.csv"
DB_PATH = "db/sales.db"
TABLE_NAME = "sales"

# Tạo thư mục nếu chưa có
os.makedirs("db", exist_ok=True)

# Đọc CSV
df = pd.read_csv(CSV_PATH)

# Ghi vào DB SQLite
conn = sqlite3.connect(DB_PATH)
df.to_sql(TABLE_NAME, conn, if_exists="replace", index=False)
conn.close()

print(f"✅ Database '{DB_PATH}' đã được tạo từ '{CSV_PATH}' với bảng '{TABLE_NAME}'")
