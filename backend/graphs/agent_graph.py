from langgraph.graph import StateGraph, END
from state.state import AgentState
from nodes.nodes import (
    router_node,
    authenticate_node,
    fetch_emails_node,
    summarize_emails_node,
    search_node,
    chat_node
)

class EmailAgentGraph:
    def __init__(self):
        self.workflow = StateGraph(AgentState)
        self._build_graph()

    def _build_graph(self):
        self.workflow.add_node("router", router_node)
        self.workflow.add_node("authenticate", authenticate_node)
        self.workflow.add_node("fetch_emails", fetch_emails_node)
        self.workflow.add_node("summarize_emails", summarize_emails_node)
        self.workflow.add_node("search", search_node)
        self.workflow.add_node("chat", chat_node)

        self.workflow.set_entry_point("router")
        
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
