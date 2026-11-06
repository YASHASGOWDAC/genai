
"""
Chunking module for Government Scheme Assistant.
Splits document pages into semantically cohesive chunks while preserving context headers.
"""

import re
from typing import List, Dict, Any, Optional
from rag.document_loader import Document

try:
    from config import CHUNK_SIZE, CHUNK_OVERLAP
except ImportError:
    CHUNK_SIZE = 600
    CHUNK_OVERLAP = 100


class DocumentChunk:
    """Represents an indexed chunk with context metadata."""
    def __init__(self, chunk_id: str, content: str, raw_content: str, metadata: Dict[str, Any]):
        self.chunk_id = chunk_id
        self.content = content          # Header + text (used for embedding & retrieval)
        self.raw_content = raw_content  # Plain extracted text snippet
        self.metadata = metadata

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "content": self.content,
            "raw_content": self.raw_content,
            "metadata": self.metadata
        }

    def __repr__(self) -> str:
        return f"DocumentChunk(id={self.chunk_id}, len={len(self.content)})"


def recursive_split_text(text: str, chunk_size: int = CHUNK_SIZE, chunk_overlap: int = CHUNK_OVERLAP) -> List[str]:
    """
    Recursively split text using hierarchy of separators:
    Double newlines -> Single newlines -> Sentence endings -> Punctuation -> Words.
    """
    separators = ["\n\n", "\n", ". ", "; ", " ", ""]
    
    def _split(text: str, seps: List[str]) -> List[str]:
        if len(text) <= chunk_size or not seps:
            return [text] if text.strip() else []

        sep = seps[0]
        remaining_seps = seps[1:]

        if sep == "":
            # Character-level chunking
            chunks = []
            for i in range(0, len(text), chunk_size - chunk_overlap):
                c = text[i:i + chunk_size].strip()
                if c:
                    chunks.append(c)
            return chunks

        parts = text.split(sep)
        chunks = []
        current_chunk = []
        current_len = 0

        for part in parts:
            part_len = len(part) + len(sep)
            if current_len + part_len > chunk_size and current_chunk:
                merged = sep.join(current_chunk).strip()
                if merged:
                    chunks.append(merged)
                
                # Maintain overlap from current_chunk
                overlap_acc = []
                overlap_len = 0
                for item in reversed(current_chunk):
                    if overlap_len + len(item) <= chunk_overlap:
                        overlap_acc.insert(0, item)
                        overlap_len += len(item) + len(sep)
                    else:
                        break
                current_chunk = overlap_acc
                current_len = overlap_len

            current_chunk.append(part)
            current_len += part_len

        if current_chunk:
            merged = sep.join(current_chunk).strip()
            if merged:
                chunks.append(merged)

        # Re-check any sub-chunk that still exceeds chunk_size
        final_chunks = []
        for c in chunks:
            if len(c) > chunk_size and remaining_seps:
                final_chunks.extend(_split(c, remaining_seps))
            elif c.strip():
                final_chunks.append(c.strip())

        return final_chunks

    return _split(text, separators)


def chunk_documents(documents: List[Document], 
                    chunk_size: int = CHUNK_SIZE, 
                    chunk_overlap: int = CHUNK_OVERLAP) -> List[DocumentChunk]:
    """
    Split a list of Documents into enriched DocumentChunks with context headers.
    """
    chunks: List[DocumentChunk] = []

    for doc in documents:
        raw_text = doc.page_content
        meta = dict(doc.metadata)
        
        filename = meta.get("filename", "unknown_doc")
        clean_file_id = re.sub(r'[^a-zA-Z0-9_\-]', '_', filename)
        page_num = meta.get("page", 1)
        scheme_name = meta.get("scheme_name") or filename.replace(".pdf", "")
        department = meta.get("department", "Govt Department")
        category = meta.get("category", "")
        level = meta.get("level", "")

        text_splits = recursive_split_text(raw_text, chunk_size, chunk_overlap)

        for idx, split_text in enumerate(text_splits):
            chunk_id = f"{clean_file_id}_p{page_num}_c{idx+1}"
            
            # Enrich chunk with an explicit context preamble for accurate embeddings and LLM grounding
            context_header = (
                f"DOCUMENT: {filename} | SCHEME: {scheme_name} | JURISDICTION: {level} | "
                f"DEPARTMENT: {department} | PAGE: {page_num}\n"
            )
            enriched_content = context_header + split_text

            chunk_meta = dict(meta)
            chunk_meta.update({
                "chunk_id": chunk_id,
                "chunk_index": idx + 1,
                "total_splits_in_page": len(text_splits),
                "scheme_name": scheme_name,
                "department": department,
                "category": category,
                "level": level,
                "filename": filename,
                "page": page_num
            })

            chunks.append(DocumentChunk(
                chunk_id=chunk_id,
                content=enriched_content,
                raw_content=split_text,
                metadata=chunk_meta
            ))

    return chunks
