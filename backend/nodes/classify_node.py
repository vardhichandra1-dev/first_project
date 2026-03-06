"""
Email Classification Node
--------------------------
Classifies emails using the LLM and writes results back to the local cache.
"""

from state.state import AgentState
from llm_initiation.LLM_initiate import LLM_initiate
from rest.email_cache import EmailCache


def classify_emails_node(state: AgentState) -> AgentState:
    print("--- CLASSIFYING EMAILS ---")
    emails = state.get("emails", [])
    if not emails:
        print("[classify] No emails to classify.")
        return {**state, "categories": {}}

    # Only classify emails that don't already have a category (cached ones may already have it)
    needs_classification = [e for e in emails if not e.get("category")]
    already_classified   = {e["id"]: e["category"] for e in emails if e.get("category")}

    new_categories = {}
    if needs_classification:
        llm = LLM_initiate()
        new_categories = llm.classify_emails(needs_classification)
        print(f"[classify] Classified {len(new_categories)} emails.")

        # Write new classifications back to the local cache
        if new_categories:
            try:
                cache = EmailCache()
                cache.update_categories(new_categories)
                # Also update the in-memory email dicts so rest of pipeline has categories
                for email in emails:
                    eid = email.get("id")
                    if eid in new_categories:
                        email["category"] = new_categories[eid]
            except Exception as e:
                print(f"[classify] Cache write-back failed: {e}")
    else:
        print("[classify] All emails already classified (from cache).")

    # Merge already-classified + newly-classified
    all_categories = {**already_classified, **new_categories}
    return {**state, "categories": all_categories, "emails": emails}
