"""
Multi-Account Gmail AI Workflow Agent – Streamlit Dashboard (Cache-Aware)
=========================================================================
Reads from local JSON cache by default.
"Update Emails" button triggers a fresh Gmail API pull, merge, and save.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import sys
import os
import re
from datetime import datetime

# ── Path Setup ──────────────────────────────────────────────────────
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
backend_dir  = os.path.join(project_root, "backend")
if backend_dir not in sys.path:
    sys.path.append(backend_dir)

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

from graphs.agent_graph import create_graph
from rest.google_services import GmailService
from rest.email_cache import EmailCache, CACHE_DAYS
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
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

.stApp {
    background: linear-gradient(135deg, #0d0f1a 0%, #111827 50%, #0d0f1a 100%);
    color: #e0e6f0;
}
div[data-testid="metric-container"] {
    background: linear-gradient(135deg, #1a1f35 0%, #1e2540 100%);
    border-radius: 14px; padding: 18px;
    border: 1px solid rgba(255,255,255,0.06);
    box-shadow: 0 4px 24px rgba(0,0,0,0.4);
    transition: transform 0.2s;
}
div[data-testid="metric-container"]:hover { transform: translateY(-2px); }
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0f1524 0%, #111827 100%);
    border-right: 1px solid rgba(255,255,255,0.06);
}
.stChatMessage {
    background: rgba(255,255,255,0.04); border-radius:12px;
    border:1px solid rgba(255,255,255,0.06);
}
h1 {
    background: linear-gradient(90deg,#60a5fa,#a78bfa);
    -webkit-background-clip:text; -webkit-text-fill-color:transparent; font-weight:700;
}
h2,h3 { color:#cbd5e1; font-weight:600; }
.cache-badge {
    display:inline-block; padding:3px 10px; border-radius:20px;
    font-size:0.78rem; font-weight:600; margin-bottom:8px;
}
.cache-hit  { background:rgba(16,185,129,0.15); color:#10b981; border:1px solid rgba(16,185,129,0.3); }
.cache-miss { background:rgba(59,130,246,0.15); color:#3b82f6; border:1px solid rgba(59,130,246,0.3); }
.email-card {
    background:rgba(255,255,255,0.03); border-radius:10px;
    border-left:4px solid; padding:10px 14px; margin-bottom:8px;
}
.notif-card {
    background:rgba(16,185,129,0.08); border:1px solid rgba(16,185,129,0.25);
    border-radius:8px; padding:8px 12px; margin-bottom:6px; font-size:0.82rem;
}
.block-container { padding-top:1.5rem; padding-bottom:2rem; }
.stButton>button {
    background:linear-gradient(90deg,#2563eb,#7c3aed); color:white;
    border:none; border-radius:8px; font-weight:600; transition:opacity 0.2s;
}
.stButton>button:hover { opacity:0.85; }
hr { border-color:rgba(255,255,255,0.08); }
</style>
""", unsafe_allow_html=True)

# ── Category Config ─────────────────────────────────────────────────
CATEGORY_COLORS = {
    "OTP":         "#ef4444", "Banking":     "#f59e0b",
    "Priority":    "#8b5cf6", "Social":      "#3b82f6",
    "Promotional": "#10b981", "Spam":        "#64748b",
}
CATEGORY_ICONS = {
    "OTP":"🔐", "Banking":"🏦", "Priority":"⚡",
    "Social":"💬", "Promotional":"🛍️", "Spam":"🗑️",
}

# ── Session State Init ─────────────────────────────────────────────
DEFAULTS = {
    "agent":           None,
    "messages":        [],
    "df":              None,
    "deleted_ids":     [],
    "notified_ids":    [],
    "notification_log": [],
}
for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

if st.session_state.agent is None:
    with st.spinner("🤖 Initialising AI Agent…"):
        st.session_state.agent = create_graph()


# ── Cache helpers ───────────────────────────────────────────────────
def emails_to_df(emails: list) -> pd.DataFrame:
    """Convert list of cache email dicts to a display DataFrame."""
    rows = []
    for e in emails:
        cat  = e.get("category") or "Unknown"
        date_raw = e.get("date_iso", "")[:10] if e.get("date_iso") else "N/A"
        rows.append({
            "ID":              e.get("id", ""),
            "Date":            date_raw,
            "Category":        cat,
            "Icon":            CATEGORY_ICONS.get(cat, "📧"),
            "Subject":         e.get("subject", "No Subject"),
            "Sender":          e.get("sender_email", e.get("sender", "Unknown")),
            "Snippet":         e.get("snippet", "")[:120],
            "Has Attachments": "📎" if e.get("has_attachments") else "",
            "Body Preview":    (e.get("body") or "")[:200],
        })
    return pd.DataFrame(rows)


def do_fresh_update():
    """Force a Gmail API pull → merge → cache → classify → return df."""
    with st.spinner(f"📬 Fetching last {CACHE_DAYS} days from Gmail…"):
        try:
            svc = GmailService(account_id="default")
            svc.authenticate()
            fresh = svc.fetch_last_n_days(days=CACHE_DAYS, max_results=200)

            cache  = EmailCache()
            merged = cache.merge(fresh)
            cache.save(merged)

        except Exception as e:
            st.error(f"❌ Gmail fetch failed: {e}")
            merged = EmailCache().load()

    with st.spinner("🏷️ Classifying emails…"):
        try:
            unclassified = [e for e in merged if not e.get("category")]
            if unclassified:
                llm  = LLM_initiate()
                cats = llm.classify_emails(unclassified)
                cache = EmailCache()
                cache.update_categories(cats)
                for e in merged:
                    if e["id"] in cats:
                        e["category"] = cats[e["id"]]
        except Exception as e:
            st.warning(f"⚠️ Classification partial: {e}")

    return emails_to_df(merged)


def load_from_cache() -> pd.DataFrame:
    """Load email cache, classify uncategorised ones."""
    cache  = EmailCache()
    emails = cache.load()
    if not emails:
        return pd.DataFrame()

    unclassified = [e for e in emails if not e.get("category")]
    if unclassified:
        try:
            llm  = LLM_initiate()
            cats = llm.classify_emails(unclassified)
            cache.update_categories(cats)
            for e in emails:
                if e["id"] in cats:
                    e["category"] = cats[e["id"]]
        except Exception as ex:
            st.warning(f"⚠️ Classification error: {ex}")

    return emails_to_df(emails)


# ── Sidebar ─────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🤖 Gmail AI Agent")
    st.caption("Powered by Groq · LangGraph · Gmail API")
    st.markdown("---")

    # Cache stats
    cache        = EmailCache()
    stats        = cache.cache_stats()
    stale        = cache.is_stale()
    status_icon  = "🟡" if stale else "🟢"

    st.markdown("**📂 Local Email Cache**")
    st.caption(f"📊 Total: **{stats['total']}** emails")
    st.caption(f"📅 Range: {stats['date_range']}")
    st.caption(f"🕐 Updated: {stats['last_updated']}")
    st.caption(f"{status_icon} Cache {'stale – consider refreshing' if stale else 'up to date'}")

    st.markdown("")
    if st.button("🔄 Update Emails from Gmail", use_container_width=True):
        st.session_state.df = do_fresh_update()
        st.success(f"✅ Updated! {len(st.session_state.df)} emails cached.")
        st.rerun()

    st.markdown("---")
    # System status
    telegram_ok = bool(os.getenv("TELEGRAM_BOT_TOKEN") and os.getenv("TELEGRAM_CHAT_ID"))
    st.markdown("**⚙️ System Status**")
    st.caption(f"{'🟢' if telegram_ok else '🟡'} Telegram {'Active' if telegram_ok else 'Not configured'}")
    st.caption("🟢 Groq LLM Active")
    st.caption("🟢 Gmail API Ready")

    st.markdown("---")
    if st.session_state.deleted_ids:
        st.caption(f"🗑️ Auto-deleted this session: **{len(st.session_state.deleted_ids)}**")
    if st.session_state.notified_ids:
        st.caption(f"📲 Notifications sent: **{len(st.session_state.notified_ids)}**")

    st.markdown("---")
    st.markdown("**ℹ️ Category Legend**")
    for cat, icon in CATEGORY_ICONS.items():
        action = ("🗑️ Auto-deleted" if cat in DELETABLE_CATEGORIES
                  else "📲 Notified"   if cat in NOTIFY_CATEGORIES
                  else "👁️ Monitored")
        st.caption(f"{icon} **{cat}** – {action}")


# ── Load data if not in session ─────────────────────────────────────
if st.session_state.df is None:
    c = EmailCache()
    if c.is_stale() or not c.load():
        st.info(f"📭 No local cache found. Click **Update Emails from Gmail** to fetch the last {CACHE_DAYS} days.")
        st.session_state.df = pd.DataFrame()
    else:
        with st.spinner("📂 Loading from local cache…"):
            st.session_state.df = load_from_cache()

df = st.session_state.df

# ── Main Dashboard ──────────────────────────────────────────────────
st.title("📊 Gmail AI Workflow Dashboard")
col_title, col_badge = st.columns([4, 1])
with col_title:
    st.caption(f"Showing last {CACHE_DAYS} days · {stats['last_updated']}")
with col_badge:
    source = "📂 From Cache" if not stale else "⚠️ Stale Cache"
    badge  = "cache-hit" if not stale else "cache-miss"
    st.markdown(f'<span class="cache-badge {badge}">{source}</span>', unsafe_allow_html=True)

st.markdown("---")

if df is not None and not df.empty:
    # ── Metrics Row ─────────────────────────────────────────────────
    m_cols = st.columns(6)
    for i, (cat, icon) in enumerate(CATEGORY_ICONS.items()):
        count = len(df[df["Category"] == cat])
        m_cols[i].metric(label=f"{icon} {cat}", value=count)

    st.markdown("---")

    # ── Charts ──────────────────────────────────────────────────────
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("📈 Category Distribution")
        fig_pie = px.pie(
            df, names="Category",
            color="Category", color_discrete_map=CATEGORY_COLORS,
            hole=0.45,
        )
        fig_pie.update_traces(textposition="inside", textinfo="percent+label")
        fig_pie.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font_color="#cbd5e1", showlegend=False,
            margin=dict(t=20, b=20, l=20, r=20),
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    with c2:
        st.subheader("📅 Emails Over Time")
        daily = df.groupby(["Date","Category"]).size().reset_index(name="Count")
        fig_bar = px.bar(
            daily, x="Date", y="Count",
            color="Category", color_discrete_map=CATEGORY_COLORS,
            barmode="stack",
        )
        fig_bar.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font_color="#cbd5e1",
            xaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
            yaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
            margin=dict(t=40, b=20, l=20, r=20),
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    st.markdown("---")

    # ── Important Email Highlights ──────────────────────────────────
    important = df[df["Category"].isin({"OTP", "Banking", "Priority"})]
    if not important.empty:
        st.subheader("🚨 Important Emails  (OTP · Banking · Priority)")
        for _, row in important.head(10).iterrows():
            color = CATEGORY_COLORS.get(row["Category"], "#fff")
            icon  = CATEGORY_ICONS.get(row["Category"], "📧")
            att   = row.get("Has Attachments", "")
            st.markdown(
                f"""<div class="email-card" style="border-color:{color}">
                <b>{icon} [{row['Category']}]</b> &nbsp; {row['Subject']} {att}<br>
                <small style="color:#94a3b8;">👤 {row['Sender']} &nbsp;|&nbsp; 📅 {row['Date']}</small><br>
                <small style="color:#cbd5e1;">{row['Snippet']}</small>
                </div>""",
                unsafe_allow_html=True,
            )
        st.markdown("---")

    # ── Full Table with filters ─────────────────────────────────────
    st.subheader("📋 All Emails")
    filter_cat = st.multiselect(
        "Filter by category:",
        options=list(CATEGORY_ICONS.keys()),
        default=list(CATEGORY_ICONS.keys()),
    )
    show_att_only = st.checkbox("Show only emails with attachments")
    filtered = df[df["Category"].isin(filter_cat)]
    if show_att_only:
        filtered = filtered[filtered["Has Attachments"] == "📎"]

    display_cols = ["Date", "Icon", "Category", "Subject", "Sender", "Snippet", "Has Attachments"]
    st.dataframe(
        filtered[display_cols].rename(columns={"Icon": "", "Has Attachments": "📎"}),
        use_container_width=True, hide_index=True,
    )

    # ── Email detail expander ────────────────────────────────────────
    st.markdown("---")
    st.subheader("🔍 Email Body Viewer")
    if not filtered.empty:
        subject_list  = filtered["Subject"].tolist()
        selected_subj = st.selectbox("Select an email to view full body:", subject_list)
        selected_row  = filtered[filtered["Subject"] == selected_subj].iloc[0]
        st.markdown(f"**From:** {selected_row['Sender']}")
        st.markdown(f"**Date:** {selected_row['Date']}")
        st.markdown(f"**Category:** {selected_row['Icon']} {selected_row['Category']}")
        st.text_area("Body Preview", value=selected_row.get("Body Preview", ""), height=180, disabled=True)

    # ── Notification Log ────────────────────────────────────────────
    if st.session_state.notification_log:
        st.markdown("---")
        st.subheader("📲 Telegram Notification Log")
        for entry in st.session_state.notification_log:
            clean = re.sub(r"<[^>]+>", "", str(entry))
            st.markdown(f'<div class="notif-card">✅ {clean}</div>', unsafe_allow_html=True)

else:
    st.info(f"📭 No emails in cache. Click **🔄 Update Emails from Gmail** in the sidebar to fetch the last {CACHE_DAYS} days of emails.")


# ── Chat Sidebar ─────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("---")
    st.subheader("💬 AI Chat Assistant")
    st.caption("Ask about emails, search the web, or just chat.\n"
               "Say *'update emails'* to trigger a fresh Gmail sync.")

    chat_container = st.container(height=380)
    with chat_container:
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

    if prompt := st.chat_input("e.g. Show my banking emails…"):
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
                        "force_refresh": False,
                        "from_cache": False,
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
                                status_box.write(f"**{step_icons.get(k, k)}**")
                                final_state.update(v)

                    status_box.update(label="✅ Done", state="complete", expanded=False)

                    # Persist stats
                    if final_state.get("deleted_ids"):
                        st.session_state.deleted_ids.extend(final_state["deleted_ids"])
                    if final_state.get("notified_ids"):
                        st.session_state.notified_ids.extend(final_state["notified_ids"])
                    if final_state.get("notification_log"):
                        st.session_state.notification_log.extend(final_state["notification_log"])

                    mode       = final_state.get("mode", "chat")
                    from_cache = final_state.get("from_cache", False)
                    answer     = ""

                    if mode == "email":
                        emails     = final_state.get("emails", [])
                        categories = final_state.get("categories", {})
                        deleted    = final_state.get("deleted_ids", [])
                        notified   = final_state.get("notified_ids", [])
                        src        = "📂 local cache" if from_cache else "📡 Gmail API"

                        answer = ""
                        if final_state.get("chat_response"):
                            answer += f"🤖 **AI Insights:**\n{final_state['chat_response']}\n\n---\n\n"

                        answer += f"**📬 Loaded {len(emails)} emails from {src}**\n\n"
                        answer += f"- 🗑️ Auto-deleted: **{len(deleted)}** (Promotional/Spam)\n"
                        answer += f"- 📲 Notified via Telegram: **{len(notified)}** (OTP/Banking/Priority)\n\n"

                        for email in emails[:5]:
                            eid  = email.get("id")
                            cat  = categories.get(eid) or email.get("category", "Unknown")
                            icon = CATEGORY_ICONS.get(cat, "📧")
                            att  = "📎 " if email.get("has_attachments") else ""
                            summ = email.get("summary", email.get("snippet", ""))[:200]
                            answer += (
                                f"**{icon} [{cat}]** {att}{email.get('subject','No Subject')}\n"
                                f"> 👤 {email.get('sender_email', '')} · {email.get('date_iso','')[:10]}\n"
                                f"> {summ}\n\n"
                            )
                        if final_state.get("error"):
                            answer += f"\n⚠️ {final_state['error']}"

                        # Refresh the dashboard df
                        st.session_state.df = emails_to_df(emails)

                    elif mode == "search":
                        answer = f"**🔍 Results:**\n\n{final_state.get('search_results', 'No results.')}"
                    else:
                        answer = final_state.get("chat_response", "Sorry, couldn't process that.")

                    st.markdown(answer)
                    st.session_state.messages.append({"role": "assistant", "content": answer})

                except Exception as e:
                    st.error(f"❌ Error: {e}")
                    status_box.update(label="❌ Failed", state="error")

    # ── Workflow Graph ──────────────────────────────────────────────
    st.markdown("---")
    with st.expander("🔗 View Agent Workflow"):
        try:
            st.image(st.session_state.agent.get_graph().draw_mermaid_png(),
                     use_container_width=True)
        except Exception:
            st.code(
                "router → authenticate → fetch_emails → classify → delete → notify → summarize\n"
                "router → search → END\n"
                "router → chat   → END"
            )
