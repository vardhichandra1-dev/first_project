from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.transport.requests import Request
import os
import pickle

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]
CREDENTIALS_FILE = "credentials.json"


class GmailService:
    def __init__(self, account_id: str = "default"):
        """
        Args:
            account_id: Identifier for the Gmail account.
                        Used to namespace the token file (token_<account_id>.pkl).
        """
        self.account_id = account_id
        self.token_file = f"token_{account_id}.pkl" if account_id != "default" else "token.pkl"
        self.creds = None
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
        print(f"[GmailService] Authenticated account: {self.account_id}")
        return self.service

    # ------------------------------------------------------------------
    # Fetch emails
    # ------------------------------------------------------------------
    def fetch_emails(self, max_results: int = 5, q: str = "is:unread") -> list:
        """Fetch emails matching the given query. Returns list of email dicts."""
        if not self.service:
            raise ValueError("Call authenticate() before fetching emails.")

        try:
            results = self.service.users().messages().list(
                userId="me", maxResults=max_results, q=q
            ).execute()
        except HttpError as e:
            print(f"[GmailService] Gmail API error: {e}")
            return []

        messages = results.get("messages", [])
        emails = []

        for msg in messages:
            data = self.service.users().messages().get(
                userId="me", id=msg["id"], format="full"
            ).execute()

            payload = data.get("payload", {})
            headers = payload.get("headers", [])

            subject = "No Subject"
            date = "Unknown"
            sender = "Unknown"
            for h in headers:
                name = h.get("name", "")
                if name == "Subject":
                    subject = h.get("value", "No Subject")
                elif name == "Date":
                    date = h.get("value", "Unknown")
                elif name == "From":
                    sender = h.get("value", "Unknown")

            snippet = data.get("snippet", "")
            emails.append({
                "id": msg["id"],
                "subject": subject,
                "text": snippet,
                "date": date,
                "sender": sender,
                "account_id": self.account_id,
            })

        return emails

    # ------------------------------------------------------------------
    # Delete (move to trash)
    # ------------------------------------------------------------------
    def delete_email(self, email_id: str) -> bool:
        """Move an email to Trash. Returns True on success."""
        if not self.service:
            raise ValueError("Call authenticate() before deleting emails.")
        try:
            self.service.users().messages().trash(userId="me", id=email_id).execute()
            print(f"[GmailService] Moved to trash: {email_id}")
            return True
        except HttpError as e:
            print(f"[GmailService] Error trashing email {email_id}: {e}")
            return False

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------
    def get_email_subject(self, email_id: str) -> str:
        """Fetch just the subject line of an email."""
        if not self.service:
            return "Unknown Subject"
        try:
            data = self.service.users().messages().get(
                userId="me", id=email_id, format="metadata",
                metadataHeaders=["Subject"]
            ).execute()
            headers = data.get("payload", {}).get("headers", [])
            for h in headers:
                if h.get("name") == "Subject":
                    return h.get("value", "No Subject")
        except Exception:
            pass
        return "No Subject"


if __name__ == "__main__":
    gmail = GmailService()
    gmail.authenticate()
    emails = gmail.fetch_emails(max_results=3)
    for e in emails:
        print(f"[{e['date']}] {e['subject']} — {e['text'][:80]}")