import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from datetime import datetime

# Set up Streamlit Page Configuration
st.set_page_config(
    page_title="AWS Agreement Assistant",
    page_icon="🔒",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom premium styling using CSS (Dark Mode & curated colors)
st.markdown("""
<style>
    /* Dark Theme & Background */
    .stApp {
        background-color: #0F172A;
        color: #F8FAFC;
    }
    
    /* Sidebar styling */
    section[data-testid="stSidebar"] {
        background-color: #1E293B !important;
        border-right: 1px solid #334155;
    }
    
    /* Titles and Headers */
    h1, h2, h3, h4 {
        color: #38BDF8 !important;
        font-family: 'Outfit', sans-serif;
    }
    
    /* Custom cards for sources and answers */
    .answer-card {
        background-color: #1E293B;
        border-left: 5px solid #0EA5E9;
        padding: 1.5rem;
        border-radius: 0.5rem;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
    }
    
    .source-card {
        background-color: #1E293B;
        border: 1px solid #334155;
        padding: 1rem;
        border-radius: 0.375rem;
        margin-top: 0.75rem;
    }
    
    .score-badge {
        background-color: #0369A1;
        color: #F0F9FF;
        padding: 0.2rem 0.6rem;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: bold;
    }

    .confidence-badge {
        background-color: #0F766E;
        color: #F0FDFA;
        padding: 0.2rem 0.6rem;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: bold;
        margin-left: 0.5rem;
    }
    
    .page-badge {
        background-color: #15803D;
        color: #F0FDF4;
        padding: 0.2rem 0.6rem;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: bold;
        margin-left: 0.5rem;
    }
    
    /* Button Premium Hover effect */
    div.stButton > button {
        background-color: #0EA5E9 !important;
        color: white !important;
        border: none !important;
        border-radius: 0.375rem !important;
        padding: 0.5rem 1rem !important;
        font-weight: 600 !important;
        transition: all 0.2s ease-in-out;
    }
    
    div.stButton > button:hover {
        background-color: #0284C7 !important;
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(14, 165, 233, 0.3);
    }
    
    /* Warning/Alert notices */
    .warning-box {
        background-color: #451A03;
        border-left: 5px solid #F59E0B;
        padding: 1rem;
        border-radius: 0.375rem;
        color: #FEF3C7;
        margin-bottom: 1.5rem;
    }
</style>
""", unsafe_allow_html=True)

BACKEND_URL = "http://localhost:8000"

def get_api_status():
    """Checks if the FastAPI server is reachable."""
    try:
        res = requests.get(f"{BACKEND_URL}/analytics", timeout=1.5)
        return res.status_code == 200
    except Exception:
        return False

# Check connection status once at start of request
api_online = get_api_status()

# Sidebar Navigation
st.sidebar.image("https://img.icons8.com/color/144/amazon-web-services.png", width=70)
st.sidebar.title("AWS Assistant")
st.sidebar.markdown("*RAG Document Assistant*")
st.sidebar.markdown("---")

page = st.sidebar.radio(
    "Navigation",
    ["💬 Chat Assistant", "📊 Analytics Dashboard", "⚙️ System Management"]
)

st.sidebar.markdown("---")
st.sidebar.markdown("### System Status")
if api_online:
    st.sidebar.success("🟢 API Server: Online")
else:
    st.sidebar.error("🔴 API Server: Offline")
    st.sidebar.info("Please start the backend server:\n\n`uvicorn app.api.main:app --reload`")

# Global check to handle offline server gracefully in main content area
if not api_online:
    st.warning("⚠️ **Connection Warning**: The FastAPI backend server is currently offline. Some features will be disabled or read-only.")

# ────────────────────────────────────────────────────────────────────────────
# PAGE 1: CHAT ASSISTANT
# ────────────────────────────────────────────────────────────────────────────
if page == "💬 Chat Assistant":
    st.title("💬 AWS Customer Agreement Chat")
    st.markdown("Ask natural language questions about the AWS Customer Agreement terms, billing, liabilities, and policies.")
    
    # Text input area
    query = st.text_input("Enter your question:", placeholder="e.g. How often does AWS bill customers?")
    
    submit_clicked = st.button("Submit Question", use_container_width=True)
    
    if submit_clicked or (query and st.session_state.get("last_query") != query):
        if not api_online:
            st.error("Cannot submit question: FastAPI backend is offline.")
        elif len(query.strip()) < 3:
            st.warning("⚠️ Question must be at least 3 characters long.")
        elif len(query.strip()) > 500:
            st.warning("⚠️ Question must be 500 characters or less.")
        else:
            st.session_state["last_query"] = query
            with st.spinner("Retrieving document context and generating answer..."):
                try:
                    res = requests.post(f"{BACKEND_URL}/ask", json={"query": query}, timeout=30)
                    if res.status_code == 200:
                        data = res.json()
                        answer = data["answer"]
                        found = data["answer_found"]
                        sources = data["sources"]
                        latency = data["response_time_ms"]
                        model = data["model_used"]
                        
                        if not found:
                            st.markdown(
                                f'<div class="warning-box">⚠️ <b>No direct answer found in context:</b><br>{answer}</div>',
                                unsafe_allow_html=True
                            )
                        else:
                            st.markdown(
                                f'<div class="answer-card"><h4>Answer:</h4><p style="font-size: 1.1rem; line-height: 1.6;">{answer}</p>'
                                f'<small style="color: #94A3B8;">Generated in {latency:.2f} ms using <b>{model}</b></small></div>',
                                unsafe_allow_html=True
                            )
                        
                        # Display Source Chunks
                        if sources:
                            with st.expander("📚 Source Reference Chunks", expanded=found):
                                st.markdown("Below are the top matching text segments retrieved from the agreement PDF:")
                                for i, src in enumerate(sources):
                                    # Convert FAISS distance to confidence percentage
                                    # FAISS distance of 0.0 -> 100% confidence. Distance >= 1.5 -> 0% confidence.
                                    dist = float(src["similarity_score"])
                                    confidence = max(0.0, min(100.0, (1.5 - dist) / 1.5 * 100.0))
                                    
                                    st.markdown(
                                        f'<div class="source-card">'
                                        f'<b>Source Chunk {i+1}</b> '
                                        f'<span class="score-badge">Distance: {dist:.4f}</span>'
                                        f'<span class="confidence-badge">Confidence: {confidence:.1f}%</span>'
                                        f'<span class="page-badge">Page: {src["page"]}</span>'
                                        f'<p style="margin-top: 0.5rem; font-style: italic; color: #CBD5E1;">"... {src["text_snippet"]} ..."</p>'
                                        f'</div>',
                                        unsafe_allow_html=True
                                    )
                    elif res.status_code == 409:
                        st.error("⚠️ Document has not been ingested yet. Please go to the 'System Management' tab and click Ingest.")
                    elif res.status_code == 400:
                        st.error(f"Bad Request (400): {res.json().get('detail', 'Query was invalid.')}")
                    else:
                        st.error(f"Error {res.status_code}: {res.json().get('detail', 'Unknown error')}")
                except Exception as e:
                    st.error(f"Failed to connect to backend: {e}")

# ────────────────────────────────────────────────────────────────────────────
# PAGE 2: ANALYTICS DASHBOARD
# ────────────────────────────────────────────────────────────────────────────
elif page == "📊 Analytics Dashboard":
    st.title("📊 SQL Logging & Analytics Dashboard")
    st.markdown("Real-time aggregated usage statistics pulled directly from the SQLite logs database.")
    
    if st.button("🔄 Refresh Data"):
        st.rerun()

    if not api_online:
        st.error("Analytics Dashboard unavailable: Connection to backend failed.")
    else:
        try:
            res = requests.get(f"{BACKEND_URL}/analytics", timeout=10)
            if res.status_code == 200:
                data = res.json()
                
                # Calculate unanswered queries count
                total_q = data["total_queries"]
                rate = data["answer_found_rate_pct"]
                unanswered_cnt = round(total_q * (100.0 - rate) / 100.0) if total_q > 0 else 0
                
                # 1. High-level metric cards
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Total Queries", total_q)
                with col2:
                    st.metric("Avg Latency (ms)", f"{data['average_response_time_ms']:.2f}")
                with col3:
                    st.metric("Unanswered Queries", unanswered_cnt)
                with col4:
                    st.metric("Answer Found Rate", f"{rate}%")
                    
                st.markdown("---")
                
                # 2. Plotly Charts Section
                col_chart1, col_chart2 = st.columns(2)
                
                with col_chart1:
                    st.subheader("🔥 Top Questions Frequency")
                    top_q = data["top_5_questions"]
                    if top_q:
                        df_q = pd.DataFrame(top_q)
                        # Sort for horizontal bar chart display
                        df_q = df_q.sort_values(by="frequency", ascending=True)
                        fig_q = px.bar(
                            df_q,
                            y="query",
                            x="frequency",
                            orientation="h",
                            color="frequency",
                            color_continuous_scale="Blues",
                            labels={"query": "User Question", "frequency": "Count"},
                            title="Most Frequent User Inquiries"
                        )
                        fig_q.update_layout(
                            paper_bgcolor="#1E293B",
                            plot_bgcolor="#1E293B",
                            font_color="#F8FAFC",
                            coloraxis_showscale=False,
                            xaxis=dict(gridcolor="#334155", showgrid=True),
                            yaxis=dict(showgrid=False),
                            margin=dict(l=20, r=20, t=40, b=20),
                            height=350
                        )
                        st.plotly_chart(fig_q, use_container_width=True)
                    else:
                        st.info("No query logs available yet.")

                with col_chart2:
                    st.subheader("📅 Query Volume by Hour (UTC)")
                    vol = data["query_volume_by_hour"]
                    if vol:
                        df_vol = pd.DataFrame(vol)
                        fig_vol = px.line(
                            df_vol,
                            x="hour",
                            y="queries",
                            markers=True,
                            labels={"hour": "Hour of Day (UTC)", "queries": "Queries Count"},
                            title="Queries Count Hourly Distribution"
                        )
                        fig_vol.update_layout(
                            paper_bgcolor="#1E293B",
                            plot_bgcolor="#1E293B",
                            font_color="#F8FAFC",
                            xaxis=dict(gridcolor="#334155", showgrid=True),
                            yaxis=dict(gridcolor="#334155", showgrid=True),
                            margin=dict(l=20, r=20, t=40, b=20),
                            height=350
                        )
                        st.plotly_chart(fig_vol, use_container_width=True)
                    else:
                        st.info("No hourly volume logs available yet.")

                st.markdown("---")

                # 3. CSV Export and Data Table
                st.subheader("📋 Detailed Frequent Queries Table")
                top_all = data["top_queries"]
                if top_all:
                    df_all = pd.DataFrame(top_all)
                    st.dataframe(df_all, use_container_width=True)
                    
                    # Export as CSV Button
                    csv = df_all.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="📥 Export Queries Frequency as CSV",
                        data=csv,
                        file_name="aws_agreement_assistant_queries.csv",
                        mime="text/csv"
                    )
                else:
                    st.info("No data table available.")

                st.markdown("---")

                # 4. Unanswered / Unanswerable Queries List
                st.subheader("❌ Unanswered / Out-of-Scope Queries List")
                unanswered = data["unanswered_queries"]
                if unanswered:
                    df_un = pd.DataFrame(unanswered)
                    # Parse timestamp for display
                    df_un["created_at"] = pd.to_datetime(df_un["created_at"]).dt.strftime("%Y-%m-%d %H:%M:%S")
                    st.table(df_un)
                else:
                    st.success("🎉 No unanswered or out-of-scope queries recorded yet!")
            else:
                st.error("Failed to load analytics data from API.")
        except Exception as e:
            st.error(f"Failed to connect to backend: {e}")

# ────────────────────────────────────────────────────────────────────────────
# PAGE 3: SYSTEM MANAGEMENT
# ────────────────────────────────────────────────────────────────────────────
elif page == "⚙️ System Management":
    st.title("⚙️ System Management & Ingestion")
    st.markdown("Trigger document ingestion and vector database creation.")
    
    st.info("The application needs to parse the AWS Customer Agreement PDF, generate character chunks, embed them, and index them in a local FAISS database before questions can be asked.")

    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Build/Re-build FAISS Vector Index")
        force_reingest = st.checkbox("Force Re-ingest (overwrite existing index if it exists)")
        
        ingest_clicked = st.button("Trigger Ingestion Engine", use_container_width=True)
        if ingest_clicked:
            if not api_online:
                st.error("Cannot trigger Ingestion Engine: FastAPI backend is offline.")
            else:
                with st.spinner("Processing PDF document... This may take up to a minute..."):
                    try:
                        res = requests.post(
                            f"{BACKEND_URL}/ingest",
                            json={"force": force_reingest},
                            timeout=120
                        )
                        if res.status_code == 200:
                            st.success(f"✅ Ingestion successful! Created {res.json()['chunks_created']} chunks and initialized FAISS index.")
                        elif res.status_code == 409:
                            st.warning("⚠️ Index already exists. Check the 'Force Re-ingest' box and click again to overwrite it.")
                        else:
                            st.error(f"Error: {res.json().get('detail', 'Unknown error occurred')}")
                    except Exception as e:
                        st.error(f"Failed to communicate with ingestion service: {e}")
                        
    with col2:
        st.subheader("Configured Parameters")
        model_used = "Offline"
        if api_online:
            try:
                res = requests.post(f"{BACKEND_URL}/ask", json={"query": "test query"}, timeout=2)
                if res.status_code == 200:
                    model_used = res.json().get("model_used", "Mock Fallback")
                else:
                    model_used = "Mock Fallback"
            except Exception:
                model_used = "Mock Fallback"
            
        st.write(f"**LLM Provider:** `{model_used}`")
        st.write(f"**Embedding Model:** `sentence-transformers/all-MiniLM-L6-v2`")
        st.write(f"**Top K Retrieve:** `4`")
        st.write(f"**Vector Store Path:** `data/faiss_index`")
        st.write(f"**Logs DB Path:** `sqlite:///rag_logs.db`")
