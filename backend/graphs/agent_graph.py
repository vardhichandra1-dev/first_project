"""
Email Agent Graph
-----------------
LangGraph workflow for the AI Email Assistant.

Flow:
    router
     ├─ email  → authenticate → fetch_emails → classify → delete → notify → summarize → END
     ├─ search → search → END
     └─ chat   → chat → END
"""

from langgraph.graph import StateGraph, END
from state.state import AgentState
from nodes.nodes import (
    router_node,
    authenticate_node,
    fetch_emails_node,
    summarize_emails_node,
    search_node,
    chat_node,
)
from nodes.classify_node import classify_emails_node
from nodes.delete_node import delete_emails_node
from nodes.notify_node import notify_emails_node


class EmailAgentGraph:
    def __init__(self):
        self.workflow = StateGraph(AgentState)
        self._build_graph()

    def _build_graph(self):
        # ── Nodes ──────────────────────────────────────────────────
        self.workflow.add_node("router", router_node)
        self.workflow.add_node("authenticate", authenticate_node)
        self.workflow.add_node("fetch_emails", fetch_emails_node)
        self.workflow.add_node("classify", classify_emails_node)
        self.workflow.add_node("delete", delete_emails_node)
        self.workflow.add_node("notify", notify_emails_node)
        self.workflow.add_node("summarize_emails", summarize_emails_node)
        self.workflow.add_node("search", search_node)
        self.workflow.add_node("chat", chat_node)

        # ── Entry Point ────────────────────────────────────────────
        self.workflow.set_entry_point("router")

        # ── Routing from router ────────────────────────────────────
        self.workflow.add_conditional_edges(
            "router",
            lambda x: x["mode"],
            {
                "email":  "authenticate",
                "search": "search",
                "chat":   "chat",
            },
        )

        # ── Email pipeline ─────────────────────────────────────────
        self.workflow.add_edge("authenticate",   "fetch_emails")
        self.workflow.add_edge("fetch_emails",   "classify")
        self.workflow.add_edge("classify",        "delete")
        self.workflow.add_edge("delete",          "notify")
        self.workflow.add_edge("notify",          "summarize_emails")
        self.workflow.add_edge("summarize_emails", END)

        # ── Search / Chat pipelines ────────────────────────────────
        self.workflow.add_edge("search", END)
        self.workflow.add_edge("chat",   END)

    def compile(self):
        return self.workflow.compile()


def create_graph():
    """Factory – returns a compiled LangGraph agent."""
    return EmailAgentGraph().compile()
