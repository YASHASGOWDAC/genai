"""
Retriever module for Government Scheme Assistant.
Implements hybrid retrieval (Dense Semantic + Keyword / Lexical Matching) with metadata filtering.

Optimized with:
- Cached vector store integration (avoids Chroma re-initialization)
- Latency monitoring for retrieval operations
"""

import re
import logging
from typing import List, Dict, Any, Optional

try:
    from rag.vector_store import GovernmentSchemeVectorStore, get_cached_vector_store
except ImportError:
    pass

try:
    from utils.performance_monitor import TimingContext
except ImportError:
    class TimingContext:
        def __init__(self, *args, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass

logger = logging.getLogger(__name__)


class GovernmentSchemeRetriever:
    """
    Hybrid retriever combining semantic embeddings with keyword frequency and scheme name boosts.
    """
    def __init__(self, vector_store: Optional['GovernmentSchemeVectorStore'] = None):
        if vector_store:
            self.vector_store = vector_store
        else:
            try:
                self.vector_store = get_cached_vector_store()
            except Exception:
                from rag.vector_store import GovernmentSchemeVectorStore
                self.vector_store = GovernmentSchemeVectorStore()

    def _compute_keyword_score(self, query: str, content: str, scheme_name: str = "") -> float:
        """Calculate lexical overlap bonus for domain terms and scheme titles."""
        query_terms = set(re.findall(r'\b[a-zA-Z0-9]{3,}\b', query.lower()))
        if not query_terms:
            return 0.0

        content_lower = content.lower()
        matched = 0
        for term in query_terms:
            if term in content_lower:
                matched += 1

        term_ratio = matched / len(query_terms)

        # High priority boost if query mentions specific scheme name or acronym
        scheme_boost = 0.0
        if scheme_name:
            scheme_clean = re.sub(r'[^a-zA-Z0-9\s]', ' ', scheme_name.lower()).split()
            for token in scheme_clean:
                if len(token) >= 3 and token in query.lower():
                    scheme_boost = 0.3
                    break

        return min(1.0, term_ratio + scheme_boost)

    def retrieve(self, query: str, top_k: int = 5, 
                 category: Optional[str] = None, 
                 level: Optional[str] = None,
                 min_similarity_threshold: float = 0.30) -> List[Dict[str, Any]]:
        """
        Execute hybrid retrieval with metadata filtering and reranking.
        """
        if not query or not query.strip():
            return []

        with TimingContext("vector_retrieval", f"hybrid_retrieve_k{top_k}"):
            # Build metadata filter if specified
            where_filter = {}
            if category and category != "All Categories":
                where_filter["category"] = category
            if level and level != "All":
                where_filter["level"] = level

            where_arg = where_filter if where_filter else None

            # Fetch extra candidates from vector store for reranking
            fetch_k = max(top_k * 2, 8)
            raw_results = self.vector_store.query_similar(query=query, top_k=fetch_k, where=where_arg)

            if not raw_results:
                return []

            # Rerank using hybrid score fusion
            reranked = []
            for item in raw_results:
                semantic_score = item.get("similarity", 0.0)
                content = item.get("content", "")
                meta = item.get("metadata", {})
                scheme_name = meta.get("scheme_name", "")

                lexical_score = self._compute_keyword_score(query, content, scheme_name)
                
                # Hybrid score: 65% dense semantic similarity + 35% lexical keyword match
                hybrid_score = round((0.65 * semantic_score) + (0.35 * lexical_score), 4)

                item["hybrid_score"] = hybrid_score
                item["lexical_score"] = lexical_score

                if hybrid_score >= min_similarity_threshold or semantic_score >= 0.35:
                    reranked.append(item)

            # Sort by hybrid score descending
            reranked.sort(key=lambda x: x["hybrid_score"], reverse=True)
            top_results = reranked[:top_k]

            return top_results

    def format_context_for_llm(self, retrieved_chunks: List[Dict[str, Any]]) -> str:
        """
        Format retrieved chunks into a structured context block for LLM prompt ingestion.
        """
        if not retrieved_chunks:
            return "No verified government scheme records found matching the query."

        context_blocks = []
        for idx, chunk in enumerate(retrieved_chunks):
            meta = chunk.get("metadata", {})
            doc_name = meta.get("filename", "Official Document")
            scheme_name = meta.get("scheme_name", "Unknown Scheme")
            page = meta.get("page", "N/A")
            department = meta.get("department", "Govt Department")
            content = chunk.get("content", "").strip()

            block = (
                f"--- SOURCE [{idx+1}] ---\n"
                f"DOCUMENT: {doc_name} | SCHEME: {scheme_name} | DEPARTMENT: {department} | PAGE: {page}\n"
                f"RELEVANCE SCORE: {chunk.get('hybrid_score', 'N/A')}\n"
                f"CONTENT:\n{content}\n"
            )
            context_blocks.append(block)

        return "\n".join(context_blocks)
