from langchain_groq import ChatGroq
import re
from langchain_core.prompts import PromptTemplate

class LLM_initiate:
    def __init__(self):
        self.llm = ChatGroq(model_name="openai/gpt-oss-120b")
    
    def get_llm(self):
        return self.llm 

    def summarize_email(self, content: str) -> str:
        """Summarizes the given email content."""
        prompt = f"Please summarize the following email content concisely:\n\n{content}"
        try:
            response = self.llm.invoke(prompt)
            return response.content
        except Exception as e:
            return f"Error accumulating summary: {str(e)}"

    def get_prompt(self):
        return PromptTemplate.from_template("{email}")

    def decide_intent(self, query: str) -> str:
        """Decides if the query is about emails, general search, or chat."""
        prompt = f"""
        You are a router. Your job is to classify the user's intent into exactly one of three categories: 'email', 'search', or 'chat'.

        Definitions:
        - 'email': User wants to read, summarize, fetch, check, or list their own emails.
        - 'search': User is asking a fact-based question containing specific entities, news, or technical queries that requires external knowledge.
        - 'chat': User is engaging in casual conversation, asking about your identity, greetings, or general open-ended non-factual questions (e.g., "tell me about you", "hello", "how are you").

        User Query: "{query}"

        Instructions:
        - Respond ONLY with the word 'email', 'search', or 'chat'.
        - Do not explain your reasoning.
        - Do not output punctuation.
        """
        try:
            response = self.llm.invoke(prompt)
            content = response.content.strip()
            # Remove <think> tags if present
            content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip().lower()
            
            if "email" in content:
                return "email"
            elif "search" in content:
                return "search"
            
            # Default to chat if not explicitly email or search
            return "chat"
            
        except Exception:
            return "chat" # Default to chat on error

    def generate_chat_response(self, query: str) -> str:
        """Generates a response for general chat."""
        prompt = f"""
        You are a helpful AI Assistant.
        
        User: {query}
        
        Respond naturally and helpfully to the user.
        """
        try:
            response = self.llm.invoke(prompt)
            return response.content
        except Exception as e:
            return f"Error generating response: {str(e)}"

    def extract_email_parameters(self, query: str) -> dict:
        """
        Extracts email fetch parameters from the user's query.
        Returns a dict with 'max_results' (int) and 'q' (str) for Gmail API.
        """
        prompt = f"""
        You are a helper that extracts Gmail search parameters from a user query.
        
        User Query: "{query}"

        Instructions:
        1. Identify the number of emails the user wants to fetch.
           - If specified (e.g., "last 5 emails", "review 3 emails"), use that number.
           - If implied as "all" or "today's emails", use a reasonable limit like 20.
           - If NOT specified, default to 5.
           - Key: "max_results" (integer)

        2. Construct a Gmail search query string (q parameter) if needed.
           - "today's mails" -> "newer_than:1d"
           - "last week" -> "newer_than:7d"
           - "unread" -> "is:unread" (Always include is:unread unless user asks for all/old emails)
           - Combine filters if needed (e.g., "is:unread newer_than:1d").
           - If no specific time/status logic, default to "is:unread".
           - Key: "q" (string)

        Output JSON ONLY:
        {{
            "max_results": <int>,
            "q": "<string>"
        }}
        """
        try:
            response = self.llm.invoke(prompt)
            content = response.content.strip()
            # Clean possible markdown code blocks
            content = re.sub(r'```json', '', content)
            content = re.sub(r'```', '', content)
            # Remove <think> tags if present
            content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()
            
            import json
            return json.loads(content)
        except Exception as e:
            print(f"Error extracting email params: {e}")
            return {"max_results": 5, "q": "is:unread"}

    def classify_emails(self, emails: list) -> dict:
        """
        Classifies a list of emails into categories.
        Returns a dict: {email_id: category}
        Categories: ["Bank/Finance", "Promotional", "Social", "Work", "Personal"]
        """
        if not emails:
            return {}

        email_data = [{"id": e.get("id"), "snippet": e.get("text", "")[:200]} for e in emails]
        prompt = f"""
        You are an email classifier. Classify the following emails based on their snippets.
        
        Categories:
        - Bank/Finance (Transaction alerts, statements, OTPs, bank offers)
        - Promotional (Marketing, newsletters, sales, offers)
        - Social (LinkedIn, Facebook, Instagram notifications)
        - Work (Meeting invites, project discussion, internal comms)
        - Personal (Family, friends, direct correspondence)

        Emails:
        {email_data}

        Instructions:
        - Return ONLY a JSON object mapping email ID to Category.
        - Example: {{"123": "Work", "124": "Promotional"}}
        """
        try:
            response = self.llm.invoke(prompt)
            content = response.content.strip()
            content = re.sub(r'```json', '', content)
            content = re.sub(r'```', '', content)
            content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()
            
            import json
            return json.loads(content)
        except Exception as e:
            print(f"Error classifying emails: {e}")
            # Fallback: all unknown
            return {e["id"]: "Personal" for e in emails}
