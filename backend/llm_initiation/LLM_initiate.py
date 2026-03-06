import re
import json
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate

# Valid Groq model – fast and capable
GROQ_MODEL = "llama-3.3-70b-versatile"

# Categories used throughout the system
EMAIL_CATEGORIES = ["OTP", "Banking", "Promotional", "Priority", "Social", "Spam"]

# Categories that should be auto-deleted
DELETABLE_CATEGORIES = {"Promotional", "Spam"}

# Categories that trigger Telegram notification
NOTIFY_CATEGORIES = {"OTP", "Banking", "Priority"}


def _clean_llm_output(text: str) -> str:
    """Strip markdown fences and <think> tags from LLM output."""
    text = re.sub(r"```json", "", text)
    text = re.sub(r"```", "", text)
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    return text.strip()


class LLM_initiate:
    def __init__(self):
        self.llm = ChatGroq(model_name=GROQ_MODEL)

    def get_llm(self):
        return self.llm

    def get_prompt(self):
        return PromptTemplate.from_template("{email}")

    # ------------------------------------------------------------------
    # Intent routing
    # ------------------------------------------------------------------
    def decide_intent(self, query: str) -> str:
        """Classify user intent: 'email', 'search', or 'chat'."""
        prompt = f"""
You are a router. Classify the user's intent into exactly one of: 'email', 'search', or 'chat'.

Definitions:
- 'email': User wants to read, fetch, summarise, classify, check, or manage their emails.
- 'search': User asks a factual/technical/news question requiring external knowledge.
- 'chat': Casual conversation, greetings, identity questions, or open-ended non-factual questions.

User Query: "{query}"

Rules:
- Respond ONLY with the single word: email | search | chat
- No punctuation, no explanation.
"""
        try:
            response = self.llm.invoke(prompt)
            content = _clean_llm_output(response.content).lower()
            if "email" in content:
                return "email"
            elif "search" in content:
                return "search"
            return "chat"
        except Exception:
            return "chat"

    # ------------------------------------------------------------------
    # Email parameter extraction
    # ------------------------------------------------------------------
    def extract_email_parameters(self, query: str) -> dict:
        """Extract Gmail API fetch parameters from the user's query."""
        prompt = f"""
You are a helper that extracts Gmail search parameters from a user query.

User Query: "{query}"

Instructions:
1. Identify how many emails to fetch.
   - If specified (e.g. "last 5 emails"), use that number.
   - If "all" or "today's", use 20.
   - Otherwise default to 5.
   - Key: "max_results" (integer)

2. Build a Gmail search query string.
   - "today's mails"  → "newer_than:1d"
   - "last week"      → "newer_than:7d"
   - "unread"         → "is:unread"
   - Combine as needed. Default: "is:unread"
   - Key: "q" (string)

Output ONLY valid JSON:
{{
    "max_results": <int>,
    "q": "<string>"
}}
"""
        try:
            response = self.llm.invoke(prompt)
            content = _clean_llm_output(response.content)
            return json.loads(content)
        except Exception as e:
            print(f"[LLM] Error extracting email params: {e}")
            return {"max_results": 5, "q": "is:unread"}

    # ------------------------------------------------------------------
    # Email summarisation
    # ------------------------------------------------------------------
    def summarize_email(self, content: str) -> str:
        """Summarise a single email's content concisely."""
        if not content:
            return "No content available."
        prompt = f"Summarise the following email in 2-3 sentences:\n\n{content}"
        try:
            response = self.llm.invoke(prompt)
            return response.content
        except Exception as e:
            return f"Error generating summary: {str(e)}"

    # ------------------------------------------------------------------
    # Email classification (6 categories)
    # ------------------------------------------------------------------
    def classify_emails(self, emails: list) -> dict:
        """
        Classify emails into one of 6 categories.

        Returns: {email_id: category_string}
        Categories: OTP | Banking | Promotional | Priority | Social | Spam
        """
        if not emails:
            return {}

        email_data = [
            {"id": e.get("id"), "subject": e.get("subject", ""), "snippet": e.get("text", "")[:250]}
            for e in emails
        ]

        prompt = f"""
You are an expert email classifier. Classify each email into exactly one category.

Categories:
- OTP        : One-time passwords, verification codes, login codes
- Banking    : Transaction alerts, bank statements, fund transfers, account notices
- Promotional: Marketing, newsletters, discount offers, sale announcements
- Priority   : Work emails, meeting requests, urgent personal messages, action required
- Social     : LinkedIn, Facebook, Instagram, Twitter notifications
- Spam       : Unsolicited junk, phishing attempts, irrelevant bulk mail

Emails to classify:
{json.dumps(email_data, indent=2)}

Rules:
- Return ONLY a JSON object mapping each email ID to its category.
- Example: {{"abc123": "OTP", "def456": "Promotional"}}
- Every email ID must appear exactly once.
- Use only the exact category names listed above.
"""
        try:
            response = self.llm.invoke(prompt)
            content = _clean_llm_output(response.content)
            return json.loads(content)
        except Exception as e:
            print(f"[LLM] Error classifying emails: {e}")
            return {e_item["id"]: "Priority" for e_item in email_data}

    # ------------------------------------------------------------------
    # General chat
    # ------------------------------------------------------------------
    def generate_chat_response(self, query: str) -> str:
        """Generate a natural chat response."""
        prompt = f"""You are a helpful AI Email Assistant. Respond naturally and helpfully.

User: {query}
"""
        try:
            response = self.llm.invoke(prompt)
            return response.content
        except Exception as e:
            return f"Error generating response: {str(e)}"

    def answer_email_query(self, query: str, emails: list) -> str:
        """Answer a user's specific query about the fetched emails."""
        if not emails:
            return "I couldn't find any relevant emails to answer your request."
        
        context_data = []
        for e in emails[:5]:  # Provide top 5 for context to avoid overloading context window
            context_data.append({
                "from": e.get("sender_email", e.get("sender", "Unknown")),
                "subject": e.get("subject", "No Subject"),
                "date": e.get("date_iso", ""),
                "content": (e.get("body") or e.get("snippet", ""))[:1000]
            })
            
        prompt = f"""You are a helpful AI Email Assistant interpreting the following fetched emails to answer the user's query.

User Query: "{query}"

Fetched Emails Context:
{json.dumps(context_data, indent=2)}

Please provide a helpful, direct answer or explanation based ONLY on the above emails.
If the user's query is just a generic command to fetch or update emails (e.g. "show emails", "fetch new messages"), respond by saying "Here are your requested emails:"
"""
        try:
            response = self.llm.invoke(prompt)
            return response.content
        except Exception as e:
            return f"Error analyzing emails: {str(e)}"

