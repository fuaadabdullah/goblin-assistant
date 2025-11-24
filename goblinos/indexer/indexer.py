"""
Vector indexer for Goblin Assistant.
Handles document chunking, embedding, and vector storage.
"""

import os
import json
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
import hashlib

try:
    from openai import OpenAI

    OPENAI_AVAILABLE = True
except Exception:
    OPENAI_AVAILABLE = False

from .secret_scrub import SecretScanner


@dataclass
class DocumentChunk:
    """A chunk of document with metadata."""

    content: str
    file_path: str
    start_line: int
    end_line: int
    chunk_id: str
    embedding: Optional[List[float]] = None


class VectorIndexer:
    """Vector indexer using Chroma for development, extensible to other backends."""

    def __init__(
        self, persist_dir: str = "./data/index", embedding_provider: str = "openai"
    ):
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)

        self.index_path = self.persist_dir / "index.json"
        self.chunks: Dict[str, DocumentChunk] = {}
        self.embedding_provider = embedding_provider

        # Simple in-memory vector storage (replace with Chroma/Weaviate for production)
        self.vectors: Dict[str, List[float]] = {}
        self.chunk_overlap = 50  # Token overlap between chunks

        # Initialize SecretScanner
        self.secret_scanner = SecretScanner()

    async def index_file(
        self, file_path: str, content: str, commit_sha: Optional[str] = None
    ) -> int:
        """
        Index a file by chunking and embedding.
        Returns number of chunks created.
        """
        # Check if file needs secret scanning
        if not await self._scan_secrets(content):
            print(f"⚠️  Skipping {file_path} - potential secrets detected")
            return 0

        # Chunk the content
        chunks = self._chunk_content(content, file_path)

        # Generate embeddings
        await self._embed_chunks(chunks)

        # Store chunks
        chunk_count = 0
        for chunk in chunks:
            if chunk.embedding:  # Only store chunks with embeddings
                self.chunks[chunk.chunk_id] = chunk
                self.vectors[chunk.chunk_id] = chunk.embedding
                chunk_count += 1

        print(f"✅ Indexed {file_path}: {chunk_count} chunks")
        return chunk_count

    async def index_changes(self, changes: List[Dict[str, Any]], repo: str):
        """Index changed files from CI/webhook."""
        total_chunks = 0

        for change in changes:
            file_path = change.get("file_path", "")
            content = change.get("content", "")
            commit_sha = change.get("commit_sha")

            if content and self._should_index_file(file_path):
                chunks = await self.index_file(file_path, content, commit_sha)
                total_chunks += chunks

        # Save index
        await self.save_index()

        print(f"✅ Indexed {len(changes)} changes: {total_chunks} total chunks")

    def _chunk_content(self, content: str, file_path: str) -> List[DocumentChunk]:
        """Chunk content by functions/classes with overlap."""
        chunks = []
        lines = content.split("\n")

        # For code files, try to chunk by functions/classes
        if self._is_code_file(file_path):
            chunks = self._chunk_by_symbols(content, file_path)
        else:
            # For other files, use line-based chunking
            chunks = self._chunk_by_lines(lines, file_path)

        return chunks

    def _chunk_by_symbols(self, content: str, file_path: str) -> List[DocumentChunk]:
        """Chunk code by functions, classes, etc."""
        chunks = []
        lines = content.split("\n")

        current_chunk_lines = []
        current_start_line = 0
        in_block = False

        for i, line in enumerate(lines):
            # Check if this line starts a new symbol
            if self._is_symbol_start(line):
                # Save previous chunk if it exists
                if current_chunk_lines:
                    chunk_content = "\n".join(current_chunk_lines)
                    if len(chunk_content.strip()) > 50:  # Minimum chunk size
                        chunks.append(
                            self._create_chunk(
                                chunk_content, file_path, current_start_line, i
                            )
                        )

                # Start new chunk
                current_chunk_lines = [line]
                current_start_line = i
                in_block = True
            elif in_block:
                current_chunk_lines.append(line)

                # Check if block ends
                if line.strip().endswith("}") or line.strip().endswith("end"):
                    # Add some overlap
                    overlap_end = min(i + self.chunk_overlap, len(lines))
                    for j in range(i + 1, overlap_end):
                        if j < len(lines):
                            current_chunk_lines.append(lines[j])

                    chunk_content = "\n".join(current_chunk_lines)
                    chunks.append(
                        self._create_chunk(
                            chunk_content, file_path, current_start_line, overlap_end
                        )
                    )

                    current_chunk_lines = []
                    in_block = False

        # Add remaining content
        if current_chunk_lines:
            chunk_content = "\n".join(current_chunk_lines)
            if len(chunk_content.strip()) > 50:
                chunks.append(
                    self._create_chunk(
                        chunk_content, file_path, current_start_line, len(lines)
                    )
                )

        return chunks

    def _chunk_by_lines(self, lines: List[str], file_path: str) -> List[DocumentChunk]:
        """Simple line-based chunking for non-code files."""
        chunks = []
        chunk_size = 50  # Lines per chunk
        overlap = 10

        for i in range(0, len(lines), chunk_size - overlap):
            end_idx = min(i + chunk_size, len(lines))
            chunk_lines = lines[i:end_idx]
            chunk_content = "\n".join(chunk_lines)

            if len(chunk_content.strip()) > 50:
                chunks.append(self._create_chunk(chunk_content, file_path, i, end_idx))

        return chunks

    def _create_chunk(
        self, content: str, file_path: str, start_line: int, end_line: int
    ) -> DocumentChunk:
        """Create a document chunk."""
        chunk_id = hashlib.md5(
            f"{file_path}:{start_line}:{end_line}".encode()
        ).hexdigest()

        return DocumentChunk(
            content=content,
            file_path=file_path,
            start_line=start_line,
            end_line=end_line,
            chunk_id=chunk_id,
        )

    def _is_symbol_start(self, line: str) -> bool:
        """Check if line starts a code symbol."""
        line = line.strip()
        return (
            line.startswith("def ")
            or line.startswith("class ")
            or line.startswith("function ")
            or line.startswith("const ")
            and ("=" in line or "(" in line)
            or line.startswith("export ")
            or line.startswith("public ")
            or line.startswith("private ")
        )

    def _is_code_file(self, file_path: str) -> bool:
        """Check if file is a code file."""
        code_extensions = {
            ".py",
            ".js",
            ".ts",
            ".java",
            ".cpp",
            ".c",
            ".go",
            ".rs",
            ".php",
        }
        return any(file_path.endswith(ext) for ext in code_extensions)

    async def _embed_chunks(self, chunks: List[DocumentChunk]):
        """Generate embeddings for chunks."""
        if not chunks:
            return

        try:
            # Generate embeddings using OpenAI
            if OPENAI_AVAILABLE and os.getenv("OPENAI_API_KEY"):
                texts = [chunk.content for chunk in chunks]
                client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
                response = client.embeddings.create(
                    input=texts, model="text-embedding-3-small"
                )
                for chunk, data in zip(chunks, response.data):
                    chunk.embedding = data.embedding
            else:
                # Fallback to dummy embeddings if OpenAI not available
                print("⚠️  OpenAI not available, using dummy embeddings")
                for chunk in chunks:
                    chunk.embedding = [
                        0.1
                    ] * 1536  # Match text-embedding-3-small dimensions

        except Exception as e:
            print(f"⚠️  Embedding failed: {e}, using dummy embeddings")
            # Fallback to dummy embeddings
            for chunk in chunks:
                chunk.embedding = [
                    0.1
                ] * 1536  # Match text-embedding-3-small dimensions

    async def search(
        self, query_embedding: List[float], top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """Search for similar chunks."""
        if not query_embedding or not self.vectors:
            return []

        results = []
        for chunk_id, vector in self.vectors.items():
            if len(vector) == len(query_embedding):
                # Simple cosine similarity (replace with proper vector search)
                similarity = self._cosine_similarity(query_embedding, vector)
                chunk = self.chunks[chunk_id]

                results.append(
                    {
                        "chunk_id": chunk_id,
                        "content": chunk.content,
                        "file_path": chunk.file_path,
                        "start_line": chunk.start_line,
                        "end_line": chunk.end_line,
                        "score": similarity,
                    }
                )

        # Sort by similarity and return top_k
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    async def search_text(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search the index for relevant chunks using text matching."""
        if not self.chunks:
            return []

        # Simple text-based search for now (replace with vector search)
        query_lower = query.lower()
        results = []

        for chunk in self.chunks.values():
            content_lower = chunk.content.lower()

            # Simple relevance scoring
            if query_lower in content_lower:
                score = 1.0
                # Bonus for exact matches
                if query in chunk.content:
                    score += 0.5
                # Bonus for function/class definitions
                if any(
                    word in chunk.content for word in ["def ", "class ", "function"]
                ):
                    score += 0.2

                results.append(
                    {
                        "content": chunk.content,
                        "file_path": chunk.file_path,
                        "start_line": chunk.start_line,
                        "end_line": chunk.end_line,
                        "score": score,
                    }
                )

        # Sort by score and limit results
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        dot_product = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5

        if norm_a == 0 or norm_b == 0:
            return 0

        return dot_product / (norm_a * norm_b)

    async def _scan_secrets(self, content: str) -> bool:
        """Scan content for secrets. Returns True if safe to index."""
        is_safe, findings = self.secret_scanner.scan_content(content)

        if not is_safe:
            print("⚠️  Secret scan findings:")
            for finding in findings[:5]:  # Show first 5 findings
                print(f"  • {finding['type']} at line {finding['line']}")
            if len(findings) > 5:
                print(f"  • ... and {len(findings) - 5} more")

        return is_safe

    def _should_index_file(self, file_path: str) -> bool:
        """Check if file should be indexed."""
        # Skip common non-content files
        skip_patterns = [
            ".git/",
            "node_modules/",
            "__pycache__/",
            ".DS_Store",
            "*.log",
            "*.tmp",
            "*.swp",
            "*.lock",
        ]

        for pattern in skip_patterns:
            if pattern in file_path:
                return False

        return True

    async def save_index(self):
        """Save index to disk."""
        index_data = {
            "chunks": {
                chunk_id: {
                    "content": chunk.content,
                    "file_path": chunk.file_path,
                    "start_line": chunk.start_line,
                    "end_line": chunk.end_line,
                    "embedding": chunk.embedding,
                }
                for chunk_id, chunk in self.chunks.items()
            },
            "vectors": self.vectors,
        }

        with open(self.index_path, "w") as f:
            json.dump(index_data, f, indent=2)

    async def load_index(self):
        """Load index from disk."""
        if not self.index_path.exists():
            return

        try:
            with open(self.index_path, "r") as f:
                index_data = json.load(f)

            # Restore chunks
            for chunk_id, chunk_data in index_data.get("chunks", {}).items():
                self.chunks[chunk_id] = DocumentChunk(
                    content=chunk_data["content"],
                    file_path=chunk_data["file_path"],
                    start_line=chunk_data["start_line"],
                    end_line=chunk_data["end_line"],
                    chunk_id=chunk_id,
                    embedding=chunk_data.get("embedding"),
                )

            # Restore vectors
            self.vectors = index_data.get("vectors", {})

            print(f"✅ Loaded index: {len(self.chunks)} chunks")

        except Exception as e:
            print(f"⚠️  Failed to load index: {e}")

    async def get_stats(self) -> Dict[str, Any]:
        """Get index statistics."""
        return {
            "total_chunks": len(self.chunks),
            "total_files": len(set(chunk.file_path for chunk in self.chunks.values())),
            "index_size_mb": self.index_path.stat().st_size / (1024 * 1024)
            if self.index_path.exists()
            else 0,
        }
