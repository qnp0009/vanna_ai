import os
import streamlit as st
import json
import pandas as pd
from datetime import datetime
from app.report_writer import generate_report
from app.uploader import save_excel_to_db
from config.config import vn

# --- Load training data ---
vn.load_training_data()

# --- Page setup ---
st.set_page_config(page_title="Vanna AI Report Assistant", layout="wide")
st.title("🧠 Vanna AI - From Question to Report")
st.markdown("Upload an Excel file, select a database, ask questions, and let AI write a report for you.")

# --- Sidebar: Upload Excel ---
st.sidebar.header("📤 Upload Excel File")
uploaded_file = st.sidebar.file_uploader("Choose an Excel file", type=["xlsx", "xls"])

if uploaded_file:
    file_path = f"data/{uploaded_file.name}"
    db_path = f"db/{uploaded_file.name}.db"
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    try:
        table_name = save_excel_to_db(file_path, db_path)
        st.sidebar.success(f"✅ Converted to {uploaded_file.name}.db with table `{table_name}`")
        st.session_state["table_name"] = table_name
    except Exception as e:
        st.sidebar.error(f"❌ Failed to convert file: {e}")

# --- Sidebar: Database Connection ---
st.sidebar.header("🗄️ Database Connection")

# Track connection state in session
if "db_connected" not in st.session_state:
    st.session_state["db_connected"] = False
if "db_connection_string" not in st.session_state:
    st.session_state["db_connection_string"] = None
if "db_name" not in st.session_state:
    st.session_state["db_name"] = None

def set_connected(connection_string, db_name):
    st.session_state["db_connected"] = True
    st.session_state["db_connection_string"] = connection_string
    st.session_state["db_name"] = db_name

def disconnect_db():
    st.session_state["db_connected"] = False
    st.session_state["db_connection_string"] = None
    st.session_state["db_name"] = None
    st.session_state.clear()

if not st.session_state["db_connected"]:
    # Connection type selection
    connection_type = st.sidebar.selectbox(
        "Select Connection Type",
        ["SQLite File", "PostgreSQL URL", "Existing SQLite Files"]
    )

    if connection_type == "SQLite File":
        # Manual SQLite file path input
        sqlite_path = st.sidebar.text_input(
            "SQLite Database Path",
            placeholder="e.g., db/my_database.db or C:/path/to/database.db"
        )
        
        if st.sidebar.button("🔗 Connect to SQLite") and sqlite_path:
            try:
                connection_string = f"sqlite:///{sqlite_path}"
                vn.connect_to_database(connection_string)
                tables = vn.db_adapter.get_tables()
                db_name = getattr(vn, 'db_name', None) or sqlite_path
                set_connected(connection_string, db_name)
                st.sidebar.success(f"✅ Connected to SQLite database: {db_name}")
                st.sidebar.write("📄 Tables:", tables)
            except Exception as e:
                st.sidebar.error(f"❌ Failed to connect: {e}")

    elif connection_type == "PostgreSQL URL":
        # PostgreSQL connection string input
        pg_url = st.sidebar.text_input(
            "PostgreSQL Connection URL",
            placeholder="postgresql://user:password@host:port/database"
        )
        
        if st.sidebar.button("🔗 Connect to PostgreSQL") and pg_url:
            try:
                vn.connect_to_database(pg_url)
                tables = vn.db_adapter.get_tables()
                db_name = getattr(vn, 'db_name', None) or pg_url
                set_connected(pg_url, db_name)
                st.sidebar.success(f"✅ Connected to PostgreSQL database: {db_name}")
                st.sidebar.write("📄 Tables:", tables)
            except Exception as e:
                st.sidebar.error(f"❌ Failed to connect: {e}")

    elif connection_type == "Existing SQLite Files":
        # List existing SQLite files in db directory
        if os.path.exists("db"):
            db_files = [f for f in os.listdir("db") if f.endswith(".db")]
            if db_files:
                selected_db = st.sidebar.selectbox("🗃️ Available SQLite Files", db_files)
                
                if st.sidebar.button("🔗 Connect to Selected File") and selected_db:
                    try:
                        db_path = f"db/{selected_db}"
                        vn.connect_to_sqlite(db_path)
                        tables = vn.db_adapter.get_tables()
                        db_name = getattr(vn, 'db_name', None) or selected_db
                        set_connected(f"sqlite:///{db_path}", db_name)
                        st.sidebar.success(f"✅ Connected to database: {db_name}")
                        st.sidebar.write("📄 Tables:", tables)
                    except Exception as e:
                        st.sidebar.error(f"❌ Failed to connect: {e}")
            else:
                st.sidebar.warning("⚠️ No SQLite files found in db/ directory")
        else:
            st.sidebar.warning("⚠️ db/ directory not found")
else:
    # Show connected DB info and disconnect button
    st.sidebar.success(f"Connected to: {st.session_state['db_name']}")
    st.sidebar.write(f"Connection string: {st.session_state['db_connection_string']}")
    if st.sidebar.button("❌ Disconnect"):
        disconnect_db()
        st.experimental_rerun()

# --- Main section: Ask question ---
st.markdown("---")
question = st.text_input("💬 Your question:", placeholder="Example: Who has the highest score?")

if st.button("🚀 Ask") and question:
    with st.spinner("🤖 Processing..."):
        try:
            # Inject table name hint (if exists)
            table_hint = st.session_state.get("table_name")
            if table_hint:
                question_hint = f"(Assume the table is named '{table_hint}') {question}"
            else:
                question_hint = question

            sql, df, _ = vn.ask(question_hint)

            st.session_state["sql"] = sql
            st.session_state["df"] = df
            st.session_state["question"] = question

            st.code(sql, language='sql')

            if df is not None and not df.empty:
                st.success("✅ Result:")
                st.dataframe(df)
                # --- Save Result Button ---
                save_result_clicked = st.button("💾 Save This Result")
                if save_result_clicked:
                    try:
                        save_result_to_disk(question, sql, df)
                        st.success("Result saved to disk! You can use it for report generation later.")
                        st.info(f"Saved to: {get_results_folder()}")
                    except Exception as e:
                        st.error(f"❌ Failed to save result: {e}")
                        st.exception(e)
            else:
                st.warning("⚠️ No data returned.")
        except Exception as e:
            st.error(f"❌ Error processing question: {e}")

# --- Helper functions for saving/loading results ---
def get_results_folder():
    db_name = getattr(vn, 'db_name', None)
    if not db_name:
        db_name = 'default'
    folder = os.path.join('saved_results', db_name)
    os.makedirs(folder, exist_ok=True)
    return folder

def save_result_to_disk(question, sql, df):
    folder = get_results_folder()
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    base = os.path.join(folder, timestamp)
    # Save metadata
    meta = {'question': question, 'sql': sql, 'csv': f'{timestamp}.csv'}
    with open(base + '.json', 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    # Save DataFrame
    df.to_csv(base + '.csv', index=False)

def load_all_saved_results():
    folder = get_results_folder()
    results = []
    for fname in os.listdir(folder):
        if fname.endswith('.json'):
            with open(os.path.join(folder, fname), 'r', encoding='utf-8') as f:
                meta = json.load(f)
            csv_path = os.path.join(folder, meta['csv'])
            if os.path.exists(csv_path):
                df = pd.read_csv(csv_path)
                results.append({'question': meta['question'], 'sql': meta['sql'], 'df': df})
    return results

# --- Saved Results Section ---
if st.session_state.get("db_connected", False):
    st.markdown("---")
    st.subheader("📚 Saved Results (from disk)")
    disk_results = load_all_saved_results()
    if disk_results:
        options = [f"{i+1}. {item['question']}" for i, item in enumerate(disk_results)]
        selected_idx = st.selectbox("Select a saved result to view:", options, key="disk_saved_result_select")
        idx = options.index(selected_idx)
        selected_result = disk_results[idx]
        st.write(f"**SQL:**\n```sql\n{selected_result['sql']}\n```")
        st.dataframe(selected_result['df'])
    else:
        st.info("No saved results yet. Run a query and save it to disk to use this feature.")

    # --- Generate Report from All Saved Results ---
    if disk_results:
        if st.button("📝 Generate Report from All Saved Results"):
            with st.spinner("✍️ Generating report from all saved results..."):
                try:
                    # Combine all questions, SQLs, and DataFrames
                    all_questions = '\n'.join([item['question'] for item in disk_results])
                    all_sqls = '\n'.join([item['sql'] for item in disk_results])
                    # For simplicity, concatenate all DataFrames vertically
                    all_df = pd.concat([item['df'] for item in disk_results], ignore_index=True)
                    report = generate_report(
                        all_questions,
                        all_sqls,
                        all_df,
                        llm_api_url=vn.base_url
                    )
                    st.subheader("📄 Report from All Saved Results:")
                    st.write(report)
                except Exception as e:
                    st.error(f"❌ Failed to generate report: {e}")

# --- Footer ---
st.markdown("---")
st.caption("🔧 Powered by Vanna AI, Streamlit & SQLite")
