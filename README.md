# Vanna AI - From Question to Report

An AI-powered application that generates SQL from natural language questions and creates comprehensive reports and slides from your data.

## Overview

- 🤖 **AI-Powered SQL**: Generate SQL from natural language questions
- 📊 **Interactive Reports**: Create detailed reports from query results
- 📈 **Presentation Slides**: Generate slides with charts and insights
- 🔄 **Multiple Queries**: Combine multiple queries into comprehensive analysis
- 🎯 **Smart Training**: Learn from your database schema and examples

## Quick Start

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure environment
Create a `.env` file:
```
LLM_API_KEY=your-api-key-here
```

### 3. Prepare your database
Place your SQLite database file in the `db/` folder (e.g., `db/ecommerce.db`)

### 4. Train the AI (optional)
```bash
python core/train.py
```

### 5. Run the application
```bash
streamlit run app_streamlit.py
```

## Features

### 💬 Q&A Tab
- Ask natural language questions about your data
- View generated SQL and results
- Add optional requests for report customization
- Generate slides from individual queries

### 📊 Comprehensive Report Tab
- Combine multiple queries into one analysis
- Generate comprehensive reports from all collected data
- Create slides from comprehensive reports
- Add custom requirements for analysis

### 📖 User Guide Tab
- Learn how to use the application effectively
- View example questions and tips

## Project Structure

```
vanna_ai/
├── app_streamlit.py    # Main Streamlit application
├── core/
│   ├── my_agent.py     # AI agent implementation
│   ├── milvus_store.py # Vector storage for knowledge
│   ├── train.py        # Training script
│   └── adapter.py      # Database adapter
├── app/
│   ├── report_writer.py # Report generation
│   ├── slides_planner.py # Slide planning
│   ├── reveal_generator.py # Slide generation
│   └── chart_generator.py # Chart creation
├── config/
│   └── config.py       # Configuration
├── db/                 # Database files
└── training_data/      # Training data storage
```

## How It Works

1. **Connect to Database**: Upload or select your SQLite database
2. **Ask Questions**: Use natural language to query your data
3. **Review Results**: See SQL, data, and generated reports
4. **Create Slides**: Generate presentation slides with charts
5. **Comprehensive Analysis**: Combine multiple queries for deeper insights

## Requirements

- Python 3.8+
- SQLite database
- LLM API key (OpenAI compatible)
- Internet connection for AI processing 