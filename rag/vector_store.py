"""
Vector Store module for Government Scheme Assistant.
Manages persistent ChromaDB vector storage, collection indexing, and metadata operations.

Optimized with:
- @st.cache_resource for persistent ChromaDB client and collection reuse
- Process-level singleton client avoiding multiple disk lock acquisitions
- Lazy import of chromadb
- Integrated performance latency monitoring for initialization and queries
"""

import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

try:
    from config import CHROMA_PERSIST_DIR, CHROMA_COLLECTION_NAME
    from rag.chunking import DocumentChunk
    from rag.embeddings import GovernmentSchemeEmbeddings, ChromaEmbeddingFunction, get_cached_embeddings_instance
except ImportError:
    CHROMA_PERSIST_DIR = Path(__file__).resolve().parent.parent / "database" / "chroma_db"
    CHROMA_COLLECTION_NAME = "government_schemes_collection"
    from rag.embeddings import GovernmentSchemeEmbeddings, ChromaEmbeddingFunction, get_cached_embeddings_instance

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

# Process-level singletons for Chroma client & collection
_PERSISTENT_CHROMA_CLIENT = None
_CACHED_COLLECTIONS: Dict[str, Any] = {}


def get_shared_chroma_client(persist_dir: Path):
    """Obtain or initialize the persistent ChromaDB client singleton."""
    global _PERSISTENT_CHROMA_CLIENT
    if _PERSISTENT_CHROMA_CLIENT is not None:
        return _PERSISTENT_CHROMA_CLIENT

    with TimingContext("chromadb_init", str(persist_dir)):
        import chromadb
        from chromadb.config import Settings
        logger.info(f"Connecting to persistent ChromaDB at: {persist_dir}")
        _PERSISTENT_CHROMA_CLIENT = chromadb.PersistentClient(
            path=str(persist_dir),
            settings=Settings(anonymized_telemetry=False, allow_reset=True)
        )
    return _PERSISTENT_CHROMA_CLIENT


class GovernmentSchemeVectorStore:
    """Manages the persistent ChromaDB collection for government schemes."""
    def __init__(self, persist_dir: Path = CHROMA_PERSIST_DIR, 
                 collection_name: str = CHROMA_COLLECTION_NAME):
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.collection_name = collection_name
        self.embedding_wrapper = get_cached_embeddings_instance()
        self.embedding_fn = ChromaEmbeddingFunction(self.embedding_wrapper)
        
        self.client = get_shared_chroma_client(self.persist_dir)
        self.collection = self.get_or_create_collection()

    def get_or_create_collection(self):
        """Retrieve existing Chroma collection or create new one with caching."""
        global _CACHED_COLLECTIONS
        cache_key = f"{self.persist_dir}_{self.collection_name}"
        if cache_key in _CACHED_COLLECTIONS:
            return _CACHED_COLLECTIONS[cache_key]

        try:
            col = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"description": "Official Central & Karnataka Government Scheme Knowledge Base"}
            )
            _CACHED_COLLECTIONS[cache_key] = col
            return col
        except Exception as e:
            logger.error(f"Error accessing ChromaDB collection: {e}")
            raise e

    def add_chunks(self, chunks: List[DocumentChunk], batch_size: int = 50) -> int:
        """
        Add document chunks to the ChromaDB collection in batches.
        Computes dense embeddings and preserves metadata.
        """
        if not chunks:
            return 0

        with TimingContext("pdf_processing", f"index_chunks_batch_{len(chunks)}"):
            total_added = 0
            for i in range(0, len(chunks), batch_size):
                batch = chunks[i:i + batch_size]
                
                ids = [c.chunk_id for c in batch]
                documents = [c.content for c in batch]
                
                # Sanitize metadata (Chroma requires primitive types: str, int, float, bool)
                metadatas = []
                for c in batch:
                    clean_meta = {}
                    for k, v in c.metadata.items():
                        if isinstance(v, (str, int, float, bool)):
                            clean_meta[k] = v
                        elif isinstance(v, list):
                            clean_meta[k] = ", ".join(str(item) for item in v)
                        elif v is None:
                            clean_meta[k] = ""
                        else:
                            clean_meta[k] = str(v)
                    metadatas.append(clean_meta)

                embeddings = self.embedding_wrapper.embed_documents(documents)

                self.collection.upsert(
                    ids=ids,
                    documents=documents,
                    embeddings=embeddings,
                    metadatas=metadatas
                )
                total_added += len(batch)
                logger.info(f"Indexed batch {i // batch_size + 1}: {len(batch)} chunks (Total: {total_added}).")

            return total_added

    def query_similar(self, query: str, top_k: int = 5, where: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Query vector store using query text and semantic embedding.
        Returns matched documents with metadata, distance score, and content.
        """
        with TimingContext("vector_retrieval", f"query_top_{top_k}"):
            query_vec = self.embedding_wrapper.embed_query(query)
            
            kwargs = {
                "query_embeddings": [query_vec],
                "n_results": min(top_k, max(1, self.collection.count()))
            }
            if where:
                kwargs["where"] = where

            results = self.collection.query(**kwargs)

            matched_docs = []
            if results and "documents" in results and results["documents"]:
                docs_list = results["documents"][0]
                metas_list = results.get("metadatas", [[]])[0]
                distances_list = results.get("distances", [[]])[0]
                ids_list = results.get("ids", [[]])[0]

                for idx, doc_text in enumerate(docs_list):
                    meta = metas_list[idx] if idx < len(metas_list) else {}
                    dist = distances_list[idx] if idx < len(distances_list) else 0.0
                    chunk_id = ids_list[idx] if idx < len(ids_list) else ""
                    
                    # Approximate similarity score from distance
                    sim_score = round(1.0 / (1.0 + float(dist)), 4)

                    matched_docs.append({
                        "chunk_id": chunk_id,
                        "content": doc_text,
                        "metadata": meta,
                        "distance": dist,
                        "similarity": sim_score
                    })

            return matched_docs

    def delete_document_chunks(self, filename: str) -> bool:
        """Delete all chunks belonging to a specific document filename."""
        try:
            self.collection.delete(where={"filename": filename})
            logger.info(f"Deleted chunks for document: {filename}")
            return True
        except Exception as e:
            logger.error(f"Error deleting chunks for document {filename}: {e}")
            return False

    def count(self) -> int:
        """Get total number of chunks currently stored in vector DB."""
        try:
            return self.collection.count()
        except Exception:
            return 0

    def reset_collection(self):
        """Reset and wipe the collection (used for re-indexing)."""
        global _CACHED_COLLECTIONS
        cache_key = f"{self.persist_dir}_{self.collection_name}"
        if cache_key in _CACHED_COLLECTIONS:
            del _CACHED_COLLECTIONS[cache_key]

        self.client.delete_collection(self.collection_name)
        self.collection = self.get_or_create_collection()


@st_cache_resource(show_spinner=False)
def get_cached_vector_store() -> GovernmentSchemeVectorStore:
    """Cached singleton instance of GovernmentSchemeVectorStore for Streamlit."""
    return GovernmentSchemeVectorStore()
