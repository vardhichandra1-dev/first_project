from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.transport.requests import Request
import os, pickle

class GmailService:
    SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]
    TOKEN_FILE = "token.pkl"
    CREDENTIALS_FILE = "credentials.json"

    def __init__(self):
        self.creds = None
        self.service = None

    def authenticate(self):
        """Authenticates the user and creates the Gmail service."""
        if os.path.exists(self.TOKEN_FILE):
            with open(self.TOKEN_FILE, "rb") as f:
                self.creds = pickle.load(f)

        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                try:
                    self.creds.refresh(Request())
                except Exception as e:
                    print(f"Error refreshing token: {e}")
                    print("Deleting invalid token and re-authenticating...")
                    os.remove(self.TOKEN_FILE)
                    self.creds = None # Reset creds to trigger fresh login
            
            if not self.creds: # Check again in case refresh failed and we reset
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.CREDENTIALS_FILE, self.SCOPES
                )
                self.creds = flow.run_local_server(port=0)
            
            # Save the new token
            with open(self.TOKEN_FILE, "wb") as f:
                pickle.dump(self.creds, f)

        self.service = build("gmail", "v1", credentials=self.creds)
        return self.service

    def fetch_emails(self, max_results=5, q="is:unread"):
        """Fetches emails from the user's inbox based on criteria."""
        if not self.service:
            raise ValueError("Service not authenticated. Call authenticate() first.")
        
        try:
            results = self.service.users().messages().list(
                userId="me", maxResults=max_results, q=q
            ).execute()
        except HttpError as e:
            # Handle empty query or invalid request gracefully
            print(f"Gmail API Warning: {e}")
            return []

        messages = results.get("messages", [])
        emails = []

        for msg in messages:
            data = self.service.users().messages().get(
                userId="me", id=msg["id"], format="full"
            ).execute()
            payload = data.get("payload", {})
            headers = payload.get("headers", [])
            date = "Unknown"
            for header in headers:
                if header.get("name") == "Date":
                    date = header.get("value")
                    break
            
            snippet = data.get("snippet", "")
            emails.append({"id": msg["id"], "text": snippet, "date": date})

        return emails

if __name__ == "__main__":
    try:
        gmail = GmailService()
        gmail.authenticate()
        emails = gmail.fetch_emails()
        print(emails[-1].get("text") if emails else "No emails found.")
    except HttpError as error:
        print(f"An error occurred: {error}")
        if error.resp.status == 403:
            print("\n[!] Access Denied (403).")
            print("    Please ensure your email is added as a 'Test user' in the Google Cloud Console.")
            print("    See 'resolve_oauth_error.md' for instructions.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")