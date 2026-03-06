"""
Telegram Notification Service
------------------------------
Sends Telegram messages for Priority / Banking / OTP emails.
If TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID are not set in .env,
all operations are silently skipped (no crash).
"""

import os
import requests
from datetime import datetime


class TelegramNotifier:
    def __init__(self):
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
        self.enabled = bool(self.bot_token and self.chat_id)

        if not self.enabled:
            print("[TelegramNotifier] Not configured – notifications will be skipped.")
            print("  Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in your .env to enable.")

    def send_alert(self, message: str) -> bool:
        """
        Send a plain-text alert to Telegram.
        Returns True on success, False if disabled or on error.
        """
        if not self.enabled:
            return False
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": "HTML",
        }
        try:
            resp = requests.post(url, json=payload, timeout=10)
            resp.raise_for_status()
            return True
        except requests.RequestException as e:
            print(f"[TelegramNotifier] Failed to send message: {e}")
            return False

    def notify_email(self, category: str, subject: str, sender: str, snippet: str) -> str:
        """
        Format and send a Telegram notification for an important email.
        Returns the formatted message string (useful for logging even when disabled).
        """
        ts = datetime.now().strftime("%H:%M %d-%b-%Y")
        icon = {"OTP": "🔐", "Banking": "🏦", "Priority": "⚡"}.get(category, "📧")
        msg = (
            f"{icon} <b>{category} Email Alert</b>\n"
            f"📅 <i>{ts}</i>\n"
            f"📌 <b>Subject:</b> {subject}\n"
            f"👤 <b>From:</b> {sender}\n"
            f"💬 <b>Preview:</b> {snippet[:200]}"
        )
        self.send_alert(msg)
        return msg
