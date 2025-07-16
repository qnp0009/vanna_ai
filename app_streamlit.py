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

# --- New: Connect via Endpoint ---
st.sidebar.markdown("---")
st.sidebar.subheader("🔗 Kết nối Database từ xa (Connection String)")
db_endpoint = st.sidebar.text_input(
    "Nhập Database Endpoint (Connection String):",
    value="",
    placeholder="Ví dụ: postgresql+psycopg2://user:pass@host:5432/dbname"
)
connect_btn = st.sidebar.button("Kết nối Endpoint")
endpoint_tables = []
if db_endpoint and connect_btn:
    try:
        endpoint_adapter = DBAdapter(db_endpoint)
        endpoint_tables = endpoint_adapter.list_tables()
        st.sidebar.success(f"✅ Kết nối thành công! Các bảng: {endpoint_tables}")
        vn.db_adapter = endpoint_adapter
        st.session_state['db_mode'] = 'endpoint'
        st.session_state['endpoint_adapter'] = endpoint_adapter
        st.session_state['endpoint_tables'] = endpoint_tables
    except Exception as e:
        st.sidebar.error(f"❌ Lỗi kết nối: {e}")

# Nếu đã kết nối endpoint, cho phép chọn bảng và preview
if st.session_state.get('db_mode') == 'endpoint' and st.session_state.get('endpoint_tables'):
    st.sidebar.markdown("---")
    st.sidebar.markdown("🗄️ **Endpoint Tables:**")
    selected_endpoint_table = st.sidebar.selectbox(
        "Chọn bảng để xem preview (Endpoint)",
        st.session_state['endpoint_tables']
    )
    if selected_endpoint_table:
        try:
            preview_df = st.session_state['endpoint_adapter'].get_table_preview(selected_endpoint_table)
            st.sidebar.dataframe(preview_df)
        except Exception as e:
            st.sidebar.error(f"❌ Không thể preview bảng: {e}")

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
    progress = st.progress(0, text="Starting Chain-of-Thought reasoning...")
    st.info("🧠 Step 1: Thinking about the sub-question...")

    conversation_steps = []
    step = 0

    while True:
        # Đưa lại subquestion và kết quả từng step vào prompt, không đưa SQL, loại bỏ '__source__' khỏi result
        def clean_result(result):
            if isinstance(result, list):
                return [
                    {k: v for k, v in row.items() if k != "__source__"}
                    for row in result
                ]
            return result
        context = "\n".join([
            f"Step {i+1}:\nSubquestion: {c['subquestion']}\nResult: {json.dumps(clean_result(c.get('result', '')), ensure_ascii=False, indent=2)}"
            for i, c in enumerate(conversation_steps)
        ])

        cot_prompt = f"""
You are an analytical assistant. The user asked:

"{user_request}"

{vn.extract_all_tables_schema()}

So far, these are the subquestions completed:
{context if context else "None yet."}

What is the next subquestion you should answer to help generate the report?
Respond in JSON format: {{ "subquestion": "...", "sql": "..." }}
If no more are needed, return: DONE
"""
        response = vn.submit_prompt([
            vn.system_message("You are a careful, step-by-step business analyst."),
            vn.user_message(cot_prompt)
        ])

        step += 1

        # Check if done
        if "DONE" in response.strip().upper():
            # Extract LLM's reasoning if available
            reasoning = None
            # Try to extract reasoning after 'DONE' or in the response
            if 'reason' in response.lower():
                # Try to extract a reason field if present
                try:
                    resp_json = json.loads(response[response.find('{'):response.rfind('}')+1])
                    reasoning = resp_json.get('reason')
                except Exception:
                    pass
            if not reasoning:
                # Fallback: try to extract any text after 'DONE' as reasoning
                done_idx = response.upper().find('DONE')
                after_done = response[done_idx+4:].strip()
                if after_done:
                    reasoning = after_done
            st.info(f"✅ LLM determined that all questions are answered at step {step}.")
            if reasoning:
                st.markdown(f"**🤖 LLM reasoning for completion:**\n\n{reasoning}")
            break

        # Parse response
        try:
            step_data = json.loads(response[response.find('{'):response.rfind('}')+1])
        except Exception as e:
            st.error(f"❌ Failed to parse response at step {step}: {e}")
            break

        # Debug: Show LLM's reasoning prompt and raw response
        with st.expander(f"🧠 Debug: LLM Prompt & Response for Step {step}"):
            st.markdown("**Prompt sent to LLM:**")
            st.code(cot_prompt, language="markdown")
            st.markdown("**Raw LLM response:**")
            st.code(response, language="json")

        st.markdown(f"### 🔍 Step {step}: {step_data['subquestion']}")
        st.code(step_data['sql'], language="sql")

        try:
            if vn.db_adapter is None:
                st.error("❌ Database adapter not initialized.")
                st.stop()

            df = vn.db_adapter.run_sql(step_data['sql'])
            df['__source__'] = step_data['subquestion']
            step_data['result'] = df.head(5).to_dict(orient='records')  # limit preview
            step_data['full_df'] = df  # keep full data for report

            # Debug: Show SQL result preview
            with st.expander(f"🗃️ SQL Result Preview for Step {step}"):
                st.dataframe(df.head(10))

            # Save to session
            conversation_steps.append(step_data)
            st.session_state['query_history'].append({
                "question": step_data['subquestion'],
                "sql": step_data['sql'],
                "df": df
            })

            st.success(f"✅ Query {step} executed successfully.")
        except Exception as e:
            st.error(f"❌ Query {step} failed: {e}")
            break

        progress.progress(min(85, int(step * 15)), text=f"Finished Step {step}")

    # Combine data
    all_dfs = [c['full_df'] for c in conversation_steps if 'full_df' in c]
    combined_df = pd.concat(all_dfs, ignore_index=True) if all_dfs else pd.DataFrame()
    st.session_state['current_df'] = combined_df
    st.session_state['current_plan'] = conversation_steps
    st.session_state['current_report_data'] = conversation_steps

   # Final report generation
    progress.progress(90, text="📝 Generating report...")

    combined_df = pd.concat([c['full_df'] for c in conversation_steps if 'full_df' in c], ignore_index=True) if conversation_steps else pd.DataFrame()

    report = generate_report(
        question=user_request,
        sql="\n".join([c['sql'] for c in conversation_steps]),
        data_frame=combined_df,
        llm_api_url=vn.base_url,
        api_key=os.getenv("LLM_API_KEY")
    )

    report = remove_think_blocks(report)

    st.session_state['current_df'] = combined_df
    st.session_state['current_plan'] = conversation_steps
    st.session_state['current_report_data'] = conversation_steps
    st.session_state['current_report'] = report

    progress.progress(100, text="✅ Done!")

    st.markdown("## 📋 Final Report")
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
                
                # Create comprehensive metadata with column info
                columns_info = []
                for col in current_df.columns:
                    col_type = str(current_df[col].dtype)
                    unique_count = current_df[col].nunique()
                    columns_info.append(f"{col} ({col_type}, {unique_count} unique values)")
                
                columns_str = '; '.join(columns_info)
                if current_plan:
                    subquestions_str = '; '.join(item['subquestion'] for item in current_plan)
                    metadata = f"Dataset columns: {columns_str}. Analysis subquestions: {subquestions_str}"
                else:
                    metadata = f"Dataset columns: {columns_str}"
                
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
                
                # Add export buttons
                # col1, col2 = st.columns([1, 4])
                # with col1:
                #     if st.button("📄 Export PDF", help="Export slides as PDF"):
                #         st.info("💡 Use the PDF button in the slides viewer above to export the presentation.")
                # with col2:
                st.markdown("*The PDF export button is available in the slides viewer navigation.*")
                
                components.html(html_string, height=600, scrolling=False)
                
            except Exception as e:
                st.error(f"❌ Failed to generate slides: {e}")

# --- Footer ---
st.markdown("---")
st.markdown("*Powered by Vanna AI*")
