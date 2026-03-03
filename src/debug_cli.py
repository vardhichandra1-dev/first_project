import agent_graph
from dotenv import load_dotenv

load_dotenv()

def main():
    print("Starting Email Assistant Agent...")
    app = agent_graph.create_graph()
    
    print("\n--- GRAPH STRUCTURE (ASCII) ---")
    try:
        print(app.get_graph().draw_ascii())
    except Exception as e:
        print(f"Could not draw ASCII graph: {e}")
        print("Ensure 'grandalf' is installed: pip install grandalf")

    print("\n--- GRAPH STRUCTURE (Mermaid) ---")
    try:
        print(app.get_graph().draw_mermaid())
    except Exception as e:
        print(f"Could not draw Mermaid graph: {e}")

    # Initialize state
    initial_state = {"service": None, "emails": [], "error": None}
    
    # Run the graph
    result = app.invoke(initial_state)
    
    if result.get("error"):
        print(f"Workflow failed with error: {result['error']}")
    else:
        print("\n--- EMAILS FETCHED ---")
        for email in result["emails"]:
            print(f"ID: {email['id']}")
            print(f"Snippet: {email['text']}")
            print(f"Summary: {email.get('summary', 'No summary available')}")
            print("-" * 30)

if __name__ == "__main__":
    main()
