from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.transport.requests import Request
import os
import pickle
from datetime import datetime, timezone, timedelta

from rest.email_cache import build_email_record

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]
CREDENTIALS_FILE = "credentials.json"


class GmailService:
    def __init__(self, account_id: str = "default"):
        """
        Args:
            account_id: Identifier for this Gmail account.
                        Used to namespace the token file (token_<id>.pkl).
        """
        self.account_id = account_id
        self.token_file = "token.pkl" if account_id == "default" else f"token_{account_id}.pkl"
        self.creds   = None
        self.service = None

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------
    def authenticate(self):
        """Authenticate and build the Gmail API service."""
        if os.path.exists(self.token_file):
            with open(self.token_file, "rb") as f:
                self.creds = pickle.load(f)

        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                try:
                    self.creds.refresh(Request())
                except Exception as e:
                    print(f"[GmailService] Token refresh failed: {e}")
                    os.remove(self.token_file)
                    self.creds = None

            if not self.creds:
                flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
                self.creds = flow.run_local_server(port=0)

            with open(self.token_file, "wb") as f:
                pickle.dump(self.creds, f)

        self.service = build("gmail", "v1", credentials=self.creds)
        print(f"[GmailService] Authenticated: {self.account_id}")
        return self.service

    # ------------------------------------------------------------------
    # Fetch last N days – full body + attachments (for cache)
    # ------------------------------------------------------------------
    def fetch_last_n_days(self, days: int = 3, max_results: int = 200) -> list:
        """
        Fetch ALL emails from the last `days` days.
        Returns a list of rich email dicts ready to be stored in the cache.
        Includes full body text and attachment metadata.
        """
        if not self.service:
            raise ValueError("Call authenticate() first.")

        # Gmail 'newer_than' filter
        q = f"newer_than:{days}d"
        print(f"[GmailService] Fetching last {days} days (q='{q}', max={max_results})…")

        try:
            results = self.service.users().messages().list(
                userId="me", maxResults=max_results, q=q
            ).execute()
        except HttpError as e:
            print(f"[GmailService] list() error: {e}")
            return []

        messages = results.get("messages", [])
        print(f"[GmailService] Found {len(messages)} message IDs – fetching full data…")

        emails = []
        for msg in messages:
            try:
                data = self.service.users().messages().get(
                    userId="me", id=msg["id"], format="full"
                ).execute()
                record = build_email_record(data, account_id=self.account_id)
                emails.append(record)
            except HttpError as e:
                print(f"[GmailService] get() error for {msg['id']}: {e}")

        print(f"[GmailService] Built {len(emails)} rich email records.")
        return emails

    # ------------------------------------------------------------------
    # Lightweight fetch (used by chat queries – reads from live q)
    # ------------------------------------------------------------------
    def fetch_emails(self, max_results: int = 10, q: str = "is:unread") -> list:
        """
        Lightweight fetch for ad-hoc queries.
        Returns rich email dicts (with body + attachments).
        """
        if not self.service:
            raise ValueError("Call authenticate() first.")

        try:
            results = self.service.users().messages().list(
                userId="me", maxResults=max_results, q=q
            ).execute()
        except HttpError as e:
            print(f"[GmailService] Gmail API error: {e}")
            return []

        messages = results.get("messages", [])
        emails   = []
        for msg in messages:
            try:
                data   = self.service.users().messages().get(
                    userId="me", id=msg["id"], format="full"
                ).execute()
                emails.append(build_email_record(data, self.account_id))
            except HttpError as e:
                print(f"[GmailService] get() error for {msg['id']}: {e}")

        return emails

    # ------------------------------------------------------------------
    # Delete (move to trash)
    # ------------------------------------------------------------------
    def delete_email(self, email_id: str) -> bool:
        """Move an email to Trash. Returns True on success."""
        if not self.service:
            raise ValueError("Call authenticate() first.")
        try:
            self.service.users().messages().trash(userId="me", id=email_id).execute()
            print(f"[GmailService] Trashed: {email_id}")
            return True
        except HttpError as e:
            print(f"[GmailService] Error trashing {email_id}: {e}")
            return False

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------
    def get_email_subject(self, email_id: str) -> str:
        """Fetch just the Subject header of an email."""
        if not self.service:
            return "Unknown Subject"
        try:
            data = self.service.users().messages().get(
                userId="me", id=email_id,
                format="metadata", metadataHeaders=["Subject"]
            ).execute()
            for h in data.get("payload", {}).get("headers", []):
                if h.get("name") == "Subject":
                    return h.get("value", "No Subject")
        except Exception:
            pass
        return "No Subject"


if __name__ == "__main__":
    gmail = GmailService()
    gmail.authenticate()
    emails = gmail.fetch_last_n_days(days=3, max_results=10)
    for e in emails:
        print(f"[{e['date_iso'][:10]}] {e['subject']} | From: {e['sender_email']} | "
              f"Attachments: {len(e['attachments'])}")