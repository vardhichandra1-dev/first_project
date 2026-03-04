import os
from tavily import TavilyClient
from state.state import AgentState
from llm_initiation.LLM_initiate import LLM_initiate
from rest.google_services import GmailService

def router_node(state: AgentState) -> AgentState:
    print("--- ROUTING ---")
    query = state.get("query", "")
    if not query:
         return {**state, "mode": "email"}
    
    llm_service = LLM_initiate()
    mode = llm_service.decide_intent(query)
    print(f"Detected intent regarding: {mode}")
    
    email_params = {}
    if mode == "email":
         email_params = llm_service.extract_email_parameters(query)
         print(f"Extracted email params: {email_params}")

    return {**state, "mode": mode, "email_params": email_params}

def authenticate_node(state: AgentState) -> AgentState:
    print("--- AUTHENTICATING ---")
    try:
        service = GmailService()
        service.authenticate()
        return {**state, "service": service, "error": None}
    except Exception as e:
        return {**state, "service": None, "error": str(e)}

def fetch_emails_node(state: AgentState) -> AgentState:
    print("--- FETCHING EMAILS ---")
    if state.get("error"):
        print(f"Skipping fetch due to error: {state['error']}")
        return state
    
    service = state["service"]
    email_params = state.get("email_params", {})
    max_results = email_params.get("max_results", 5)
    q = email_params.get("q", "is:unread")

    try:
        print(f"Fetching with: max_results={max_results}, q='{q}'")
        emails = service.fetch_emails(max_results=max_results, q=q)
        return {**state, "emails": emails, "error": None}
    except Exception as e:
        return {**state, "emails": [], "error": str(e)}

def summarize_emails_node(state: AgentState) -> AgentState:
    print("--- SUMMARIZING EMAILS ---")
    if state.get("error") or not state.get("emails"):
        return state

    llm_service = LLM_initiate()
    emails = state["emails"]
    for email in emails:
        print(f"Summarizing email {email.get('id')}...")
        summary = llm_service.summarize_email(email.get("text", ""))
        email["summary"] = summary
    
    return {**state, "emails": emails}

def search_node(state: AgentState) -> AgentState:
    print("--- SEARCHING ---")
    query = state.get("query")
    if not query:
        return {**state, "search_results": "No query provided."}
    
    try:
        tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
        response = tavily.search(query=query)
        results = response.get("results", [])
        formatted_results = "\n\n".join([f"- [{r['title']}]({r['url']}): {r['content']}" for r in results])
        return {**state, "search_results": formatted_results}
    except Exception as e:
        return {**state, "search_results": f"Error searching: {str(e)}"}

def chat_node(state: AgentState) -> AgentState:
    print("--- CHATTING ---")
    query = state.get("query")
    if not query:
        return {**state, "chat_response": "I didn't catch that. Could you please repeat?"}
    
    llm_service = LLM_initiate()
    response = llm_service.generate_chat_response(query)
    return {**state, "chat_response": response}
