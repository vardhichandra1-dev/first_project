from typing import TypedDict, List, Dict, Optional, Any

class AgentState(TypedDict):
    # Gmail service instance
    service: Optional[Any]

    # Emails fetched (rich dicts – from cache or live)
    emails: List[Dict]

    # Error message if any step fails
    error: Optional[str]

    # User query from chat
    query: Optional[str]

    # Routing mode: email | search | chat
    mode: Optional[str]

    # Parameters extracted from user query for email fetch
    email_params: Optional[Dict]

    # True → bypass cache and pull fresh from Gmail API
    force_refresh: Optional[bool]

    # True → emails were served from local cache (not live API)
    from_cache: Optional[bool]

    # --- Classification ---
    # Maps email_id -> category (OTP, Banking, Promotional, Priority, Social, Spam)
    categories: Optional[Dict[str, str]]

    # --- Auto-deletion ---
    deleted_ids: Optional[List[str]]

    # --- Notifications ---
    notified_ids: Optional[List[str]]
    notification_log: Optional[List[str]]

    # --- Search & Chat ---
    search_results: Optional[str]
    chat_response: Optional[str]
