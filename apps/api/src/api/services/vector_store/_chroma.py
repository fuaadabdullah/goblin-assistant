"""ChromaStore — optional vector store backed by a Chroma HTTP server.

Chroma's own deployment documentation recommends connecting via its HTTP API
when running as a server, with data stored on a persistent volume.  This
implementation talks to Chroma over HTTP only — it never touches the local
filesystem, which means it is safe on ephemeral runtimes.

Set CHROMA_URL (e.g. https://chroma.myinfra.internal) to enable this backend.
Leave it unset and the factory will use PgVectorStore instead.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx

from ._protocol import VectorSearchResult

logger = logging.getLogger(__name__)


class ChromaStore:
    """Vector store that targets a Chroma HTTP server.

    This is an optional implementation.  It is selected by the factory when
    CHROMA_URL is set.  All calls go over HTTP — no local client state or
    filesystem access.
    """

    def __init__(self, url: str, collection_name: str = "goblin_rag") -> None:
        self._base = url.rstrip("/")
        self._collection_name = collection_name

    # ── Internal HTTP helpers ───────────────────────────────────────────────

    async def _ensure_collection(self, client: httpx.AsyncClient) -> str:
        """Return the collection UUID, creating the collection if it doesn't exist."""
        r = await client.post(
            f"{self._base}/api/v1/collections",
            json={"name": self._collection_name, "get_or_create": True},
        )
        r.raise_for_status()
        return r.json()["id"]

    async def _get_collection_id(self, client: httpx.AsyncClient) -> Optional[str]:
        r = await client.get(f"{self._base}/api/v1/collections/{self._collection_name}")
        if r.status_code == 404:
            return None
        r.raise_for_status()
        return r.json()["id"]

    # ── VectorStore protocol ────────────────────────────────────────────────

    async def upsert(
        self,
        doc_id: str,
        content: str,
        embedding: List[float],
        user_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        meta = {**(metadata or {}), "user_id": user_id}
        async with httpx.AsyncClient(timeout=10.0) as client:
            cid = await self._ensure_collection(client)
            await client.post(
                f"{self._base}/api/v1/collections/{cid}/upsert",
                json={
                    "ids": [doc_id],
                    "embeddings": [embedding],
                    "documents": [content],
                    "metadatas": [meta],
                },
            )

    async def query(
        self,
        embedding: List[float],
        user_id: str,
        n_results: int = 10,
    ) -> List[VectorSearchResult]:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                cid = await self._get_collection_id(client)
                if cid is None:
                    return []
                r = await client.post(
                    f"{self._base}/api/v1/collections/{cid}/query",
                    json={
                        "query_embeddings": [embedding],
                        "n_results": n_results,
                        "where": {"user_id": user_id},
                        "include": ["documents", "metadatas", "distances"],
                    },
                )
                r.raise_for_status()
                data = r.json()

            results = []
            ids = data.get("ids", [[]])[0]
            docs = data.get("documents", [[]])[0]
            metas = data.get("metadatas", [[]])[0]
            dists = data.get("distances", [[]])[0]

            for rid, content, meta, dist in zip(ids, docs, metas, dists):
                results.append(
                    VectorSearchResult(
                        id=rid,
                        content=content,
                        score=max(0.0, 1.0 - float(dist)),
                        metadata=dict(meta or {}),
                    )
                )
            return results
        except Exception as exc:
            logger.error("Chroma query failed: %s", exc)
            return []

    async def delete_user_data(self, user_id: str) -> Dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                cid = await self._get_collection_id(client)
                if cid is None:
                    return {"success": True, "deleted_count": 0, "user_id": user_id}

                ids_r = await client.post(
                    f"{self._base}/api/v1/collections/{cid}/get",
                    json={"where": {"user_id": user_id}, "include": []},
                )
                ids_r.raise_for_status()
                ids = ids_r.json().get("ids", [])

                if ids:
                    del_r = await client.post(
                        f"{self._base}/api/v1/collections/{cid}/delete",
                        json={"ids": ids},
                    )
                    del_r.raise_for_status()

            return {
                "success": True,
                "deleted_count": len(ids),
                "user_id": user_id,
                "deleted_at": datetime.utcnow().isoformat(),
            }
        except Exception as exc:
            logger.error("Chroma delete failed for user %s: %s", user_id, exc)
            return {"success": False, "error": str(exc), "user_id": user_id}

    async def export_user_data(self, user_id: str) -> Dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                cid = await self._get_collection_id(client)
                if cid is None:
                    return {
                        "success": True,
                        "document_count": 0,
                        "documents": [],
                        "user_id": user_id,
                        "exported_at": datetime.utcnow().isoformat(),
                    }
                r = await client.post(
                    f"{self._base}/api/v1/collections/{cid}/get",
                    json={
                        "where": {"user_id": user_id},
                        "include": ["documents", "metadatas"],
                    },
                )
                r.raise_for_status()
                data = r.json()

            documents = [
                {"doc_id": rid, "content": content, "metadata": meta}
                for rid, content, meta in zip(
                    data.get("ids", []),
                    data.get("documents", []),
                    data.get("metadatas", []),
                )
            ]
            return {
                "success": True,
                "user_id": user_id,
                "document_count": len(documents),
                "documents": documents,
                "exported_at": datetime.utcnow().isoformat(),
            }
        except Exception as exc:
            logger.error("Chroma export failed for user %s: %s", user_id, exc)
            return {"success": False, "error": str(exc), "user_id": user_id}

    async def get_user_document_count(self, user_id: str) -> int:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                cid = await self._get_collection_id(client)
                if cid is None:
                    return 0
                r = await client.post(
                    f"{self._base}/api/v1/collections/{cid}/get",
                    json={"where": {"user_id": user_id}, "include": []},
                )
                r.raise_for_status()
                return len(r.json().get("ids", []))
        except Exception as exc:
            logger.error("Chroma count failed for user %s: %s", user_id, exc)
            return 0

    async def health(self) -> Dict[str, Any]:
        probes = [
            f"{self._base}/api/v1/heartbeat",
            f"{self._base}/health",
            self._base,
        ]
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                for url in probes:
                    try:
                        r = await client.get(url)
                        if r.status_code == 200:
                            payload = r.json() if r.text else {}
                            return {
                                "status": "healthy",
                                "backend": "chroma",
                                "url": self._base,
                                "response": payload,
                            }
                    except Exception:
                        continue
        except Exception as exc:
            return {"status": "degraded", "backend": "chroma", "url": self._base, "error": str(exc)}

        return {
            "status": "degraded",
            "backend": "chroma",
            "url": self._base,
            "error": "all probes failed",
        }
