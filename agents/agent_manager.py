"""
agent_manager.py: Legacy/simple manager using direct OpenAI client for log processing, indexing, and search via RCAVectorStore.
Useful for batch operations without the Semantic Kernel pipeline.
"""

import os
from dotenv import load_dotenv
from openai import OpenAI
from storage.rca_vector_store import RCAVectorStore

load_dotenv()


class AgentManager:
    """
    The AgentManager orchestrates RCA operations like:
    - Processing logs
    - Generating RCA reports
    - Indexing RCA reports into Pinecone
    - Answering user queries using embeddings search
    """

    def __init__(self):
        # Initialize OpenAI client
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        # Initialize RCA vector store (Pinecone integration)
        self.vector_store = RCAVectorStore()

    def process_logs_and_generate_rca(self, logs_dir: str, rca_dir: str) -> str:
        """
        Automatically process logs and generate RCA reports.
        :param logs_dir: Directory containing raw log files
        :param rca_dir: Directory to save generated RCA reports
        """
        from agents.log_agent import LogAgent

        log_agent = LogAgent(openai_client=self.openai_client)

        # Process logs into RCA reports
        return log_agent.generate_rca_reports(logs_dir, rca_dir)

    def index_rca_reports(self, rca_dir: str) -> str:
        """
        Chunk RCA reports and store them into Pinecone for semantic search.
        :param rca_dir: Folder where RCA reports are saved
        """
        return self.vector_store.chunk_and_store_reports(rca_dir)

    def search_similar_rcas(self, query: str, top_k: int = 5):
        """
        Search RCA reports by semantic similarity.
        :param query: User query
        :param top_k: Number of top matches to return
        """
        return self.vector_store.search_similar(query, top_k=top_k)

    def analyze_faults(self, query: str):
        """
        Use OpenAI to analyze RCA findings and summarize potential causes.
        :param query: Query about network fault
        """
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an RCA assistant helping analyze network faults."},
                    {"role": "user", "content": query},
                ]
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"❌ RCA Analysis failed: {e}"


# If you want to test locally
if __name__ == "__main__":
    agent_manager = AgentManager()

    logs_dir = "./logs"
    rca_dir = "./rca_reports"

    # Auto process logs and index RCA reports
    print(agent_manager.process_logs_and_generate_rca(logs_dir, rca_dir))
    print(agent_manager.index_rca_reports(rca_dir))

    # Example search
    results = agent_manager.search_similar_rcas("Link failure due to routing issue", top_k=3)
    for match in results:
        print(f"\nSource: {match['metadata']['source']}")
        print(f"Snippet: {match['metadata']['content']}")
