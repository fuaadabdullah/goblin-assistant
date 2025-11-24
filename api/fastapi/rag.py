"""Enhanced RAG utilities for Goblin Assistant FastAPI.

This module provides RAG functionality with persistent storage and secret scanning.
Uses a simple file-based approach for persistence instead of ChromaDB to keep dependencies light.
"""

import os
import re
import json
import hashlib
import numpy as np
from typing import List, Dict, Optional, Any
from datetime import datetime
import pickle

try:
    from openai import OpenAI

    OPENAI_AVAILABLE = True
except Exception:
    OPENAI_AVAILABLE = False


class SecretScanner:
    """Scans text for potential secrets before indexing."""

    SECRET_PATTERNS = [
        r'(?i)(api[_-]?key|apikey)\s*[:=]\s*["\']?([a-zA-Z0-9_-]{20,})["\']?',
        r'(?i)(secret|token)\s*[:=]\s*["\']?([a-zA-Z0-9_-]{20,})["\']?',
        r'(?i)(password|pwd)\s*[:=]\s*["\']?([a-zA-Z0-9_-]{8,})["\']?',
        r"sk-[a-zA-Z0-9_-]{48,}",  # OpenAI keys
        r"ghp_[a-zA-Z0-9_-]{36}",  # GitHub tokens
    ]

    @staticmethod
    def scan_text(text: str) -> List[str]:
        """Scan text for potential secrets. Returns list of found patterns."""
        found_secrets = []
        for pattern in SecretScanner.SECRET_PATTERNS:
            matches = re.findall(pattern, text)
            found_secrets.extend(matches)
        return found_secrets

    @staticmethod
    def redact_text(text: str) -> str:
        """Redact potential secrets from text."""
        for pattern in SecretScanner.SECRET_PATTERNS:
            text = re.sub(pattern, "[REDACTED_SECRET]", text)
        return text


class SimpleVectorDB:
    """Simple file-based vector database."""

    def __init__(self, persist_dir: str = "./vector_db"):
        self.persist_dir = persist_dir
        self.documents = []
        self.embeddings = []
        self.metadata = []
        self.index_file = os.path.join(persist_dir, "index.pkl")

        os.makedirs(persist_dir, exist_ok=True)
        self.load_index()

    def load_index(self):
        """Load index from disk."""
        if os.path.exists(self.index_file):
            try:
                with open(self.index_file, "rb") as f:
                    data = pickle.load(f)
                    self.documents = data.get("documents", [])
                    self.embeddings = data.get("embeddings", [])
                    self.metadata = data.get("metadata", [])
            except Exception as e:
                print(f"Failed to load index: {e}")

    def save_index(self):
        """Save index to disk."""
        try:
            data = {
                "documents": self.documents,
                "embeddings": self.embeddings,
                "metadata": self.metadata,
            }
            with open(self.index_file, "wb") as f:
                pickle.dump(data, f)
        except Exception as e:
            print(f"Failed to save index: {e}")

    def embed_text(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for texts."""
        if OPENAI_AVAILABLE and os.getenv("OPENAI_API_KEY"):
            try:
                client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
                response = client.embeddings.create(
                    input=texts, model="text-embedding-3-small"
                )
                return [data.embedding for data in response.data]
            except Exception as e:
                print(f"OpenAI embedding failed: {e}")

        # Fallback: simple hash-based embeddings
        embeddings = []
        for text in texts:
            # Create a deterministic embedding from text hash
            hash_obj = hashlib.md5(text.encode())
            hash_bytes = hash_obj.digest()
            # Convert to float list
            embedding = [float(b) / 255.0 for b in hash_bytes] * 4  # 128 dims
            embeddings.append(embedding[:128])
        return embeddings

    def add_document(self, doc_id: str, content: str, metadata: Dict[str, Any]) -> bool:
        """Add a document after secret scanning."""
        # Scan for secrets
        secrets_found = SecretScanner.scan_text(content)
        if secrets_found:
            print(f"⚠️ Secrets detected in document {doc_id}, skipping indexing")
            return False

        # Redact any potential secrets
        safe_content = SecretScanner.redact_text(content)

        # Generate embedding
        embeddings = self.embed_text([safe_content])
        embedding = embeddings[0]

        # Add to index
        self.documents.append(safe_content)
        self.embeddings.append(embedding)
        self.metadata.append(metadata)

        # Save to disk
        self.save_index()
        return True

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Search for similar documents."""
        if not self.embeddings:
            return []

        # Generate query embedding
        query_embedding = self.embed_text([query])[0]

        # Calculate cosine similarities
        similarities = []
        for i, doc_embedding in enumerate(self.embeddings):
            # Cosine similarity
            dot_product = np.dot(query_embedding, doc_embedding)
            norm_query = np.linalg.norm(query_embedding)
            norm_doc = np.linalg.norm(doc_embedding)

            if norm_query == 0 or norm_doc == 0:
                similarity = 0.0
            else:
                similarity = dot_product / (norm_query * norm_doc)

            similarities.append((similarity, i))

        # Sort by similarity
        similarities.sort(key=lambda x: x[0], reverse=True)

        # Return top-k results
        results = []
        for similarity, idx in similarities[:top_k]:
            results.append(
                {
                    "content": self.documents[idx],
                    "metadata": self.metadata[idx],
                    "score": float(similarity),
                    "rank": len(results) + 1,
                }
            )

        return results


# Global vector database instance
vector_db = SimpleVectorDB()


def get_vector_db() -> SimpleVectorDB:
    """Get the global vector database instance."""
    return vector_db


def add_document(id: str, text: str, metadata: Optional[Dict] = None):
    """Add a doc to the vector database."""
    return vector_db.add_document(id, text, metadata or {})


def retrieve(query: str, k: int = 4):
    """Retrieve relevant documents for a query."""
    return vector_db.search(query, top_k=k)


def embed_text(texts: List[str]) -> List[List[float]]:
    """Generate embeddings for texts."""
    return vector_db.embed_text(texts)
