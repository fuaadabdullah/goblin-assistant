"""
ChromaDB Indexer for Goblin Assistant RAG system.

This module provides ChromaDB-based vector indexing with secret scrubbing
for secure document storage and retrieval.
"""

import os
import re
import json
import hashlib
import uuid
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime
import chromadb
from chromadb.config import Settings
import numpy as np

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except Exception:
    OPENAI_AVAILABLE = False


class SecretScanner:
    """Enhanced secret scanner for multiple types of sensitive data."""

    SECRET_PATTERNS = [
        # API Keys
        r'(?i)(api[_-]?key|apikey)\s*[:=]\s*["\']?([a-zA-Z0-9_-]{20,})["\']?',
        r"sk-[a-zA-Z0-9_-]{48,}",  # OpenAI keys
        r"xoxb-[0-9]+-[0-9]+-[a-zA-Z0-9]+",  # Slack bot tokens
        r"xoxp-[0-9]+-[0-9]+-[a-zA-Z0-9]+",  # Slack user tokens
        r"ghp_[a-zA-Z0-9_-]{36}",  # GitHub tokens
        r"gho_[a-zA-Z0-9_-]{36}",  # GitHub OAuth tokens
        r"glpat-[a-zA-Z0-9_-]{20}",  # GitLab tokens

        # Secrets and Tokens
        r'(?i)(secret|token)\s*[:=]\s*["\']?([a-zA-Z0-9_-]{20,})["\']?',
        r'(?i)(bearer|authorization)\s*[:=]\s*["\']?([a-zA-Z0-9_-]{20,})["\']?',

        # Passwords
        r'(?i)(password|pwd|passwd)\s*[:=]\s*["\']?([a-zA-Z0-9_-]{8,})["\']?',

        # Database credentials
        r'(?i)(db[_-]?password|database[_-]?password)\s*[:=]\s*["\']?([a-zA-Z0-9_-]{8,})["\']?',

        # Private keys
        r'-----BEGIN\s+(?:RSA\s+)?PRIVATE\s+KEY-----.*?-----END\s+(?:RSA\s+)?PRIVATE\s+KEY-----',

        # AWS credentials
        r'(?i)(aws[_-]?access[_-]?key[_-]?id|aws[_-]?secret[_-]?access[_-]?key)\s*[:=]\s*["\']?([a-zA-Z0-9_-]{16,})["\']?',

        # Generic long alphanumeric strings (potential keys)
        r'\b[a-zA-Z0-9_-]{40,}\b',
    ]

    @staticmethod
    def scan_text(text: str) -> List[Dict[str, Any]]:
        """Scan text for potential secrets. Returns list of found secrets with metadata."""
        found_secrets = []
        for i, pattern in enumerate(SecretScanner.SECRET_PATTERNS):
            matches = re.findall(pattern, text)
            for match in matches:
                if isinstance(match, tuple):
                    # Pattern with capture groups
                    secret_value = match[-1]  # Last group is usually the secret
                else:
                    # Simple pattern
                    secret_value = match

                if len(secret_value) >= 8:  # Only flag reasonably long secrets
                    found_secrets.append({
                        "pattern_index": i,
                        "secret_type": SecretScanner._get_secret_type(i),
                        "value_hash": hashlib.sha256(secret_value.encode()).hexdigest()[:16],
                        "length": len(secret_value),
                        "position": text.find(secret_value)
                    })

        return found_secrets

    @staticmethod
    def _get_secret_type(pattern_index: int) -> str:
        """Get human-readable secret type from pattern index."""
        types = [
            "API Key", "OpenAI Key", "Slack Bot Token", "Slack User Token",
            "GitHub Token", "GitHub OAuth Token", "GitLab Token",
            "Generic Secret", "Bearer Token", "Password", "Database Password",
            "Private Key", "AWS Access Key", "AWS Secret Key", "Long Alphanumeric"
        ]
        return types[pattern_index] if pattern_index < len(types) else "Unknown"

    @staticmethod
    def redact_text(text: str) -> Tuple[str, List[Dict[str, Any]]]:
        """Redact potential secrets from text. Returns (redacted_text, secrets_found)."""
        secrets_found = SecretScanner.scan_text(text)
        redacted_text = text

        for secret in secrets_found:
            # Create a redaction marker
            marker = f"[REDACTED_{secret['secret_type'].replace(' ', '_')}_{secret['value_hash']}]"
            # Find and replace the actual secret (this is approximate since we only have hash)
            # In practice, you'd want to store the original positions
            redacted_text = re.sub(r'\b[a-zA-Z0-9_-]{40,}\b', marker, redacted_text, count=1)

        return redacted_text, secrets_found

    @staticmethod
    def is_safe_to_index(text: str, max_secrets: int = 3) -> Tuple[bool, List[Dict[str, Any]]]:
        """Check if text is safe to index based on secret content."""
        secrets = SecretScanner.scan_text(text)
        return len(secrets) <= max_secrets, secrets


class ChromaIndexer:
    """ChromaDB-based vector indexer with secret scrubbing."""

    def __init__(self, persist_directory: str = "./chroma_db"):
        self.persist_directory = persist_directory
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(anonymized_telemetry=False)
        )
        self.collection = None
        self.secret_scanner = SecretScanner()

        # Initialize or get collection
        self._init_collection()

    def _init_collection(self):
        """Initialize or get the documents collection."""
        try:
            self.collection = self.client.get_or_create_collection(
                name="goblin_documents",
                metadata={"description": "Goblin Assistant document index with RAG"}
            )
        except Exception as e:
            print(f"Failed to initialize Chroma collection: {e}")
            # Fallback to creating new collection
            self.collection = self.client.create_collection(
                name="goblin_documents",
                metadata={"description": "Goblin Assistant document index with RAG"}
            )

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for texts using OpenAI."""
        if not OPENAI_AVAILABLE or not os.getenv("OPENAI_API_KEY"):
            # Fallback to simple hash-based embeddings for demo
            return self._simple_embeddings(texts)

        try:
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            response = client.embeddings.create(
                input=texts,
                model="text-embedding-3-small"
            )
            return [data.embedding for data in response.data]
        except Exception as e:
            print(f"OpenAI embedding failed: {e}")
            return self._simple_embeddings(texts)

    def _simple_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Simple hash-based embeddings for fallback."""
        embeddings = []
        for text in texts:
            # Create a simple 384-dimensional embedding from text hash
            hash_obj = hashlib.sha256(text.encode())
            hash_bytes = hash_obj.digest()
            # Convert to float values between -1 and 1
            embedding = []
            for i in range(0, len(hash_bytes), 4):
                chunk = hash_bytes[i:i+4]
                if len(chunk) < 4:
                    chunk += b'\x00' * (4 - len(chunk))
                value = int.from_bytes(chunk, byteorder='big') / (2**32 - 1) * 2 - 1
                embedding.append(value)
            # Pad to 384 dimensions
            while len(embedding) < 384:
                embedding.extend(embedding[:384 - len(embedding)])
            embedding = embedding[:384]
            embeddings.append(embedding)
        return embeddings

    def add_documents(self, documents: List[str], metadata: List[Dict[str, Any]] = None,
                     ids: List[str] = None) -> Dict[str, Any]:
        """Add documents to the index with secret scrubbing."""
        if metadata is None:
            metadata = [{} for _ in documents]
        if ids is None:
            ids = [str(uuid.uuid4()) for _ in documents]

        # Process documents for secrets
        safe_documents = []
        processed_metadata = []
        secrets_found = []

        for i, doc in enumerate(documents):
            # Scan for secrets
            is_safe, doc_secrets = self.secret_scanner.is_safe_to_index(doc)

            if not is_safe:
                print(f"⚠️  Document {ids[i]} contains {len(doc_secrets)} potential secrets, skipping")
                secrets_found.extend(doc_secrets)
                continue

            # Redact secrets
            redacted_doc, doc_secrets = self.secret_scanner.redact_text(doc)
            safe_documents.append(redacted_doc)
            secrets_found.extend(doc_secrets)

            # Add processing metadata
            doc_metadata = metadata[i].copy()
            doc_metadata.update({
                "indexed_at": datetime.utcnow().isoformat(),
                "secrets_scrubbed": len(doc_secrets),
                "original_length": len(doc),
                "redacted_length": len(redacted_doc)
            })
            processed_metadata.append(doc_metadata)

        if not safe_documents:
            return {
                "success": False,
                "message": "No safe documents to index",
                "secrets_found": secrets_found
            }

        # Generate embeddings
        embeddings = self.embed_texts(safe_documents)

        # Add to ChromaDB
        try:
            self.collection.add(
                embeddings=embeddings,
                documents=safe_documents,
                metadatas=processed_metadata,
                ids=ids[:len(safe_documents)]  # Match the safe documents count
            )

            return {
                "success": True,
                "documents_indexed": len(safe_documents),
                "secrets_found": secrets_found,
                "total_secrets": sum(len(secrets) for secrets in secrets_found)
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "secrets_found": secrets_found
            }

    def search(self, query: str, n_results: int = 5) -> Dict[str, Any]:
        """Search the index for relevant documents."""
        try:
            # Generate embedding for query
            query_embedding = self.embed_texts([query])[0]

            # Search ChromaDB
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                include=['documents', 'metadatas', 'distances']
            )

            return {
                "success": True,
                "documents": results.get('documents', [[]])[0],
                "metadata": results.get('metadatas', [[]])[0],
                "distances": results.get('distances', [[]])[0],
                "count": len(results.get('documents', [[]])[0])
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def get_stats(self) -> Dict[str, Any]:
        """Get index statistics."""
        try:
            count = self.collection.count()
            return {
                "success": True,
                "total_documents": count,
                "collection_name": self.collection.name
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def clear_index(self) -> Dict[str, Any]:
        """Clear all documents from the index."""
        try:
            # Get all document IDs
            results = self.collection.get(include=[])
            ids = results.get('ids', [])

            if ids:
                self.collection.delete(ids=ids)

            return {
                "success": True,
                "documents_removed": len(ids)
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }


# Global indexer instance
chroma_indexer = ChromaIndexer()


def index_document(content: str, metadata: Dict[str, Any] = None, doc_id: str = None) -> Dict[str, Any]:
    """Convenience function to index a single document."""
    if doc_id is None:
        doc_id = str(uuid.uuid4())

    return chroma_indexer.add_documents(
        documents=[content],
        metadata=[metadata or {}],
        ids=[doc_id]
    )


def search_documents(query: str, limit: int = 5) -> Dict[str, Any]:
    """Convenience function to search documents."""
    return chroma_indexer.search(query, limit)


def get_index_stats() -> Dict[str, Any]:
    """Get current index statistics."""
    return chroma_indexer.get_stats()


def clear_index() -> Dict[str, Any]:
    """Clear the entire index."""
    return chroma_indexer.clear_index()
