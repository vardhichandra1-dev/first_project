# 🤖 Gmail AI Workflow Agent

An **agentic automation system** that classifies and manages Gmail emails using LLM-driven categorization, stores them locally in JSON, auto-deletes non-critical emails, and delivers real-time alerts via **Telegram**.

Built with **Python · LangGraph · Groq API · Gmail API · Telegram Bot API · Streamlit**

---

## ✨ Features

| Feature | Details |
|---|---|
| 📂 **Local Email Cache** | Fetches last 3 days of emails once, stores as `data/email_cache.json` – no repeated API calls |
| 🏷️ **LLM Classification** | Classifies every email: OTP · Banking · Promotional · Priority · Social · Spam |
| 🗑️ **Auto-Deletion** | Promotional & Spam emails auto-moved to Trash |
| 📲 **Telegram Notifications** | Real-time alerts for OTP, Banking, and Priority emails |
| 🔀 **Intent Routing** | Detects whether your chat query is about Email, Web Search, or Chat |
| 📊 **Analytics Dashboard** | 6-category metrics, stacked bar chart, important-email highlights, body viewer |
| 💬 **AI Chat Assistant** | Conversational sidebar powered by Groq (`llama-3.3-70b-versatile`) |
| 🔍 **Web Search** | Real-time search via Tavily for factual/news queries |

---

## 🗂️ Project Structure

```
Email_Assistant_agent/
│
├── backend/
│   ├── graphs/
│   │   └── agent_graph.py          # LangGraph workflow (router → fetch → classify → delete → notify → summarize)
│   │
│   ├── llm_initiation/
│   │   └── LLM_initiate.py         # Groq LLM – intent routing, 6-category classification, summarization
│   │
│   ├── nodes/
│   │   ├── nodes.py                # Core nodes: router, auth, fetch (cache-aware), summarize, search, chat
│   │   ├── classify_node.py        # LLM email classification + cache write-back
│   │   ├── delete_node.py          # Auto-trash Promotional/Spam
│   │   └── notify_node.py          # Telegram alerts for OTP/Banking/Priority
│   │
│   ├── rest/
│   │   ├── google_services.py      # Gmail API wrapper (fetch full body + attachments, delete)
│   │   ├── email_cache.py          # Local JSON cache manager (load/save/merge/stale-check)
│   │   ├── notifier.py             # Telegram Bot notification service
│   │   └── debug_cli.py            # CLI tool for backend debugging
│   │
│   └── state/
│       └── state.py                # LangGraph AgentState definition
│
├── frontend/
│   └── app.py                      # Streamlit dashboard (main entry point)
│
├── data/
│   └── email_cache.json            # Local email store (auto-created on first update)
│
├── credentials.json                # Google OAuth client secrets (required)
├── token.pkl                       # Saved auth token (auto-generated on first run)
├── .env                            # Environment variables
├── requirements.txt                # Python dependencies
└── README.md
```

---

## 🔄 Agent Workflow

```
User Query
    │
    ▼
 router ──────────────────────────────────────┐
    │                                         │
  email                               search / chat
    │                                         │
 authenticate (if fresh fetch needed)    search / chat node
    │                                         │
 fetch_emails ──► local cache (default)       END
              └─► Gmail API (if stale / "update" keyword)
    │
 classify  ──► LLM (6 categories) + writes back to cache
    │
 delete    ──► Trash: Promotional, Spam
    │
 notify    ──► Telegram: OTP, Banking, Priority
    │
 summarize ──► LLM summary for important emails
    │
   END
```

---

## � Email Cache

Emails are fetched **once** for the last 3 days and stored locally. Subsequent loads read from cache with no API calls.

**Cache file:** `data/email_cache.json`

Each stored email record:
```json
{
  "id":             "...",
  "subject":        "Your OTP is 123456",
  "sender":         "noreply@bank.com",
  "sender_email":   "noreply@bank.com",
  "date_iso":       "2026-03-06T10:00:00+05:30",
  "timestamp_unix": 1741234567,
  "snippet":        "Your account was debited...",
  "body":           "Full plain-text email body...",
  "has_attachments": true,
  "attachments": [
    { "name": "statement.pdf", "mime_type": "application/pdf", "size_bytes": 45230 }
  ],
  "labels":         ["INBOX", "UNREAD"],
  "category":       "Banking",
  "cached_at":      "2026-03-06T11:00:00+00:00"
}
```

**Refresh cache:**
- Click **🔄 Update Emails from Gmail** in the sidebar, OR
- Say *"update emails"* / *"refresh"* / *"sync"* in the chat

---

## �📧 Email Categories & Actions

| Category | Icon | Action |
|---|---|---|
| OTP | 🔐 | 📲 Telegram alert |
| Banking | 🏦 | 📲 Telegram alert |
| Priority | ⚡ | 📲 Telegram alert |
| Social | 💬 | 👁️ Monitored only |
| Promotional | 🛍️ | 🗑️ Auto-deleted (Trash) |
| Spam | 🗑️ | 🗑️ Auto-deleted (Trash) |

---

## ⚙️ Setup & Installation

### 1. Prerequisites
- Python 3.10+
- Gmail API enabled in Google Cloud Console
- `credentials.json` (OAuth 2.0 Desktop App) in the project root
- [Groq API Key](https://console.groq.com) (free)
- *(Optional)* Telegram Bot Token for notifications

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure `.env`
```ini
GROQ_API_KEY=your_groq_api_key
TAVILY_API_KEY=your_tavily_api_key

# Optional – leave blank to disable Telegram
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id
```

> **Get Telegram credentials:**
> - Token: Message [@BotFather](https://t.me/BotFather) → `/newbot`
> - Chat ID: Message [@userinfobot](https://t.me/userinfobot)

### 4. Run the Application
```bash
streamlit run frontend/app.py
```

### 5. First Run
1. A browser window opens for Google OAuth authentication.  
2. After approval, `token.pkl` is saved for future runs.  
3. Click **🔄 Update Emails from Gmail** in the sidebar to populate the local cache.

---

## 🛠️ Tech Stack

| Tool | Purpose |
|---|---|
| **LangGraph** | Stateful agent workflow orchestration |
| **Groq** (`llama-3.3-70b-versatile`) | Email classification, summarization, intent routing |
| **Gmail API** | Email fetching (full body + attachments), auto-deletion |
| **Telegram Bot API** | Real-time push notifications |
| **Tavily** | Web search capability |
| **Streamlit** | Analytics dashboard & chat UI |
| **Plotly** | Charts and visualizations |

---

## 🐛 Debugging

To test the backend without the UI:
```bash
python backend/rest/debug_cli.py
```

To inspect the local cache directly:
```bash
python -c "
import sys; sys.path.insert(0,'backend')
from rest.email_cache import EmailCache
c = EmailCache()
print(c.cache_stats())
"
```
