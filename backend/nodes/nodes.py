"""
Core Agent Nodes (Cache-Aware)
-------------------------------
fetch_emails_node: reads from local JSON cache when available.
  - Loads cache on normal email queries.
  - Forces a fresh Gmail API pull when state["force_refresh"] is True.
  - After a fresh pull, merges results into the cache immediately.
"""

import os
from tavily import TavilyClient
from state.state import AgentState
from llm_initiation.LLM_initiate import LLM_initiate
from rest.google_services import GmailService
from rest.email_cache import EmailCache, CACHE_DAYS


# ------------------------------------------------------------------
# Router
# ------------------------------------------------------------------
def router_node(state: AgentState) -> AgentState:
    print("--- ROUTING ---")
    query = state.get("query", "")
    if not query:
        return {**state, "mode": "email"}

    llm  = LLM_initiate()
    mode = llm.decide_intent(query)
    print(f"[router] Intent: {mode}")

    email_params   = {}
    force_refresh  = False

    if mode == "email":
        email_params  = llm.extract_email_parameters(query)

        # Detect explicit refresh intent from user query
        refresh_kws = ["update", "refresh", "latest", "new emails", "sync", "reload"]
        if any(kw in query.lower() for kw in refresh_kws):
            force_refresh = True
            print("[router] Force-refresh requested by user.")

    return {**state, "mode": mode, "email_params": email_params,
            "force_refresh": force_refresh}


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
# Gmail – Fetch Emails (Cache-Aware)
# ------------------------------------------------------------------
def fetch_emails_node(state: AgentState) -> AgentState:
    print("--- FETCHING EMAILS ---")
    if state.get("error"):
        return state

    cache         = EmailCache()
    force_refresh = state.get("force_refresh", False)

    # ── Use cache when fresh and no force-refresh ──────────────────
    if not force_refresh and not cache.is_stale():
        cached_emails = cache.load()
        if cached_emails:
            print(f"[fetch] Serving {len(cached_emails)} emails from cache.")
            return {
                **state,
                "emails":        cached_emails,
                "from_cache":    True,
                "error":         None,
            }

    # ── Fresh fetch from Gmail API ─────────────────────────────────
    service = state.get("service")
    if not service:
        return {**state, "emails": [], "error": "Authentication required for fresh fetch."}

    try:
        print(f"[fetch] Pulling last {CACHE_DAYS} days from Gmail API…")
        fresh_emails = service.fetch_last_n_days(days=CACHE_DAYS, max_results=200)

        # Merge into cache and save
        merged = cache.merge(fresh_emails)
        cache.save(merged)

        print(f"[fetch] Cache updated: {len(merged)} emails stored.")
        return {
            **state,
            "emails":        merged,
            "from_cache":    False,
            "error":         None,
        }
    except Exception as e:
        print(f"[fetch] Error: {e}")
        # Fallback to whatever is in cache
        fallback = cache.load()
        return {**state, "emails": fallback, "from_cache": True, "error": str(e)}


# ------------------------------------------------------------------
# Email – Summarise (Priority / Banking / OTP only)
# ------------------------------------------------------------------
def summarize_emails_node(state: AgentState) -> AgentState:
    print("--- SUMMARISING EMAILS ---")
    emails     = state.get("emails", [])
    categories = state.get("categories", {})
    deleted_ids= set(state.get("deleted_ids", []))

    if not emails:
        return state

    SUMMARISE_CATS = {"OTP", "Banking", "Priority"}
    llm = LLM_initiate()

    for email in emails:
        eid = email.get("id")
        if eid in deleted_ids:
            email["summary"] = "⚠️ Auto-deleted (Promotional/Spam)."
            continue
        cat = categories.get(eid, "")
        # Summarise from body text if available, else snippet
        content = email.get("body") or email.get("snippet", "")
        if cat in SUMMARISE_CATS or not categories:
            email["summary"] = llm.summarize_email(content)
        else:
            email["summary"] = f"[{cat}] — summary skipped."

    query = state.get("query", "")
    chat_response = None
    if query:
        chat_response = llm.answer_email_query(query, emails)

    return {**state, "emails": emails, "chat_response": chat_response}


# ------------------------------------------------------------------
# Web Search
# ------------------------------------------------------------------
def search_node(state: AgentState) -> AgentState:
    print("--- SEARCHING ---")
    query = state.get("query")
    if not query:
        return {**state, "search_results": "No query provided."}
    try:
        tavily    = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
        response  = tavily.search(query=query)
        results   = response.get("results", [])
        formatted = "\n\n".join(
            f"- [{r['title']}]({r['url']}): {r['content']}" for r in results
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
        return {**state, "chat_response": "I didn't catch that. Could you repeat?"}
    llm      = LLM_initiate()
    response = llm.generate_chat_response(query)
    return {**state, "chat_response": response}
