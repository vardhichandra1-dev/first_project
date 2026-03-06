"""
Auto-Delete Node
-----------------
Moves Promotional and Spam emails to Trash via Gmail API.
Banking, OTP, Priority, and Social emails are NEVER deleted.
Stores list of deleted email IDs in state["deleted_ids"].
"""

from state.state import AgentState
from llm_initiation.LLM_initiate import DELETABLE_CATEGORIES


def delete_emails_node(state: AgentState) -> AgentState:
    print("--- AUTO-DELETING NON-CRITICAL EMAILS ---")

    service = state.get("service")
    categories = state.get("categories", {})
    emails = state.get("emails", [])

    if not service or not categories:
        print("[delete] Skipping – no service or categories.")
        return {**state, "deleted_ids": []}

    deleted_ids = []
    for email in emails:
        email_id = email.get("id")
        category = categories.get(email_id, "")
        if category in DELETABLE_CATEGORIES:
            success = service.delete_email(email_id)
            if success:
                deleted_ids.append(email_id)
                print(f"[delete] Trashed {category} email: {email_id}")

    print(f"[delete] Total deleted: {len(deleted_ids)}")
    return {**state, "deleted_ids": deleted_ids}
