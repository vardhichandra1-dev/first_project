# 🤖 Gmail AI Workflow Agent

An **agentic automation system** that classifies and manages Gmail emails using LLM-driven categorization, auto-deletes non-critical emails, and delivers real-time alerts for important emails via **Telegram**.

Built with **Python · LangGraph · Groq API · Gmail API · Telegram Bot API · Streamlit**

---

## ✨ Features

| Feature | Details |
|---|---|
| 🏷️ **LLM Email Classification** | Classifies every email into: OTP, Banking, Promotional, Priority, Social, Spam |
| 🗑️ **Auto-Deletion** | Promotional & Spam emails are automatically moved to Trash |
| 📲 **Telegram Notifications** | Real-time alerts for OTP, Banking, and Priority emails |
| 🔀 **Intent-Based Routing** | Detects whether your query is about Email, Web Search, or Chat |
| 📊 **Analytics Dashboard** | 6-category metrics, stacked bar chart, and important-email highlights |
| 💬 **AI Chat Assistant** | Conversational sidebar powered by Groq (llama-3.3-70b-versatile) |
| 🔍 **Web Search** | Real-time search via Tavily for factual/news queries |

---

## 🗂️ Project Structure

```
Email_Assistant_agent/
├── backend/
│   ├── graphs/
│   │   └── agent_graph.py          # LangGraph workflow definition
│   ├── llm_initiation/
│   │   └── LLM_initiate.py         # Groq LLM – routing, classification, summarization
│   ├── nodes/
│   │   ├── nodes.py                # Core nodes: router, auth, fetch, summarize, search, chat
│   │   ├── classify_node.py        # LLM email classification node
│   │   ├── delete_node.py          # Auto-delete Promotional/Spam node
│   │   └── notify_node.py          # Telegram alert node for OTP/Banking/Priority
│   ├── rest/
│   │   ├── google_services.py      # Gmail API wrapper (fetch, delete, subjects)
│   │   ├── notifier.py             # Telegram Bot notification service
│   │   └── debug_cli.py            # CLI tool for backend debugging
│   └── state/
│       └── state.py                # LangGraph AgentState definition
├── frontend/
│   └── app.py                      # Streamlit dashboard (main entry point)
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
 router ──────────────────────────────────┐
    │                                     │
  email                            search / chat
    │                                     │
    ▼                                     ▼
 authenticate                        search / chat node
    │                                     │
 fetch_emails                            END
    │
 classify  ◄─── LLM (6 categories)
    │
 delete    ◄─── Trash: Promotional, Spam
    │
 notify    ◄─── Telegram: OTP, Banking, Priority
    │
 summarize ◄─── LLM summary for important emails
    │
   END
```

---

## 📧 Email Categories & Actions

| Category | Icon | Automatic Action |
|---|---|---|
| OTP | 🔐 | 📲 Telegram alert |
| Banking | 🏦 | 📲 Telegram alert |
| Priority | ⚡ | 📲 Telegram alert |
| Social | 💬 | 👁️ Monitored only |
| Promotional | 🛍️ | 🗑️ Auto-deleted |
| Spam | 🗑️ | 🗑️ Auto-deleted |

---

## ⚙️ Setup & Installation

### 1. Prerequisites
- Python 3.10+
- A **Google Cloud Project** with the Gmail API enabled
- `credentials.json` downloaded from Google Cloud Console (OAuth 2.0 Desktop App)
- A **Groq API Key** (free at [console.groq.com](https://console.groq.com))
- *(Optional)* A **Telegram Bot Token** for notifications

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Create / update `.env` in the project root:
```ini
GROQ_API_KEY=your_groq_api_key
TAVILY_API_KEY=your_tavily_api_key

# Optional – leave blank to disable Telegram notifications
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id
```

> **Get Telegram credentials:**
> - Token: Message [@BotFather](https://t.me/BotFather) → `/newbot`
> - Chat ID: Message [@userinfobot](https://t.me/userinfobot)

### 4. Run the Application
```bash
# From the project root
streamlit run frontend/app.py
```

### 5. First-Run Google OAuth
On first launch, a browser window opens for Google authentication. After approval, a `token.pkl` file is saved and reused on subsequent runs.

---

## 🛠️ Tech Stack

| Tool | Purpose |
|---|---|
| **LangGraph** | Stateful agent workflow orchestration |
| **Groq** (`llama-3.3-70b-versatile`) | Email classification, summarization, intent routing |
| **Gmail API** | Email fetching, auto-deletion (trash) |
| **Telegram Bot API** | Real-time push notifications |
| **Tavily** | Web search capability |
| **Streamlit** | Interactive analytics dashboard & chat UI |
| **Plotly** | Charts and visualizations |

---

## 🐛 Debugging

To test the backend agent without the UI:
```bash
python backend/rest/debug_cli.py
```
