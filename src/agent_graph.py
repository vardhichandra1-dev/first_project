from typing import TypedDict, List, Any, Dict, Optional, Literal
from langgraph.graph import StateGraph, END
from google_services import GmailService
from LLM_initiate import LLM_initiate
from tavily import TavilyClient
import os
from dotenv import load_dotenv

load_dotenv()

class AgentState(TypedDict):
    service: Optional[GmailService]
    emails: List[Dict]
    error: Optional[str]
    query: Optional[str]
    search_results: Optional[str]
    chat_response: Optional[str]
    chat_response: Optional[str]
    mode: Optional[str]
    email_params: Optional[Dict]

class EmailAgentGraph:
    def __init__(self):
        self.workflow = StateGraph(AgentState)
        self.tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
        self._build_graph()

    def _router_node(self, state: AgentState) -> AgentState:
        print("--- ROUTING ---")
        query = state.get("query", "")
        if not query:
             # Default to email if no query, or handle error?
             # For now assume if no query but triggered, might be email default
             return {**state, "mode": "email"}
        
        llm_service = LLM_initiate()
        mode = llm_service.decide_intent(query)
        print(f"Detected intent regarding: {mode}")
        
        email_params = {}
        if mode == "email":
             email_params = llm_service.extract_email_parameters(query)
             print(f"Extracted email params: {email_params}")

        return {**state, "mode": mode, "email_params": email_params}

    def _authenticate_node(self, state: AgentState) -> AgentState:
        print("--- AUTHENTICATING ---")
        try:
            service = GmailService()
            service.authenticate()
            return {**state, "service": service, "error": None} # Keep existing state
        except Exception as e:
            return {**state, "service": None, "error": str(e)}

    def _fetch_emails_node(self, state: AgentState) -> AgentState:
        print("--- FETCHING EMAILS ---")
        if state.get("error"):
            print(f"Skipping fetch due to error: {state['error']}")
            return state
        
        service = state["service"]
        email_params = state.get("email_params", {})
        # Default fallback if params missing
        max_results = email_params.get("max_results", 5)
        q = email_params.get("q", "is:unread")

        try:
            print(f"Fetching with: max_results={max_results}, q='{q}'")
            emails = service.fetch_emails(max_results=max_results, q=q)
            return {**state, "emails": emails, "error": None}
        except Exception as e:
            return {**state, "emails": [], "error": str(e)}

    def _summarize_emails_node(self, state: AgentState) -> AgentState:
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

    def _search_node(self, state: AgentState) -> AgentState:
        print("--- SEARCHING ---")
        query = state.get("query")
        if not query:
            return {**state, "search_results": "No query provided."}
        
        try:
            response = self.tavily.search(query=query)
            # Tavily returns a dict with 'results' list
            results = response.get("results", [])
            # Format results
            formatted_results = "\n\n".join([f"- [{r['title']}]({r['url']}): {r['content']}" for r in results])
            return {**state, "search_results": formatted_results}
        except Exception as e:
            return {**state, "search_results": f"Error searching: {str(e)}"}

    def _chat_node(self, state: AgentState) -> AgentState:
        print("--- CHATTING ---")
        query = state.get("query")
        if not query:
            return {**state, "chat_response": "I didn't catch that. Could you please repeat?"}
        
        llm_service = LLM_initiate()
        response = llm_service.generate_chat_response(query)
        return {**state, "chat_response": response}

    def _build_graph(self):
        self.workflow.add_node("router", self._router_node)
        self.workflow.add_node("authenticate", self._authenticate_node)
        self.workflow.add_node("fetch_emails", self._fetch_emails_node)
        self.workflow.add_node("summarize_emails", self._summarize_emails_node)
        self.workflow.add_node("search", self._search_node)
        self.workflow.add_node("chat", self._chat_node)

        self.workflow.set_entry_point("router")
        
        # Conditional edge from router
        self.workflow.add_conditional_edges(
            "router",
            lambda x: x["mode"],
            {
                "email": "authenticate",
                "search": "search",
                "chat": "chat"
            }
        )

        self.workflow.add_edge("authenticate", "fetch_emails")
        self.workflow.add_edge("fetch_emails", "summarize_emails")
        self.workflow.add_edge("summarize_emails", END)
        self.workflow.add_edge("search", END)
        self.workflow.add_edge("chat", END)

    def compile(self):
        return self.workflow.compile()

def create_graph():
    """Factory function to create the graph logic."""
    agent = EmailAgentGraph()
    return agent.compile()
