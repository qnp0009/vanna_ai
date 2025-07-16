# syntax=docker/dockerfile:1
FROM python:3.10-slim

# Cài các thư viện hệ thống cần thiết cho các driver database phổ biến
RUN apt-get update && apt-get install -y \
    build-essential \
    default-libmysqlclient-dev \
    libpq-dev \
    unixodbc-dev \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Tùy chọn: Cài thêm driver cho Oracle, ClickHouse, DuckDB, Snowflake nếu cần
# RUN apt-get update && apt-get install -y libaio1

# Tạo thư mục làm việc
WORKDIR /app

# Copy toàn bộ mã nguồn vào image
COPY . /app

# Cài Python dependencies
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Cài thêm các dialect phổ biến cho SQLAlchemy
RUN pip install --no-cache-dir \
    psycopg2-binary \
    pymysql \
    pyodbc \
    cx_Oracle \
    clickhouse-sqlalchemy \
    duckdb-engine \
    snowflake-sqlalchemy \
    pyhive \
    pybigquery

# Expose port for Streamlit
EXPOSE 8501

# Lệnh mặc định để chạy app
CMD ["streamlit", "run", "app_streamlit.py", "--server.port=8801", "--server.address=0.0.0.0"] 