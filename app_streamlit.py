import os
import streamlit as st
import streamlit.components.v1 as components
from app.report_writer import generate_report, remove_think_blocks
from app.slides_planner import ask_llm_for_slides, deduplicate_charts
from app.reveal_generator import generate_reveal_html
from config.config import vn
from core.adapter import DBAdapter
import pandas as pd
import json

# --- Load training data (no cache) ---
vn.load_training_data()

# --- Page setup ---
st.set_page_config(page_title="Vanna AI Report Assistant", layout="wide")
st.title("🧠 Vanna AI - From Question to Report")
st.markdown("Upload a database, select a database, ask questions, wait for sql result and let AI write a report and slides for you.")

# --- Sidebar: Select database ---
st.sidebar.header("Select Database")

# Upload DB
st.sidebar.markdown("---")
st.sidebar.subheader("⬆️ Upload a new database (.db)")
db_file_upload = st.sidebar.file_uploader("Choose a .db file to upload", type=["db"])
if db_file_upload is not None:
    import shutil
    db_save_path = os.path.join("db", db_file_upload.name)
    try:
        with open(db_save_path, "wb") as f:
            shutil.copyfileobj(db_file_upload, f)
        st.sidebar.success(f"✅ Uploaded and saved as {db_file_upload.name}")
    except Exception as e:
        st.sidebar.error(f"❌ Failed to save file: {e}")

db_files = [f for f in os.listdir("db") if f.endswith(".db")]
selected_db = st.sidebar.selectbox("🗃️ Available Databases", db_files)

if selected_db:
    try:
        db_path = f"db/{selected_db}"
        db_adapter = DBAdapter(f"sqlite:///{db_path}")
        vn.db_adapter = db_adapter
        vn.connect_to_sqlite(db_path)

        st.sidebar.success("✅ Connected to database")

        all_schema = vn.extract_all_tables_schema()
        st.sidebar.markdown("---")
        st.sidebar.markdown("🗄️ **Database Schema:**")
        st.sidebar.text_area("📋 All Tables Schema", all_schema, height=300, disabled=True)

    except Exception as e:
        st.sidebar.error(f"❌ Failed to connect to database: {e}")

# --- Initialize session state ---
if 'query_history' not in st.session_state:
    st.session_state['query_history'] = []

# --- Main Section ---
st.markdown("---")
st.markdown("💡 **Enter a high-level request (e.g., 'Quarter 1 2020 report') and let AI do the rest!**")

def auto_generate_report():
    st.session_state['trigger_auto_report'] = True

user_request = st.text_area(
    "Your report request:",
    value=st.session_state.get('user_request', ''),
    key="user_request",
    placeholder="E.g., Write a business report for Q1 2020...",
    on_change=auto_generate_report
)

trigger_report = st.button("🚀 Auto Plan & Generate Report") or st.session_state.get('trigger_auto_report', False)
if st.session_state.get('trigger_auto_report'):
    st.session_state['trigger_auto_report'] = False

if trigger_report and user_request.strip():
    progress = st.progress(0, text="Planning queries...")
    st.info("Step 1: AI is planning queries for your report...")

    plan_prompt = f"""
You are a data analyst assistant. Break the following user request into sub-questions and write SQL for each.

User request: {user_request}

Database schema:
{vn.extract_all_tables_schema()}

Return as JSON list with "subquestion" and "sql".
"""
    plan_response = vn.submit_prompt([
        vn.system_message("You are a careful, detail-driven data analyst."),
        vn.user_message(plan_prompt)
    ])

    try:
        plan = json.loads(plan_response[plan_response.find('['):plan_response.rfind(']')+1])
    except Exception as e:
        st.error(f"❌ Failed to parse plan: {e}")
        st.stop()

    st.success("✅ Query Plan:")
    for i, item in enumerate(plan):
        st.markdown(f"**{i+1}. {item['subquestion']}**\n```sql\n{item['sql']}\n```")

    progress.progress(10, text="Executing SQL queries...")
    results = []
    all_dfs = []

    for idx, item in enumerate(plan):
        try:
            # Check if db_adapter is initialized
            if vn.db_adapter is None:
                st.error("❌ Database adapter not initialized. Please select a database first.")
                st.stop()
            
            df = vn.db_adapter.run_sql(item['sql'])
            df['__source__'] = item['subquestion']
            all_dfs.append(df)
            results.append({
                "subquestion": item['subquestion'],
                "sql": item['sql'],
                "result": df.to_dict(orient='records')
            })

            # Save to query history
            st.session_state['query_history'].append({
                "question": item['subquestion'],
                "sql": item['sql'],
                "df": df
            })

            st.success(f"✅ Query {idx+1} executed.")
        except Exception as e:
            st.error(f"❌ Query {idx+1} failed: {e}")
            results.append({
                "subquestion": item['subquestion'],
                "sql": item['sql'],
                "result": f"Error: {e}"
            })

        progress.progress(10 + int(60 * (idx + 1) / len(plan)), text=f"Executed {idx+1}/{len(plan)}")

    combined_df = pd.concat(all_dfs, ignore_index=True) if all_dfs else pd.DataFrame()

    st.session_state['current_df'] = combined_df
    st.session_state['current_plan'] = plan
    st.session_state['current_report_data'] = results

    progress.progress(75, text="Generating report...")
    summary = "\n".join([f"{r['subquestion']}\nSQL: {r['sql']}\nResult: {r['result']}" for r in results])

    report = generate_report(
        question=user_request,
        sql="\n".join([item['sql'] for item in plan]),
        data_frame=combined_df,
        llm_api_url=vn.base_url,
        api_key=os.getenv("LLM_API_KEY")
    )
    
    # Save report to session state
    st.session_state['current_report'] = report
    progress.progress(100, text="Done!")
    
    st.markdown("## 📋 Generated Report")
    st.markdown(report)

# --- Slide Generation ---
if st.session_state.get("current_report"):
    st.markdown("---")
    st.markdown("## 📊 Generate Slides")
    
    if st.button("📊 Generate Slides from Report"):
        # Check if current_df exists
        if 'current_df' not in st.session_state or st.session_state['current_df'] is None or st.session_state['current_df'].empty:
            st.error("❌ No data available for slides. Please ensure the report was generated successfully.")
            st.stop()
        
        slides_progress = st.progress(0, text="Planning slides...")
        with st.spinner("Generating slides from report..."):
            try:
                # Get data from session state
                current_df = st.session_state['current_df']
                current_plan = st.session_state.get('current_plan', [])
                current_report = st.session_state['current_report']
                
                # Create comprehensive metadata
                columns_str = ', '.join(current_df.columns)
                if current_plan:
                    subquestions_str = ', '.join(item['subquestion'] for item in current_plan)
                    metadata = f"Columns: {columns_str}. Subquestions: {subquestions_str}"
                else:
                    metadata = f"Columns: {columns_str}"
                
                slides_progress.progress(20, text="Calling LLM for slides...")
                
                # Call LLM to create slides
                slides = ask_llm_for_slides(
                    report_text=current_report,
                    metadata=metadata,
                    api_key=os.getenv("LLM_API_KEY"),
                    base_url=vn.base_url
                )
                
                if not slides:
                    st.warning("⚠️ LLM returned empty slides. Please check your prompt or LLM connection.")
                    st.stop()
                
                slides_progress.progress(60, text="Deduplicating charts...")
                slides = deduplicate_charts(slides)
                
                slides_progress.progress(80, text="Generating HTML...")
                
                # Generate HTML slides with clear df
                html_string = generate_reveal_html(
                    slides_json=slides,
                    df=current_df,  # Pass current_df clearly
                    return_html=True
                )
                
                # Save to session state
                st.session_state['current_slides_html'] = html_string
                slides_progress.progress(100, text="✅ Slides Generated!")
                
                # Display slides
                st.markdown("## 📊 Report Slides")
                components.html(html_string, height=600, scrolling=False)
                
            except Exception as e:
                st.error(f"❌ Failed to generate slides: {e}")

# --- Footer ---
st.markdown("---")
st.markdown("*Powered by Vanna AI*")
