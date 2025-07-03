import os
import pandas as pd
import sqlite3

def save_excel_to_db(file_path, db_path, table_name="DATA"):
    df = pd.read_excel(file_path) if file_path.endswith('.xlsx') else pd.read_csv(file_path)

    conn = sqlite3.connect(db_path)
    df.to_sql(table_name, conn, if_exists='replace', index=False)
    conn.close()
    return df.columns.tolist()  # Trả về tên cột để train
