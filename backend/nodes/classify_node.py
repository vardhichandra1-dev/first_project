"""
Email Classification Node
--------------------------
Uses the LLM to classify each fetched email into one of 6 categories:
  OTP | Banking | Promotional | Priority | Social | Spam
Stores result in state["categories"] as {email_id: category}.
"""

from state.state import AgentState
from llm_initiation.LLM_initiate import LLM_initiate


def classify_emails_node(state: AgentState) -> AgentState:
    print("--- CLASSIFYING EMAILS ---")
    emails = state.get("emails", [])
    if not emails:
        print("[classify] No emails to classify.")
        return {**state, "categories": {}}

    llm = LLM_initiate()
    categories = llm.classify_emails(emails)
    print(f"[classify] Results: {categories}")
    return {**state, "categories": categories}
