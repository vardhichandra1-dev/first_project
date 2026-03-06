"""
Core Agent Nodes
-----------------
Each function takes AgentState and returns a (partial) updated AgentState.
"""

import os
from tavily import TavilyClient
from state.state import AgentState
from llm_initiation.LLM_initiate import LLM_initiate
from rest.google_services import GmailService


# ------------------------------------------------------------------
# Router
# ------------------------------------------------------------------
def router_node(state: AgentState) -> AgentState:
    print("--- ROUTING ---")
    query = state.get("query", "")
    if not query:
        return {**state, "mode": "email"}

    llm = LLM_initiate()
    mode = llm.decide_intent(query)
    print(f"[router] Detected intent: {mode}")

    email_params = {}
    if mode == "email":
        email_params = llm.extract_email_parameters(query)
        print(f"[router] Email params: {email_params}")

    return {**state, "mode": mode, "email_params": email_params}


# ------------------------------------------------------------------
# Gmail – Authenticate
# ------------------------------------------------------------------
def authenticate_node(state: AgentState) -> AgentState:
    print("--- AUTHENTICATING ---")
    try:
        service = GmailService(account_id="default")
        service.authenticate()
        return {**state, "service": service, "error": None}
    except Exception as e:
        print(f"[auth] Error: {e}")
        return {**state, "service": None, "error": str(e)}


# ------------------------------------------------------------------
# Gmail – Fetch Emails
# ------------------------------------------------------------------
def fetch_emails_node(state: AgentState) -> AgentState:
    print("--- FETCHING EMAILS ---")
    if state.get("error"):
        return state

    service = state["service"]
    email_params = state.get("email_params", {})
    max_results = email_params.get("max_results", 5)
    q = email_params.get("q", "is:unread")

    try:
        print(f"[fetch] max_results={max_results}, q='{q}'")
        emails = service.fetch_emails(max_results=max_results, q=q)
        print(f"[fetch] Got {len(emails)} emails.")
        return {**state, "emails": emails, "error": None}
    except Exception as e:
        print(f"[fetch] Error: {e}")
        return {**state, "emails": [], "error": str(e)}


# ------------------------------------------------------------------
# Email – Summarise (only Priority / Banking / OTP)
# ------------------------------------------------------------------
def summarize_emails_node(state: AgentState) -> AgentState:
    print("--- SUMMARISING EMAILS ---")
    if state.get("error") or not state.get("emails"):
        return state

    categories = state.get("categories", {})
    SUMMARISE_CATS = {"OTP", "Banking", "Priority"}

    llm = LLM_initiate()
    emails = state["emails"]
    deleted_ids = set(state.get("deleted_ids", []))

    for email in emails:
        email_id = email.get("id")
        if email_id in deleted_ids:
            email["summary"] = "⚠️ This email was auto-deleted (Promotional/Spam)."
            continue
        cat = categories.get(email_id, "")
        if cat in SUMMARISE_CATS or not categories:
            email["summary"] = llm.summarize_email(email.get("text", ""))
        else:
            email["summary"] = f"[{cat}] — auto-skipped summarisation."

    return {**state, "emails": emails}


# ------------------------------------------------------------------
# Web Search
# ------------------------------------------------------------------
def search_node(state: AgentState) -> AgentState:
    print("--- SEARCHING ---")
    query = state.get("query")
    if not query:
        return {**state, "search_results": "No query provided."}

    try:
        tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
        response = tavily.search(query=query)
        results = response.get("results", [])
        formatted = "\n\n".join(
            [f"- [{r['title']}]({r['url']}): {r['content']}" for r in results]
        )
        return {**state, "search_results": formatted}
    except Exception as e:
        return {**state, "search_results": f"Search error: {str(e)}"}


# ------------------------------------------------------------------
# General Chat
# ------------------------------------------------------------------
def chat_node(state: AgentState) -> AgentState:
    print("--- CHATTING ---")
    query = state.get("query")
    if not query:
        return {**state, "chat_response": "I didn't catch that. Could you please repeat?"}

    llm = LLM_initiate()
    response = llm.generate_chat_response(query)
    return {**state, "chat_response": response}
