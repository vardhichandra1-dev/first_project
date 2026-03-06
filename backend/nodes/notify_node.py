"""
Telegram Notification Node
---------------------------
Sends Telegram alerts for OTP, Banking, and Priority emails.
Gracefully skips if Telegram credentials are not configured.
Stores notification log entries in state["notification_log"].
"""

from state.state import AgentState
from rest.notifier import TelegramNotifier
from llm_initiation.LLM_initiate import NOTIFY_CATEGORIES


def notify_emails_node(state: AgentState) -> AgentState:
    print("--- SENDING NOTIFICATIONS ---")

    categories = state.get("categories", {})
    emails = state.get("emails", [])
    deleted_ids = set(state.get("deleted_ids", []))

    notification_log = []
    notified_ids = []

    notifier = TelegramNotifier()

    for email in emails:
        email_id = email.get("id")
        # Don't notify for deleted emails
        if email_id in deleted_ids:
            continue

        category = categories.get(email_id, "")
        if category in NOTIFY_CATEGORIES:
            subject = email.get("subject", "No Subject")
            sender  = email.get("sender", "Unknown")
            snippet = email.get("text", "")

            log_entry = notifier.notify_email(category, subject, sender, snippet)
            notification_log.append(log_entry)
            notified_ids.append(email_id)
            print(f"[notify] Sent alert for {category} email: {email_id}")

    print(f"[notify] Total notifications: {len(notified_ids)}")
    return {**state, "notified_ids": notified_ids, "notification_log": notification_log}
