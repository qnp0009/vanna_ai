import os
import streamlit as st
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
        save_excel_to_db(file_path, db_path)
        st.sidebar.success(f"✅ Successfully converted to {uploaded_file.name}.db")
    except Exception as e:
        st.sidebar.error(f"❌ Failed to convert file: {e}")

# --- Sidebar: Select database ---
st.sidebar.header("📂 Select Database")
db_files = [f for f in os.listdir("db") if f.endswith(".db")]
selected_db = st.sidebar.selectbox("🗃️ Available Databases", db_files)

if selected_db:
    try:
        db_path = f"db/{selected_db}"
        vn.connect_to_sqlite(db_path)
        tables = vn.run_sql("SELECT name FROM sqlite_master WHERE type='table'")
        st.sidebar.success("✅ Connected to database")
        st.sidebar.write("📄 Tables:", tables)
    except Exception as e:
        st.sidebar.error(f"❌ Failed to connect to database: {e}")

# --- Main section: Ask question ---
st.markdown("---")
question = st.text_input("💬 Your question:", placeholder="Example: Who has the highest score?")

if st.button("🚀 Ask") and question:
    with st.spinner("🤖 Processing..."):
        try:
            sql, df, q = vn.ask(question)
            st.code(sql, language='sql')

            if df is not None and not df.empty:
                st.success("✅ Result:")
                st.dataframe(df)

                # --- Button to generate report ---
                if st.button("📝 Generate Report"):
                    try:
                        report = generate_report(question, sql, df, llm_api_url=vn.base_url)
                        st.subheader("📄 Report:")
                        st.write(report)
                    except Exception as e:
                        st.error(f"❌ Failed to generate report: {e}")
            else:
                st.warning("⚠️ No data returned.")
        except Exception as e:
            st.error(f"❌ Error processing question: {e}")

# --- Footer ---
st.markdown("---")
st.caption("🔧 Powered by Vanna AI, Streamlit & SQLite")
