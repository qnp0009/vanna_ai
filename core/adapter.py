from sqlalchemy import create_engine, inspect, text
import pandas as pd

class DBAdapter:
    def __init__(self, db_url: str):
        """
        db_url có thể là:
        - SQLite: sqlite:///db/mydb.sqlite3
        - MySQL: mysql+pymysql://user:pass@localhost:3306/mydb
        - PostgreSQL: postgresql+psycopg2://user:pass@localhost:5432/mydb
        """
        self.db_url = db_url
        self.engine = create_engine(db_url)

    def get_engine(self):
        return self.engine

    def get_connection(self):
        return self.engine.connect()

    def list_tables(self) -> list:
        """
        Trả về danh sách tên bảng trong cơ sở dữ liệu
        """
        inspector = inspect(self.engine)
        return inspector.get_table_names()

    def load_dataframe(self, table_name: str) -> pd.DataFrame:
        sql = f"SELECT * FROM {table_name}"
        return pd.read_sql(sql, self.engine)

    def run_sql(self, sql: str) -> pd.DataFrame:
        """
        Thực thi một câu truy vấn SQL bất kỳ và trả về DataFrame
        """
        with self.engine.connect() as conn:
            return pd.read_sql(sql, conn)

    def get_table_preview(self, table_name: str, limit=3) -> pd.DataFrame:
        """
        Trả về preview của bảng (mặc định: 3 dòng đầu)
        """
        sql = f"SELECT * FROM {table_name} LIMIT {limit}"
        return self.run_sql(sql)
