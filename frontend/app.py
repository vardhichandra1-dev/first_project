"""
Multi-Account Gmail AI Workflow Agent – Streamlit Dashboard
============================================================
Displays email analytics with 6-category classification,
auto-delete stats, Telegram notification log, and AI chat.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import sys
import os
from datetime import datetime

# ── Path Setup ─────────────────────────────────────────────────────
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
backend_dir  = os.path.join(project_root, "backend")
if backend_dir not in sys.path:
    sys.path.append(backend_dir)

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

from graphs.agent_graph import create_graph
from rest.google_services import GmailService
from llm_initiation.LLM_initiate import LLM_initiate, DELETABLE_CATEGORIES, NOTIFY_CATEGORIES

# ── Page Config ────────────────────────────────────────────────────
st.set_page_config(
    page_title="Gmail AI Agent",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Styling ────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

.stApp {
    background: linear-gradient(135deg, #0d0f1a 0%, #111827 50%, #0d0f1a 100%);
    color: #e0e6f0;
}

/* Metrics */
div[data-testid="metric-container"] {
    background: linear-gradient(135deg, #1a1f35 0%, #1e2540 100%);
    border-radius: 14px;
    padding: 18px;
    border: 1px solid rgba(255,255,255,0.06);
    box-shadow: 0 4px 24px rgba(0,0,0,0.4);
    transition: transform 0.2s ease;
}
div[data-testid="metric-container"]:hover {
    transform: translateY(-2px);
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0f1524 0%, #111827 100%);
    border-right: 1px solid rgba(255,255,255,0.06);
}

/* Chat messages */
.stChatMessage {
    background: rgba(255,255,255,0.04);
    border-radius: 12px;
    border: 1px solid rgba(255,255,255,0.06);
}

/* Section headers */
h1 { 
    background: linear-gradient(90deg, #60a5fa, #a78bfa);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-weight: 700;
}
h2, h3 { color: #cbd5e1; font-weight: 600; }

/* Notification card */
.notif-card {
    background: linear-gradient(135deg, rgba(16,185,129,0.1), rgba(16,185,129,0.05));
    border: 1px solid rgba(16,185,129,0.3);
    border-radius: 10px;
    padding: 10px 14px;
    margin-bottom: 8px;
    font-size: 0.85rem;
}

/* Priority badge */
.badge-otp      { background:#dc2626; color:#fff; padding:2px 8px; border-radius:6px; font-size:0.75rem; }
.badge-banking  { background:#d97706; color:#fff; padding:2px 8px; border-radius:6px; font-size:0.75rem; }
.badge-priority { background:#7c3aed; color:#fff; padding:2px 8px; border-radius:6px; font-size:0.75rem; }
.badge-social   { background:#0284c7; color:#fff; padding:2px 8px; border-radius:6px; font-size:0.75rem; }
.badge-promo    { background:#16a34a; color:#fff; padding:2px 8px; border-radius:6px; font-size:0.75rem; }
.badge-spam     { background:#475569; color:#fff; padding:2px 8px; border-radius:6px; font-size:0.75rem; }

/* Block container */
.block-container { padding-top: 1.5rem; padding-bottom: 2rem; }

/* Buttons */
.stButton > button {
    background: linear-gradient(90deg, #2563eb, #7c3aed);
    color: white;
    border: none;
    border-radius: 8px;
    font-weight: 600;
    transition: opacity 0.2s;
}
.stButton > button:hover { opacity: 0.85; }

/* Dataframe */
.stDataFrame { border-radius: 10px; overflow: hidden; }

/* Divider */
hr { border-color: rgba(255,255,255,0.08); }
</style>
""", unsafe_allow_html=True)

# ── Category Config ─────────────────────────────────────────────────
CATEGORY_COLORS = {
    "OTP":         "#ef4444",
    "Banking":     "#f59e0b",
    "Priority":    "#8b5cf6",
    "Social":      "#3b82f6",
    "Promotional": "#10b981",
    "Spam":        "#64748b",
}
CATEGORY_ICONS = {
    "OTP":         "🔐",
    "Banking":     "🏦",
    "Priority":    "⚡",
    "Social":      "💬",
    "Promotional": "🛍️",
    "Spam":        "🗑️",
}

# ── Session State Init ─────────────────────────────────────────────
for key, default in {
    "agent":           None,
    "messages":        [],
    "email_data":      None,
    "deleted_ids":     [],
    "notified_ids":    [],
    "notification_log": [],
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

if st.session_state.agent is None:
    with st.spinner("🤖 Initialising AI Agent..."):
        st.session_state.agent = create_graph()


# ── Data Helpers ────────────────────────────────────────────────────
def parse_date(date_str: str) -> str:
    if not date_str or date_str == "Unknown":
        return datetime.now().strftime("%Y-%m-%d")
    for fmt in ("%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S"):
        try:
            return datetime.strptime(date_str.strip(), fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    # fallback – strip timezone offset manually
    try:
        clean = date_str.split(" +")[0].split(" -")[0].strip()
        return datetime.strptime(clean, "%a, %d %b %Y %H:%M:%S").strftime("%Y-%m-%d")
    except Exception:
        return datetime.now().strftime("%Y-%m-%d")


def load_dashboard_data():
    """Authenticate, fetch, classify, and return a DataFrame + raw lists."""
    try:
        service = GmailService(account_id="default")
        service.authenticate()
        raw_emails = service.fetch_emails(max_results=30, q="is:unread")
        if not raw_emails:
            return pd.DataFrame(), {}, []

        llm = LLM_initiate()
        categories = llm.classify_emails(raw_emails)

        rows = []
        for email in raw_emails:
            cat   = categories.get(email["id"], "Priority")
            icon  = CATEGORY_ICONS.get(cat, "📧")
            rows.append({
                "ID":       email["id"],
                "Date":     parse_date(email.get("date", "")),
                "Category": cat,
                "Icon":     icon,
                "Subject":  email.get("subject", "No Subject"),
                "Sender":   email.get("sender", "Unknown"),
                "Snippet":  email.get("text", ""),
            })

        return pd.DataFrame(rows), categories, raw_emails

    except Exception as e:
        st.error(f"❌ Failed to load data: {e}")
        return pd.DataFrame(), {}, []


# ── Sidebar ─────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🤖 Gmail AI Agent")
    st.caption("Powered by Groq · LangGraph · Gmail API")
    st.markdown("---")

    # Refresh button
    if st.button("🔄 Refresh Inbox", use_container_width=True):
        with st.spinner("Fetching emails..."):
            df, cats, raw = load_dashboard_data()
            st.session_state.email_data = (df, cats, raw)
        st.success("✅ Refreshed!")

    # Status info
    telegram_ok = bool(
        os.getenv("TELEGRAM_BOT_TOKEN") and os.getenv("TELEGRAM_CHAT_ID")
    )
    st.markdown("---")
    st.markdown("**⚙️ System Status**")
    st.markdown(f"{'🟢' if telegram_ok else '🟡'} Telegram Notifications "
                f"{'Active' if telegram_ok else 'Not configured'}")
    st.markdown("🟢 Groq LLM Active")
    st.markdown("🟢 Gmail API Ready")

    st.markdown("---")
    # Session deletion stats
    if st.session_state.deleted_ids:
        st.markdown(f"**🗑️ Auto-deleted this session:** `{len(st.session_state.deleted_ids)}` emails")
    if st.session_state.notified_ids:
        st.markdown(f"**📲 Notifications sent:** `{len(st.session_state.notified_ids)}`")

    st.markdown("---")
    st.markdown("**ℹ️ Category Legend**")
    for cat, icon in CATEGORY_ICONS.items():
        action = ("🗑️ Auto-deleted" if cat in DELETABLE_CATEGORIES
                  else "📲 Notified" if cat in NOTIFY_CATEGORIES
                  else "👁️ Monitored")
        st.caption(f"{icon} **{cat}** – {action}")


# ── Load data on first run ──────────────────────────────────────────
if st.session_state.email_data is None:
    with st.spinner("📬 Loading inbox data..."):
        df, cats, raw = load_dashboard_data()
        st.session_state.email_data = (df, cats, raw)

df, cats, raw = st.session_state.email_data
if isinstance(df, tuple):   # safety guard
    df, cats, raw = df

# ── Main Dashboard ──────────────────────────────────────────────────
st.title("📊 Gmail AI Workflow Dashboard")
st.caption(f"Last updated: {datetime.now().strftime('%d %b %Y, %H:%M:%S')}")
st.markdown("---")

if not df.empty:
    # ── Row 1: Metric Cards ─────────────────────────────────────────
    m_cols = st.columns(6)
    for i, (cat, icon) in enumerate(CATEGORY_ICONS.items()):
        count = len(df[df["Category"] == cat])
        m_cols[i].metric(label=f"{icon} {cat}", value=count)

    st.markdown("---")

    # ── Row 2: Charts ───────────────────────────────────────────────
    c1, c2 = st.columns([1, 1])

    with c1:
        st.subheader("📈 Category Distribution")
        fig_pie = px.pie(
            df, names="Category",
            color="Category",
            color_discrete_map=CATEGORY_COLORS,
            hole=0.45,
        )
        fig_pie.update_traces(textposition="inside", textinfo="percent+label")
        fig_pie.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color="#cbd5e1",
            showlegend=False,
            margin=dict(t=20, b=20, l=20, r=20),
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    with c2:
        st.subheader("📅 Emails Over Time")
        daily = df.groupby(["Date", "Category"]).size().reset_index(name="Count")
        fig_bar = px.bar(
            daily, x="Date", y="Count",
            color="Category",
            color_discrete_map=CATEGORY_COLORS,
            barmode="stack",
        )
        fig_bar.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color="#cbd5e1",
            xaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
            yaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
            margin=dict(t=40, b=20, l=20, r=20),
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    st.markdown("---")

    # ── Row 3: Priority / Banking / OTP Highlight ───────────────────
    important = df[df["Category"].isin({"OTP", "Banking", "Priority"})]
    if not important.empty:
        st.subheader("🚨 Important Emails (OTP · Banking · Priority)")
        for _, row in important.iterrows():
            icon  = CATEGORY_ICONS.get(row["Category"], "📧")
            color = CATEGORY_COLORS.get(row["Category"], "#fff")
            st.markdown(
                f"""<div style="background:rgba(255,255,255,0.04);border-left:4px solid {color};
                border-radius:8px;padding:10px 14px;margin-bottom:8px;">
                <b>{icon} [{row['Category']}]</b> &nbsp; {row['Subject']}<br>
                <small style="color:#94a3b8;">👤 {row['Sender']} &nbsp;|&nbsp; 📅 {row['Date']}</small><br>
                <small>{row['Snippet'][:120]}…</small></div>""",
                unsafe_allow_html=True,
            )
        st.markdown("---")

    # ── Row 4: Full Email Table ─────────────────────────────────────
    st.subheader("📋 All Emails")
    filter_cat = st.multiselect(
        "Filter by category:",
        options=list(CATEGORY_ICONS.keys()),
        default=list(CATEGORY_ICONS.keys()),
    )
    filtered_df = df[df["Category"].isin(filter_cat)]
    st.dataframe(
        filtered_df[["Date", "Icon", "Category", "Subject", "Sender", "Snippet"]].rename(
            columns={"Icon": ""}
        ),
        use_container_width=True,
        hide_index=True,
    )

    # ── Row 5: Notification Log ─────────────────────────────────────
    if st.session_state.notification_log:
        st.markdown("---")
        st.subheader("📲 Telegram Notification Log")
        for entry in st.session_state.notification_log:
            # Strip HTML tags for display
            import re
            clean = re.sub(r"<[^>]+>", "", entry)
            st.markdown(
                f'<div class="notif-card">✅ {clean}</div>',
                unsafe_allow_html=True,
            )

else:
    st.info("📭 No emails found. Click **Refresh Inbox** in the sidebar to load your inbox.")

# ── Chat Sidebar ─────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("---")
    st.subheader("💬 AI Chat Assistant")
    st.caption("Ask about emails, search the web, or just chat.")

    chat_container = st.container(height=380)
    with chat_container:
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

    if prompt := st.chat_input("e.g. Fetch my last 5 unread emails…"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with chat_container:
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                status_box = st.status("🤖 Processing…", expanded=True)
                final_state = {}
                try:
                    initial_state = {
                        "query": prompt,
                        "emails": [],
                        "categories": {},
                        "deleted_ids": [],
                        "notified_ids": [],
                        "notification_log": [],
                    }
                    step_icons = {
                        "router":          "🔀 Routing",
                        "authenticate":    "🔑 Authenticating",
                        "fetch_emails":    "📬 Fetching Emails",
                        "classify":        "🏷️ Classifying",
                        "delete":          "🗑️ Auto-deleting",
                        "notify":          "📲 Notifying",
                        "summarize_emails":"📝 Summarising",
                        "search":          "🔍 Searching",
                        "chat":            "💬 Thinking",
                    }
                    for event in st.session_state.agent.stream(initial_state):
                        for k, v in event.items():
                            if k != "__end__":
                                label = step_icons.get(k, f"⚙️ {k}")
                                status_box.write(f"**{label}**")
                                final_state.update(v)

                    status_box.update(label="✅ Done", state="complete", expanded=False)

                    # Persist session-level stats
                    if final_state.get("deleted_ids"):
                        st.session_state.deleted_ids.extend(final_state["deleted_ids"])
                    if final_state.get("notified_ids"):
                        st.session_state.notified_ids.extend(final_state["notified_ids"])
                    if final_state.get("notification_log"):
                        st.session_state.notification_log.extend(final_state["notification_log"])

                    # Compose assistant answer
                    mode   = final_state.get("mode", "chat")
                    answer = ""

                    if mode == "email":
                        emails     = final_state.get("emails", [])
                        categories = final_state.get("categories", {})
                        deleted    = final_state.get("deleted_ids", [])
                        notified   = final_state.get("notified_ids", [])

                        answer = f"**📬 Found {len(emails)} emails**\n\n"
                        answer += f"- 🗑️ Auto-deleted: **{len(deleted)}** (Promotional/Spam)\n"
                        answer += f"- 📲 Notified via Telegram: **{len(notified)}** (OTP/Banking/Priority)\n\n"

                        for email in emails[:5]:
                            eid  = email.get("id")
                            cat  = categories.get(eid, "Unknown")
                            icon = CATEGORY_ICONS.get(cat, "📧")
                            summ = email.get("summary", "")
                            answer += (
                                f"**{icon} [{cat}]** {email.get('subject','No Subject')}\n"
                                f"> {summ[:180]}\n\n"
                            )

                        if final_state.get("error"):
                            answer += f"\n⚠️ Error: {final_state['error']}"

                        # Refresh dashboard data
                        with st.spinner("Refreshing dashboard…"):
                            df_new, cats_new, raw_new = load_dashboard_data()
                            st.session_state.email_data = (df_new, cats_new, raw_new)

                    elif mode == "search":
                        answer = f"**🔍 Search Results:**\n\n{final_state.get('search_results', 'No results.')}"
                    else:
                        answer = final_state.get("chat_response", "Sorry, I couldn't process that.")

                    st.markdown(answer)
                    st.session_state.messages.append({"role": "assistant", "content": answer})

                except Exception as e:
                    st.error(f"❌ Error: {e}")
                    status_box.update(label="❌ Failed", state="error")

    # ── Workflow Graph Visualisation ────────────────────────────────
    st.markdown("---")
    with st.expander("🔗 View Agent Workflow"):
        try:
            graph_img = st.session_state.agent.get_graph().draw_mermaid_png()
            st.image(graph_img, use_container_width=True)
        except Exception:
            st.markdown("""
**Workflow:**
```
router  →  authenticate  →  fetch_emails
        →  classify       →  delete
        →  notify         →  summarize  →  END

router  →  search  →  END
router  →  chat    →  END
```
""")
