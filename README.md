# Vanna AI với Milvus Vector Database

Hệ thống AI tự động tạo SQL từ câu hỏi tiếng Anh, sử dụng vector database Milvus để lưu trữ và tìm kiếm kiến thức.

## Overview

- 🤖 **AI-Powered SQL**: Tự động tạo SQL từ ngôn ngữ tự nhiên
- 🧠 **Vector Knowledge Base**: Lưu trữ kiến thức với Milvus
- 📚 **Schema Learning**: Học và ghi nhớ cấu trúc database
- 🔍 **Semantic Search**: Tìm kiếm ngữ nghĩa trong knowledge base

## Quick Start

### 1. Cài đặt
```bash
pip install vanna pymilvus sentence-transformers pandas
```

### 2. Khởi động Milvus
```bash
# Tải và chạy Milvus
wget https://github.com/milvus-io/milvus/releases/download/v2.3.3/milvus-standalone-docker-compose.yml -O docker-compose.yml
docker-compose up -d
```

### 3. Cấu hình
Tạo file `.env`:
```
OPEN_API_KEY = "your-openai-api-key-here"
```

### 4. Chạy
```python

# Dạy schema
vanna.add_ddl("""
CREATE TABLE sales (
    id INT,
    product_name VARCHAR,
    amount FLOAT,
    sale_date DATE
)
""")

# Train vanna AI
python train.py

# Run app

python app.py
```



## Cấu trúc dự án

```
vanna_ai/
├── README.md           # Tài liệu dự án
├── config.py           # Cấu hình API key
├── milvus_store.py     # Vector database implementation
└── vanna_ai.py         # Script chính
```

## API chính

### MilvusVectorDB
- `add_ddl(ddl)`: Thêm DDL vào knowledge base
- `add_documentation(doc)`: Thêm tài liệu
- `add_question_sql(question, sql)`: Thêm cặp câu hỏi-SQL
- `get_related_ddl(question)`: Tìm DDL liên quan
- `get_similar_question_sql(question)`: Tìm câu hỏi tương tự 