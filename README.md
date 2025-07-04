# Vanna AI with Milvus Vector Database

This project uses AI to automatically generate SQL from English questions, leveraging a Milvus vector database to store and search knowledge. It also supports automatic report generation from your data and questions.

## Overview

- 🤖 **AI-Powered SQL**: Automatically generate SQL from natural language
- 🧠 **Vector Knowledge Base**: Store knowledge with Milvus
- 📚 **Schema Learning**: Learn and remember database structure
- 🔍 **Semantic Search**: Semantic search in the knowledge base
- 📝 **Automated Report Writing**: Generate natural language reports from your data and questions

## Quick Start

### 1. Install dependencies
```bash
pip install vanna pymilvus sentence-transformers pandas streamlit
```

### 2. Start Milvus
```bash
# Download and run Milvus
# download through https://milvus.io/docs and follow the guide
```

### 3. Configure environment
Create a `.env` file:
```
LLM_API_KEY=your-openai-api-key-here
```

### 4. Train the AI
Edit and run `core/train.py` to load your schema and sample Q&A:
```python
from config.config import vn
vn.connect_to_sqlite("db/DIEM.db")
vn.load_training_data()
# Add DDL, documentation, and Q&A pairs as shown in train.py
# ...
vn.save_training_data()
# Make sure load training data before excute the app
# use python -m core.train 
```

### 5. Run the app (example CLI)
```python
from config.config import vn
vn.connect_to_sqlite("db/DIEM.db")
vn.load_training_data()
while True:
    question = input("Enter your question: ")
    if question.lower() in ("exit", "quit"): break
    sql, df, _ = vn.ask(question)
    print("SQL:", sql)
    print(df.head(10) if df is not None else "No data")
# Run app
python -m streamlit run app_streamlit.py
```

### 6. Generate Reports Automatically
You can use the report generation feature to get natural language summaries and insights from your data:

- **API usage:**
  - Use the `/report/` endpoint in your FastAPI app (see `app/app.py`):
    ```python
    @app.post("/report/")
    async def report(question: str = Form(...), db_file: str = Form(...)):
        db_path = f"db/{db_file}.db"
        sql = agent.generate_sql_from_question(question)
        data_csv = query_data(sql, db_path)
        report = generate_report(question, sql, data_csv, llm_api_url="http://localhost:8001")
        return {"sql": sql, "report": report}
    ```
- **CLI usage:**
  - After generating SQL and data, call your report writer:
    ```python
    from app.report_writer import generate_report
    report = generate_report(question, sql, df, llm_api_url="http://localhost:8001")
    print(report)
    ```
- **Streamlit app:**
  - Use the Streamlit interface to upload data, ask questions, and get both SQL and natural language reports.

## Project Structure

```
vanna_ai/
├── README.md           # Project documentation
├── config/             # Configuration and MyVanna instance
│   └── config.py
├── core/
│   ├── my_agent.py     # MyVanna class
│   ├── milvus_store.py # Milvus vector DB implementation
│   └── train.py        # Training script
├── app/
│   ├── report_writer.py# Report generation logic
│   └── uploader.py     # Excel/DB uploader
├── db/                 # SQLite databases
├── data/               # Data files
├── app_streamlit.py# Streamlit UI
```

## Main API

### MyVanna
- `connect_to_sqlite(db_path)`: Connect to SQLite database
- `run_sql(sql)`: Run SQL and return DataFrame
- `train(...)`: Add DDL, documentation, or Q&A pairs
- `ask(question)`: Generate SQL and get results
- `save_training_data(filename)`: Save training data to file
- `load_training_data(filename)`: Load training data from file

### MilvusVectorDB
- `add_ddl(ddl)`: Add DDL to knowledge base
- `add_documentation(doc)`: Add documentation
- `add_question_sql(question, sql)`: Add Q&A pair
- `get_related_ddl(question)`: Find related DDL
- `get_similar_question_sql(question)`: Find similar Q&A

### Report Generation
- `generate_report(question, sql, data, llm_api_url)`: Generate a natural language report from your question, SQL, and data using an LLM API.
- Use via API, CLI, or Streamlit as shown above.

## Notes
- Always load training data before asking questions for best results.
- The LLM only knows your schema if you provide it in the training context or prompt.
- You can extend or adapt the CLI/app for your use case.
- The report generation feature lets you get not just SQL, but also human-readable summaries and insights from your data. 