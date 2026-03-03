# Email Assistant Agent

An intelligent agent that authenticates with Gmail to fetch unread emails and perform web searches, featuring a Streamlit chat interface.

## Project Structure

```
.
├── src/
│   ├── app.py               # Streamlit Application (Main Entry Point)
│   ├── debug_cli.py         # Command-line interface for debugging
│   ├── agent_graph.py       # LangGraph workflow definition (EmailAgentGraph)
│   ├── google_services.py   # Gmail API interaction (GmailService)
│   └── LLM_initiate.py      # LLM Logic (Groq implementation)
├── credentials.json         # Google OAuth client secrets (Required)
├── token.pkl                # Saved authentication token (Auto-generated)
├── requirements.txt         # Project dependencies
└── README.md                # Project documentation
```

## Features

-   **Chat Interface**: User-friendly chat UI built with Streamlit.
-   **Email Summarization**: Connects to Gmail to fetch and summarize unread emails.
-   **Web Search**: Uses Tavily for real-time web search results.
-   **Routing**: Automatically detects user intent (Email, Search, or Chat).
-   **LangGraph Workflow**: Structured state management using extensive graph logic.

## Setup & Usage

1.  **Prerequisites**:
    -   Python 3.10+
    -   Google Cloud Credentials (`credentials.json`) in the root directory.
    -   Environment variables set in `.env` (GROQ_API_KEY, TAVILY_API_KEY).

2.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Run the Application**:
    ```bash
    streamlit run src/app.py
    ```

4.  **First Run**:
    -   On the first run, a browser window will open asking you to authenticate with your Google account.
    -   If successful, a `token.pkl` file will be created, and you won't need to log in again until the token expires.

## Debugging

To test the agent logic without the UI, you can run the CLI script:
```bash
python src/debug_cli.py
```
