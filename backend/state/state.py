from typing import TypedDict, List, Dict, Optional, Any

class AgentState(TypedDict):
    service: Optional[Any]
    emails: List[Dict]
    error: Optional[str]
    query: Optional[str]
    search_results: Optional[str]
    chat_response: Optional[str]
    mode: Optional[str]
    email_params: Optional[Dict]
