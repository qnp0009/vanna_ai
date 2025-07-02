import pandas as pd
import sqlite3
import os

# Đường dẫn tới file và nơi tạo DB
DB_PATH = "db/DIEM.db"
TABLE_NAME = "DIEM"
XLSX_PATH="data/DIEM.xlsx"
# Tạo thư mục nếu chưa có
os.makedirs("db", exist_ok=True)

# Đọc CSV
df = pd.read_excel(XLSX_PATH)

# Ghi vào DB SQLite
conn = sqlite3.connect(DB_PATH)
df.to_sql(TABLE_NAME, conn, if_exists="replace", index=False)
conn.close()

print(f"✅ Database '{DB_PATH}' đã được tạo từ '{XLSX_PATH}' với bảng '{TABLE_NAME}'")
print(df.columns)