"""Retrieval memory with optional sentence-transformers embeddings."""

from __future__ import annotations

import math
import time
from typing import Any, Dict, List, Optional


class VectorMemoryStore:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2", *, enable_embeddings: bool = False):
        self.documents: List[Dict[str, Any]] = []
        self._model = None
        self._model_name = model_name
        self._embeddings_enabled = enable_embeddings
        self._model_attempted = False
        self._embeddings: List[Any] = []

    def add_memory(self, doc_id: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        document = {"id": doc_id, "content": content, "metadata": metadata or {}, "timestamp": time.time()}
        self.documents.append(document)
        self._embeddings.append(self._encode(content) if self._get_model() is not None else None)

    add = add_memory

    def _get_model(self):
        if not self._embeddings_enabled:
            return None
        if self._model_attempted:
            return self._model
        self._model_attempted = True
        try:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self._model_name)
        except Exception:
            self._model = None
        return self._model

    def _encode(self, text: str):
        model = self._get_model()
        if model is None:
            return None
        vector = model.encode(text, convert_to_numpy=True)
        norm = float((vector**2).sum() ** 0.5)
        return vector / norm if norm else vector

    @staticmethod
    def _lexical_score(query: str, content: str) -> float:
        query_words = set(query.lower().split())
        content_words = content.lower().split()
        if not query_words or not content_words:
            return 0.0
        overlap = sum(1 for word in content_words if word in query_words)
        return overlap / (math.sqrt(len(content_words)) * math.sqrt(len(query_words)) + 1e-9)

    def search(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        scored = []
        query_vector = self._encode(query)
        for document, embedding in zip(self.documents, self._embeddings):
            if query_vector is not None and embedding is not None:
                score = float(query_vector.dot(embedding))
            else:
                score = self._lexical_score(query, str(document["content"]))
            if score > 0:
                scored.append((score, document))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [{**document, "score": score} for score, document in scored[:top_k]]
