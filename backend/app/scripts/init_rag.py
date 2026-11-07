"""Initialize the vector chunk schema after document tables exist."""
from app.rag import setup_rag_schema

if __name__ == "__main__":
    setup_rag_schema()
    print("RAG chunk tables ready")
