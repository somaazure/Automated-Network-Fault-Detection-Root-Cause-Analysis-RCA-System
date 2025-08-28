"""
rca_vector_store.py: Manages Pinecone integration and embeddings, chunks RCA reports, indexes them, 
and performs semantic search/RAG via answer_query(). 
Uses OpenAI embeddings and returns consolidated answers with sources.
"""
import os
from typing import List, Dict
from dotenv import load_dotenv
from openai import OpenAI
from pinecone import Pinecone

load_dotenv(override=True)

class RCAVectorStore:
    def __init__(self):
        # Load API keys and index name
        self.api_key = os.getenv("PINECONE_API_KEY")
        self.index_name = os.getenv("PINECONE_INDEX", "rca-index")
        self.namespace = os.getenv("PINECONE_NAMESPACE", "rca-logs")

        # Initialize OpenAI and Pinecone clients
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.pc = Pinecone(api_key=self.api_key)

        # Reuse existing index if present
        self._connect_to_index()

    def _connect_to_index(self):
        """Connect to an existing Pinecone index, don't try to create a new one."""
        existing_indexes = [idx["name"] for idx in self.pc.list_indexes()]

        if self.index_name not in existing_indexes:
            raise RuntimeError(
                f"⚠️ Pinecone index '{self.index_name}' does not exist.\n"
                f"Please create it manually from Pinecone dashboard: https://app.pinecone.io"
            )
        else:
            print(f"✅ Connected to Pinecone index '{self.index_name}'.")

        self.index = self.pc.Index(self.index_name)

    def _embed_text(self, text: str) -> List[float]:
        """Generate embedding for a given text using OpenAI."""
        try:
            response = self.client.embeddings.create(
                input=text,
                model="text-embedding-3-small"
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"❌ Error generating embedding: {e}")
            return []

    def _chunk_text(self, text: str, chunk_size: int = 800) -> List[str]:
        """
        Split text into chunks to improve semantic search.
        Default chunk size = 800 characters.
        """
        words = text.split()
        chunks = []
        current_chunk = []

        for word in words:
            if len(" ".join(current_chunk + [word])) <= chunk_size:
                current_chunk.append(word)
            else:
                chunks.append(" ".join(current_chunk))
                current_chunk = [word]

        if current_chunk:
            chunks.append(" ".join(current_chunk))

        return chunks

    def chunk_and_store_reports(self, rca_dir: str) -> str:
        """
        Process RCA reports, chunk them, generate embeddings, and store them in Pinecone.
        """
        if not os.path.exists(rca_dir):
            return "⚠️ RCA reports folder not found!"

        files = [f for f in os.listdir(rca_dir) if f.endswith(".txt")]
        if not files:
            return "⚠️ No RCA reports found to index."

        vectors = []
        counter = 0

        for file in files:
            file_path = os.path.join(rca_dir, file)
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            chunks = self._chunk_text(content)

            for idx, chunk in enumerate(chunks):
                embedding = self._embed_text(chunk)
                if not embedding:
                    continue

                vector_id = f"{file}_{idx}"
                vectors.append({
                    "id": vector_id,
                    "values": embedding,
                    "metadata": {
                        "source": file,
                        "chunk": idx,
                        "content": chunk
                    }
                })
                counter += 1

        if vectors:
            self.index.upsert(vectors=vectors, namespace=self.namespace)
            return f"✅ Successfully indexed {counter} chunks from {len(files)} RCA reports."
        else:
            return "⚠️ No chunks were indexed."

    def search_similar(self, query: str, top_k: int = 5) -> List[Dict]:
        """
        Search Pinecone index for chunks similar to a given query.
        """
        embedding = self._embed_text(query)
        if not embedding:
            return []

        try:
            results = self.index.query(
                vector=embedding,
                top_k=top_k,
                include_metadata=True,
                namespace=self.namespace
            )

            return results.matches
        except Exception as e:
            print(f"❌ Search error: {e}")
            return []

    def answer_query(self, query: str, top_k: int = 5) -> Dict:
        matches = self.search_similar(query, top_k=top_k)
        if not matches:
            return {"answer": "No relevant results found.", "sources": []}

        context_snippets = []
        sources = []
        for m in matches:
            md = m["metadata"] if isinstance(m, dict) else m.metadata
            src = md.get("source", "Unknown")
            txt = md.get("content", "")
            context_snippets.append(f"Source: {src}\nContent: {txt}")
            sources.append(src)

        context = "\n\n".join(context_snippets)
        prompt = (
            "You are an expert network RCA assistant. Based ONLY on the provided context, "
            "write a concise consolidated answer as bullet points.\n"
            "Formatting requirements:\n"
            "- Use short bullet points (one line each).\n"
            "- Start each key item with a bold label where helpful (e.g., **Severity**, **Root cause**).\n"
            "- Include brief inline citations like [source: <filename>] on bullets they support.\n"
            "- If information is insufficient, include a final bullet noting what's missing.\n\n"
            f"Question: {query}\n\nContext:\n{context}"
        )

        try:
            resp = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
            )
            answer = resp.choices[0].message.content
        except Exception as e:
            answer = f"Error generating answer: {e}"

        unique_sources = sorted(list(dict.fromkeys(sources)))
        return {"answer": answer, "sources": unique_sources}
