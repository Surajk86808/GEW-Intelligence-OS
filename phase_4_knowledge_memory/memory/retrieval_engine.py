from __future__ import annotations

from typing import Any

from .config import ENABLE_HYBRID_KEYWORD_BOOST, MIN_RELEVANCE_SCORE, TOP_K_RETRIEVAL
from .embedding_engine import EmbeddingEngine
from .vector_engine import VectorEngine


class RetrievalEngine:
    def __init__(self, embedding_engine: EmbeddingEngine, vector_engine: VectorEngine) -> None:
        self.embedding_engine = embedding_engine
        self.vector_engine = vector_engine

    def retrieve(self, query: str, filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        query_vector = self.embedding_engine.embed_text(query)
        raw_results = self.vector_engine.search(query_vector, TOP_K_RETRIEVAL * 3, filters=filters, query_text=query)
        reranked = self._rerank(query, raw_results)
        return [item for item in reranked if item["score"] >= MIN_RELEVANCE_SCORE][:TOP_K_RETRIEVAL]

    def _rerank(self, query: str, results: list[dict[str, Any]]) -> list[dict[str, Any]]:
        query_terms = {term.lower() for term in query.split() if term.strip()}
        reranked = []
        for result in results:
            metadata = result["metadata"]
            text = str(metadata.get("text", "")).lower()
            keyword_hits = sum(1 for term in query_terms if term in text)
            boosted_score = float(result["score"])
            if ENABLE_HYBRID_KEYWORD_BOOST:
                boosted_score += min(0.2, keyword_hits * 0.02)
            reranked.append({**result, "score": round(boosted_score, 6), "keyword_hits": keyword_hits})
        reranked.sort(key=lambda item: (item["score"], item["keyword_hits"]), reverse=True)
        return reranked
