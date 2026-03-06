from typing import TypedDict, List, Dict, Optional, Any

class AgentState(TypedDict):
    # Gmail service instance
    service: Optional[Any]

    # Emails fetched (list of dicts with id, text, subject, date)
    emails: List[Dict]

    # Error message if any step fails
    error: Optional[str]

    # User query from chat
    query: Optional[str]

    # Routing mode: email | search | chat
    mode: Optional[str]

    # Parameters extracted from user query for email fetch
    email_params: Optional[Dict]

    # --- Classification ---
    # Maps email_id -> category (OTP, Banking, Promotional, Priority, Social, Spam)
    categories: Optional[Dict[str, str]]

    # --- Auto-deletion ---
    # List of email IDs that were moved to trash
    deleted_ids: Optional[List[str]]

    # --- Notifications ---
    # List of email IDs for which a Telegram alert was sent
    notified_ids: Optional[List[str]]

    # Human-readable notification log entries
    notification_log: Optional[List[str]]

    # --- Search & Chat ---
    search_results: Optional[str]
    chat_response: Optional[str]
