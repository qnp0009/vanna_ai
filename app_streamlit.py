import os
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import io

from app.report_writer import generate_report
from app.slides_planner import ask_llm_for_slides, deduplicate_charts
from app.reveal_generator import generate_reveal_html
from config.config import vn
from core.adapter import DBAdapter

@st.cache_resource(show_spinner=False)
def load_training_data_cached():
    vn.load_training_data()
    return vn.training_data

@st.cache_data(show_spinner=False)
def generate_slides_cached(question, sql, df, base_url, api_key):
    report = generate_report(question, sql, df, llm_api_url=base_url)
    metadata = f"Columns: {', '.join(df.columns)}"
    slides = ask_llm_for_slides(
        report_text=report,
        metadata=metadata,
        api_key=api_key,
        base_url=base_url
    )
    html_string = generate_reveal_html(
        slides_json=slides,
        df=df,
        return_html=True
    )
    return html_string

# --- Load training data (cached) ---
load_training_data_cached()

# --- Initialize session state for multiple queries ---
if 'query_history' not in st.session_state:
    st.session_state['query_history'] = []

# --- Page setup ---
st.set_page_config(page_title="Vanna AI Report Assistant", layout="wide")
st.title("🧠 Vanna AI - From Question to Report")
st.markdown("Upload a database, select a database, ask questions, wait for sql result and let AI write a report and slides for you.")

# --- Sidebar: Select database ---
st.sidebar.header("Select Database")

# --- Sidebar: Upload database file ---
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

        # Show schema for all tables
        st.sidebar.markdown("---")
        st.sidebar.markdown("🗄️ **Database Schema:**")
        
        # Cache the schema extraction to avoid repeated calls
        @st.cache_data
        def get_all_schema():
            return vn.extract_all_tables_schema()
        
        all_schema = get_all_schema()
        st.sidebar.text_area("📋 All Tables Schema", all_schema, height=300, disabled=True)

    except Exception as e:
        st.sidebar.error(f"❌ Failed to connect to database: {e}")

# --- Sidebar: Query History ---
if 'history' not in st.session_state:
    st.session_state['history'] = []

st.sidebar.markdown("---")
st.sidebar.markdown("🕑 **Query History**")

if st.session_state['history']:
    for i, item in enumerate(reversed(st.session_state['history'])):
        if st.sidebar.button(f"{item['question']}", key=f"history_{i}"):
            st.session_state['question_restore'] = item['question']
        st.sidebar.caption(f"SQL: {item['sql'][:50]}..." if item['sql'] else "")
else:
    st.sidebar.caption("No queries yet.")

# --- Sidebar: Multiple Queries Summary ---
st.sidebar.markdown("---")
st.sidebar.markdown("📊 **Multiple Queries Summary**")
st.sidebar.write(f"Total queries: {len(st.session_state['query_history'])}")

if st.session_state['query_history']:
    for i, query_info in enumerate(st.session_state['query_history']):
        st.sidebar.markdown(f"**Query {i+1}:** {query_info['question'][:30]}...")
        st.sidebar.caption(f"Rows: {len(query_info['df'])} | Cols: {len(query_info['df'].columns)}")

# --- Tabs for main content ---
tabs = st.tabs(["💬 Q&A", "📖 User Guide", "📊 Comprehensive Report"])

with tabs[1]:
    st.header("📖 How to use Vanna AI")
    st.markdown("""
    **How to use:**
    1. Select a database in the left sidebar.
    2. Ask natural language questions about your data (you can ask about multiple tables at once).
    3. View results, SQL, and generate reports/slides if you want.
    4. Use the "Comprehensive Report" tab to generate a report based on all your queries.

    **Example questions:**
    - Who has the highest score?
    - List all students and their scores.
    - Compare the number of students between tables.
    - Combine data from the students and scores tables.
    - How many students do not have a score?
    - What is the total score for each class?

    **Tips:**
    - You can ask about any table, or multiple tables at once.
    - If the result is not correct, try rephrasing your question more clearly.
    - You can generate presentation slides from the result.
    - Use multiple queries to gather comprehensive data, then generate a comprehensive report.
    """)

# --- Main section: Ask question ---
with tabs[0]:
    st.markdown("---")
    st.markdown("💡 **Tip:** You can ask questions about any table in the database. The AI will automatically use the appropriate tables to answer your question.")

    def submit_question():
        st.session_state['submit_question'] = True

    if 'question_restore' in st.session_state:
        question = st.text_input(
            "💬 Your question:",
            value=st.session_state.pop('question_restore'),
            placeholder="Example: Who has the highest score? Show me data from all tables. Compare results between tables.",
            key="question_input",
            on_change=submit_question
        )
    else:
        question = st.text_input(
            "💬 Your question:",
            placeholder="Example: Who has the highest score? Show me data from all tables. Compare results between tables.",
            key="question_input",
            on_change=submit_question
        )

    ask_clicked = st.button("🚀 Ask") or st.session_state.get('submit_question', False)
    if ask_clicked and question:
        st.session_state['submit_question'] = False
        with st.spinner("🤖 Processing..."):
            try:
                sql, df, _ = vn.ask(question)
                st.session_state["sql"] = sql
                st.session_state["df"] = df
                st.session_state["question"] = question
                st.session_state["has_result"] = df is not None and not df.empty
                
                # Save to query history
                summary = df.head(1).to_dict() if (df is not None and not df.empty) else None
                st.session_state['history'].append({
                    'question': question,
                    'sql': sql,
                    'summary': summary
                })
                
                # Save to multiple queries history
                if st.session_state["has_result"] and df is not None:
                    st.session_state['query_history'].append({
                        'question': question,
                        'sql': sql,
                        'df': df.copy()
                    })
                
                # Auto-generate report if data is available
                if st.session_state["has_result"]:
                    st.session_state['auto_generate_report'] = True
                else:
                    st.error("❌ No data returned from the query. Cannot generate report.")
                    
            except Exception as e:
                st.error(f"❌ Error processing question: {e}")

    # Always show result, chart, and slides if available
    if st.session_state.get("has_result") and st.session_state.get("df") is not None and not st.session_state["df"].empty:
        st.code(st.session_state["sql"], language='sql')
        st.success("✅ Result:")
        st.dataframe(st.session_state["df"])
        # Auto chart generation removed

        # Add user request input box after SQL result
        if st.session_state.get("has_result"):
            def trigger_slides():
                st.session_state['trigger_generate_slides'] = True
            
            st.text_area(
                "✍️ Requests for your report (optional):",
                value=st.session_state.get('user_request', ''),
                key="user_request",
                placeholder="Enter your requests, comments, or any content you want to emphasize in the report/slides... (Press Enter to generate slides)",
                disabled=not st.session_state.get("has_result"),
                on_change=trigger_slides
            )
            user_request = st.session_state.get('user_request', '')
        else:
            user_request = ""

        # --- Generate Slides button (Reveal.js version) ---
        generate_slides_disabled = not st.session_state.get("has_result")
        generate_slides_clicked = st.button("📊 Generate slides", disabled=generate_slides_disabled) or st.session_state.get('trigger_generate_slides', False)
        
        # Reset the trigger
        if st.session_state.get('trigger_generate_slides'):
            st.session_state['trigger_generate_slides'] = False
            
        if generate_slides_clicked:
            progress = st.progress(0, text="Generating report...")
            try:
                # Step 1: Generate report
                progress.progress(10, text="Generating report...")
                # Add user_request to the question for LLM to generate a more relevant report
                question_for_report = st.session_state["question"]
                if user_request:
                    question_for_report += f"\nAdditional requests: {user_request}"
                report = generate_report(
                    question_for_report,
                    st.session_state["sql"],
                    st.session_state["df"],
                    llm_api_url=vn.base_url
                )
                
                # Save report to session state
                st.session_state['current_report'] = report
                
                progress.progress(40, text="Planning slides...")
                metadata = f"Columns: {', '.join(st.session_state['df'].columns)}"
                slides = ask_llm_for_slides(
                    report_text=report,
                    metadata=metadata,
                    api_key=os.getenv("LLM_API_KEY"),
                    base_url=vn.base_url
                )
                slides = deduplicate_charts(slides)
                progress.progress(70, text="Generating HTML...")
                html_string = generate_reveal_html(
                    slides_json=slides,
                    df=st.session_state["df"],
                    return_html=True
                )
                progress.progress(100, text="Done!")
                components.html(html_string, height=600, scrolling=False)
            except Exception as e:
                st.error(f"❌ Failed to generate Reveal.js slides: {e}")
            finally:
                progress.empty()
        
        # Show report if available
        if st.session_state.get('current_report'):
            st.markdown("## 📋 Generated Report")
            st.markdown(st.session_state['current_report'])
            
            # Generate slides from current report
            def trigger_current_slides():
                st.session_state['trigger_current_slides'] = True
            
            current_slides_clicked = st.button("📊 Generate Slides from Report") or st.session_state.get('trigger_current_slides', False)
            
            # Reset the trigger
            if st.session_state.get('trigger_current_slides'):
                st.session_state['trigger_current_slides'] = False
                
            if current_slides_clicked:
                progress = st.progress(0, text="Generating slides from report...")
                try:
                    # Step 1: Planning slides
                    progress.progress(20, text="Planning slides...")
                    metadata = f"Columns: {', '.join(st.session_state['df'].columns)}"
                    slides = ask_llm_for_slides(
                        report_text=st.session_state['current_report'],
                        metadata=metadata,
                        api_key=os.getenv("LLM_API_KEY"),
                        base_url=vn.base_url
                    )
                    slides = deduplicate_charts(slides)
                    
                    # Step 2: Generating HTML
                    progress.progress(60, text="Generating HTML...")
                    html_string = generate_reveal_html(
                        slides_json=slides,
                        df=st.session_state["df"],
                        return_html=True
                    )
                    
                    progress.progress(100, text="Done!")
                    
                    # Display slides
                    st.markdown("## 📊 Report Slides")
                    components.html(html_string, height=600, scrolling=False)
                    
                except Exception as e:
                    st.error(f"❌ Failed to generate slides from report: {e}")
                finally:
                    progress.empty()

# --- Comprehensive Report Tab ---
with tabs[2]:
    st.header("📊 Comprehensive Report")
    st.markdown("Generate a comprehensive report based on all your queries and their results.")
    
    if not st.session_state['query_history']:
        st.info("No queries yet. Please run some queries in the Q&A tab first.")
    else:
        st.markdown(f"**Total queries collected:** {len(st.session_state['query_history'])}")
        
        # Show summary of all queries
        for i, query_info in enumerate(st.session_state['query_history']):
            with st.expander(f"Query {i+1}: {query_info['question']}"):
                st.code(query_info['sql'], language='sql')
                st.write(f"**Data:** {len(query_info['df'])} rows × {len(query_info['df'].columns)} columns")
                st.dataframe(query_info['df'].head(5))
        
        # User request for comprehensive report
        def trigger_comprehensive_report():
            st.session_state['trigger_comprehensive_report'] = True
        
        st.text_area(
            "✍️ Additional requests for comprehensive report (optional):",
            value=st.session_state.get('comprehensive_request', ''),
            key="comprehensive_request",
            placeholder="Enter any specific requirements for the comprehensive report... (Press Enter to generate report)",
            on_change=trigger_comprehensive_report
        )
        comprehensive_request = st.session_state.get('comprehensive_request', '')
        
        # Generate comprehensive report button
        comprehensive_report_clicked = st.button("📋 Generate Comprehensive Report", disabled=len(st.session_state['query_history']) == 0) or st.session_state.get('trigger_comprehensive_report', False)
        
        # Reset the trigger
        if st.session_state.get('trigger_comprehensive_report'):
            st.session_state['trigger_comprehensive_report'] = False
            
        if comprehensive_report_clicked:
            progress = st.progress(0, text="Generating comprehensive report...")
            try:
                # Combine all queries and data
                all_questions = []
                all_sqls = []
                all_dfs = []
                
                for query_info in st.session_state['query_history']:
                    all_questions.append(query_info['question'])
                    all_sqls.append(query_info['sql'])
                    all_dfs.append(query_info['df'])
                
                # Create comprehensive question
                comprehensive_question = f"Comprehensive analysis based on {len(all_questions)} queries:\n"
                for i, q in enumerate(all_questions, 1):
                    comprehensive_question += f"{i}. {q}\n"
                
                if comprehensive_request:
                    comprehensive_question += f"\nAdditional requirements: {comprehensive_request}"
                
                # Combine all dataframes
                combined_df = pd.concat(all_dfs, ignore_index=True)
                
                progress.progress(30, text="Generating comprehensive report...")
                
                # Generate comprehensive report
                comprehensive_report = generate_report(
                    comprehensive_question,
                    "\n".join(all_sqls),
                    combined_df,
                    llm_api_url=vn.base_url
                )
                
                # Save comprehensive report to session state
                st.session_state['comprehensive_report'] = comprehensive_report
                st.session_state['comprehensive_combined_df'] = combined_df
                
                progress.progress(100, text="Done!")
                
            except Exception as e:
                st.error(f"❌ Failed to generate comprehensive report: {e}")
            finally:
                progress.empty()
        
        # Show comprehensive report if available
        if st.session_state.get('comprehensive_report'):
            st.markdown("## 📋 Comprehensive Report")
            st.markdown(st.session_state['comprehensive_report'])
            
            # Generate slides from comprehensive report
            def trigger_comprehensive_slides():
                st.session_state['trigger_comprehensive_slides'] = True
            
            comprehensive_slides_clicked = st.button("📊 Generate Slides from Comprehensive Report") or st.session_state.get('trigger_comprehensive_slides', False)
            
            # Reset the trigger
            if st.session_state.get('trigger_comprehensive_slides'):
                st.session_state['trigger_comprehensive_slides'] = False
                
            if comprehensive_slides_clicked:
                progress = st.progress(0, text="Generating slides from comprehensive report...")
                try:
                    # Step 1: Planning slides
                    progress.progress(20, text="Planning slides...")
                    metadata = f"Columns: {', '.join(st.session_state['comprehensive_combined_df'].columns)}"
                    slides = ask_llm_for_slides(
                        report_text=st.session_state['comprehensive_report'],
                        metadata=metadata,
                        api_key=os.getenv("LLM_API_KEY"),
                        base_url=vn.base_url
                    )
                    slides = deduplicate_charts(slides)
                    
                    # Step 2: Generating HTML
                    progress.progress(60, text="Generating HTML...")
                    html_string = generate_reveal_html(
                        slides_json=slides,
                        df=st.session_state['comprehensive_combined_df'],
                        return_html=True
                    )
                    
                    progress.progress(100, text="Done!")
                    
                    # Display slides
                    st.markdown("## 📊 Comprehensive Report Slides")
                    components.html(html_string, height=600, scrolling=False)
                    
                except Exception as e:
                    st.error(f"❌ Failed to generate slides from comprehensive report: {e}")
                finally:
                    progress.empty()

# --- Footer ---
st.markdown("---")
st.caption("🔧 Powered by Vanna AI and Streamlit")
