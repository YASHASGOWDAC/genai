"""
Embeddings module for Government Scheme Assistant.
Generates semantic dense vectors using SentenceTransformers with offline local cache support and fallback.

Optimized with:
- @st.cache_resource for persistent in-memory caching of the embedding model
- Zero top-level torch/transformers imports
- Performance monitoring for model load times
"""

import logging
import hashlib
from typing import List, Union
import numpy as np

try:
    from config import EMBEDDING_MODEL_NAME
except ImportError:
    EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

try:
    from utils.performance_monitor import TimingContext
except ImportError:
    class TimingContext:
        def __init__(self, *args, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass

try:
    import streamlit as st
    st_cache_resource = st.cache_resource
except Exception:
    def st_cache_resource(*args, **kwargs):
        def dec(f):
            return f
        return dec

logger = logging.getLogger(__name__)

# Global singleton cache for embedding model across process
_EMBEDDING_MODEL_INSTANCE = None


class FallbackEmbeddingModel:
    """
    Deterministic pseudo-semantic embedding generator based on token hashing and n-gram frequency.
    Ensures vector store operations continue without breaking if torch/models are downloading or offline.
    """
    def __init__(self, dimension: int = 384):
        self.dimension = dimension

    def encode(self, texts: Union[str, List[str]], show_progress_bar: bool = False, **kwargs) -> np.ndarray:
        if isinstance(texts, str):
            texts = [texts]

        vectors = []
        for text in texts:
            words = text.lower().split()
            vec = np.zeros(self.dimension, dtype=np.float32)
            if not words:
                vectors.append(vec)
                continue

            for idx, word in enumerate(words):
                h = int(hashlib.md5(word.encode("utf-8")).hexdigest(), 16)
                pos = h % self.dimension
                val = ((h >> 4) % 1000) / 1000.0 - 0.5
                vec[pos] += val

            norm = np.linalg.norm(vec)
            if norm > 0:
                vec = vec / norm
            vectors.append(vec)

        return np.array(vectors, dtype=np.float32)


class GovernmentSchemeEmbeddings:
    """
    Primary embedding wrapper for RAG retrieval and ChromaDB indexing.
    Loads locally stored SentenceTransformers model without requiring internet access.
    """
    def __init__(self, model_name: str = EMBEDDING_MODEL_NAME):
        self.model_name = model_name
        self.model = None
        self._load_model()

    def _load_model(self):
        global _EMBEDDING_MODEL_INSTANCE
        if _EMBEDDING_MODEL_INSTANCE is not None:
            self.model = _EMBEDDING_MODEL_INSTANCE
            return

        with TimingContext("embedding_model_load", self.model_name):
            try:
                from sentence_transformers import SentenceTransformer
                logger.info(f"Loading local SentenceTransformer model: {self.model_name}")
                # Try loading strictly from local cache first (offline capability)
                try:
                    self.model = SentenceTransformer(self.model_name, local_files_only=True)
                    logger.info("Loaded SentenceTransformer in local offline mode.")
                except Exception:
                    self.model = SentenceTransformer(self.model_name)
                    logger.info("SentenceTransformer loaded from cache/model hub.")

                _EMBEDDING_MODEL_INSTANCE = self.model
            except Exception as e:
                logger.warning(f"Could not load SentenceTransformer ({e}). Initializing deterministic fallback embedding.")
                self.model = FallbackEmbeddingModel(dimension=384)
                _EMBEDDING_MODEL_INSTANCE = self.model

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed a batch of document chunk strings."""
        if not texts:
            return []
        embeddings = self.model.encode(texts, show_progress_bar=False)
        if isinstance(embeddings, np.ndarray):
            return embeddings.tolist()
        return embeddings

    def embed_query(self, text: str) -> List[float]:
        """Embed a single user query string."""
        if not text:
            return [0.0] * 384
        embeddings = self.model.encode([text], show_progress_bar=False)
        if isinstance(embeddings, np.ndarray):
            return embeddings[0].tolist()
        return embeddings[0]

    def __call__(self, input: Union[str, List[str]]) -> Union[List[float], List[List[float]]]:
        """ChromaDB compatible embedding callable."""
        if isinstance(input, str):
            return self.embed_query(input)
        return self.embed_documents(input)


class ChromaEmbeddingFunction:
    """Implements chromadb.EmbeddingFunction protocol."""
    def __init__(self, embedding_wrapper: GovernmentSchemeEmbeddings):
        self.embedding_wrapper = embedding_wrapper

    def __call__(self, input: List[str]) -> List[List[float]]:
        return self.embedding_wrapper.embed_documents(input)


@st_cache_resource(show_spinner=False)
def get_cached_embeddings_instance(model_name: str = EMBEDDING_MODEL_NAME) -> GovernmentSchemeEmbeddings:
    """Cached singleton instance of GovernmentSchemeEmbeddings across Streamlit reruns."""
    return GovernmentSchemeEmbeddings(model_name=model_name)
