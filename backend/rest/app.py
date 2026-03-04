import streamlit as st
import pandas as pd
import plotly.express as px
import sys
import os
import base64
from datetime import datetime

# Add backend to path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.append(backend_dir)

from graphs.agent_graph import create_graph
from rest.google_services import GmailService
from llm_initiation.LLM_initiate import LLM_initiate

st.set_page_config(page_title="Email Dashboard", page_icon="📊", layout="wide")

# ==============================================================================
# CSS STYLING (Professional Dashboard Theme)
# ==============================================================================
st.markdown("""
<style>
    /* Main Background */
    .stApp {
        background-color: #f4f6f9;
        color: #333;
    }
    
    /* Metrics Cards */
    div[data-testid="metric-container"] {
        background-color: #ffffff;
        border-radius: 10px;
        padding: 15px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        border-left: 5px solid #4a90e2;
        color: #333;
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #ddd;
        box-shadow: 2px 0 5px rgba(0,0,0,0.05);
    }
    
    /* Chat Messages */
    .stChatMessage {
        background-color: #f0f2f6;
        border-radius: 10px;
        border: none;
        padding: 10px;
    }
    
    /* Headers */
    h1, h2, h3 {
        font-family: 'Helvetica Neue', sans-serif;
        color: #2c3e50;
    }
    
    /* Grid Padding */
    .block-container {
        padding-top: 2rem;
    }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# INITIALIZATION & STATE
# ==============================================================================
if "agent" not in st.session_state:
    st.session_state.agent = create_graph()

if "messages" not in st.session_state:
    st.session_state.messages = []

if "email_data" not in st.session_state:
    st.session_state.email_data = None

# ==============================================================================
# DATA FETCHING LOGIC
# ==============================================================================
def load_dashboard_data():
    """Fetches emails, classifies them, and prepares DataFrame."""
    try:
        service = GmailService()
        service.authenticate()
        
        # Fetch last 30 emails for dashboard stats
        raw_emails = service.fetch_emails(max_results=30, q="is:unread")
        
        if not raw_emails:
            return pd.DataFrame()

        # Classify
        llm = LLM_initiate()
        classifications = llm.classify_emails(raw_emails)
        
        # Build Data Structure
        processed_data = []
        for email in raw_emails:
            cat = classifications.get(email["id"], "Personal")
            
            # Simple Date Parsing (Approximation)
            date_str = email.get("date", "")
            try:
                # Try parsing standard email date format
                # Example: "Thu, 30 Jan 2026 10:00:00 +0000"
                # For simplicity in dashboard, we might just look at day/month
                if date_str:
                    dt = datetime.strptime(date_str.split(" +")[0].split(" -")[0].strip(), "%a, %d %b %Y %H:%M:%S")
                    date_display = dt.strftime("%Y-%m-%d")
                else:
                    date_display = datetime.now().strftime("%Y-%m-%d")
            except:
                date_display = datetime.now().strftime("%Y-%m-%d")

            processed_data.append({
                "Subject": email["text"][:50] + "...",
                "Snippet": email["text"],
                "Category": cat,
                "Date": date_display,
                "ID": email["id"]
            })
            
        return pd.DataFrame(processed_data)
    except Exception as e:
        st.error(f"Failed to load dashboard data: {e}")
        return pd.DataFrame()

# Initialize/Refresh Data Button
with st.sidebar:
    st.title("🤖 Assistant")
    if st.button("Refresh Dashboard Data"):
        st.session_state.email_data = load_dashboard_data()
        st.success("Data Refreshed!")

# Load data if empty
if st.session_state.email_data is None:
    with st.spinner("Loading Dashboard Data..."):
        st.session_state.email_data = load_dashboard_data()

df = st.session_state.email_data

# ==============================================================================
# MAIN LAYOUT (DASHBOARD)
# ==============================================================================
st.title("📊 Email Analytics Dashboard")

if not df.empty:
    # --- Row 1: Metrics ---
    col1, col2, col3, col4 = st.columns(4)
    
    total_emails = len(df)
    bank_count = len(df[df["Category"] == "Bank/Finance"])
    promo_count = len(df[df["Category"] == "Promotional"])
    work_count = len(df[df["Category"] == "Work"])

    col1.metric("Total Emails", total_emails, "+2 new")
    col2.metric("Bank & Finance", bank_count, "Important")
    col3.metric("Promotions", promo_count, "Marketing")
    col4.metric("Work / Social", work_count + len(df[df["Category"] == "Social"]))

    # --- Row 2: Charts ---
    c1, c2 = st.columns([1, 1])
    
    with c1:
        st.subheader("Category Distribution")
        fig_pie = px.pie(df, names="Category", hole=0.4, title="Email Categories")
        fig_pie.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig_pie, use_container_width=True)

    with c2:
        st.subheader("Emails Over Time")
        # Group by Date
        daily_counts = df.groupby("Date").size().reset_index(name="Count")
        fig_line = px.line(daily_counts, x="Date", y="Count", markers=True, title="Traffic Trend")
        st.plotly_chart(fig_line, use_container_width=True)

    # --- Row 3: Summaries / List ---
    st.subheader("Recent Email Summaries")
    
    # Simple table view
    st.dataframe(
        df[["Date", "Category", "Snippet"]],
        use_container_width=True,
        hide_index=True
    )
    
else:
    st.info("No data available. Please check your connection or refresh.")

# ==============================================================================
# CHAT SIDEBAR
# ==============================================================================
with st.sidebar:
    st.markdown("---")
    st.subheader("💬 AI Chat Assistant")
    
    # Chat container
    chat_container = st.container(height=400)
    with chat_container:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

    # Chat Input
    if prompt := st.chat_input("Ask about your emails..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with chat_container:
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                status = st.status("Processing...", expanded=True)
                final_state = {}
                try:
                    initial_state = {"query": prompt}
                    # Streaming
                    for event in st.session_state.agent.stream(initial_state):
                        for k, v in event.items():
                            if k != "__end__":
                                status.write(f"Executed: **{k}**")
                                final_state.update(v)
                    
                    status.update(label="Done", state="complete", expanded=False)
                    
                    # Generate Answer from State
                    mode = final_state.get("mode", "unknown")
                    answer = ""
                    if mode == "email":
                         emails = final_state.get("emails", [])
                         answer = f"Found {len(emails)} emails. " + (emails[0].get("summary", "") if emails else "")
                    elif mode == "search":
                         answer = f"Search Results: {final_state.get('search_results','')}"
                    else:
                         answer = final_state.get("chat_response", "Done.")
                    
                    if final_state.get("error"):
                        answer += f"\nError: {final_state['error']}"

                    st.markdown(answer)
                    st.session_state.messages.append({"role": "assistant", "content": answer})
                    
                except Exception as e:
                    st.error(f"Error: {e}")

    # Graph Visualization
    st.markdown("---")
    with st.expander("Workflow Graph"):
        try:
            graph_image = st.session_state.agent.get_graph().draw_mermaid_png()
            st.image(graph_image, use_container_width=True)
        except Exception:
            st.warning("Graph not available")
