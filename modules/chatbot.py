"""
Chatbot coordinator module for Government Scheme Assistant.
Coordinates retrieval, LLM answer synthesis, multilingual detection, and history tracking.
"""

import time
import logging
from typing import Dict, Any, List, Optional

from rag.retriever import GovernmentSchemeRetriever
from rag.answer_generator import GovernmentSchemeAnswerGenerator
from database.sqlite_db import save_chat_message, get_session_chat_history
from modules.multilingual import detect_language

logger = logging.getLogger(__name__)


class GovernmentSchemeChatbot:
    """Conversational orchestrator for government scheme Q&A."""
    def __init__(self):
        self.retriever = GovernmentSchemeRetriever()
        self.answer_generator = GovernmentSchemeAnswerGenerator()

    def process_query(self, user_query: str, session_id: str, 
                      preferred_language: str = "English",
                      category_filter: Optional[str] = None,
                      level_filter: Optional[str] = None,
                      provider_preference: Optional[str] = None) -> Dict[str, Any]:
        """
        Process a citizen query end-to-end through the local RAG pipeline.
        Searches strictly local ChromaDB without internet retrieval.
        """
        start_time = time.time()
        
        # Determine language (user preference or detected language)
        detected_lang = detect_language(user_query)
        effective_language = preferred_language if preferred_language != "English" else detected_lang

        # 1. Retrieve relevant document chunks from local ChromaDB
        retrieved_chunks = self.retriever.retrieve(
            query=user_query,
            top_k=4,
            category=category_filter,
            level=level_filter
        )

        # 2. Fetch conversation history for session
        raw_history = get_session_chat_history(session_id, limit=4)
        formatted_history = []
        for h in raw_history:
            formatted_history.append({
                "user": h["user_question"],
                "assistant": h["assistant_response"]
            })

        # 3. Generate grounded answer strictly using retrieved local chunks
        result = self.answer_generator.generate_answer(
            query=user_query,
            retrieved_chunks=retrieved_chunks,
            language=effective_language,
            conversation_history=formatted_history,
            provider_preference=provider_preference
        )

        elapsed = round(time.time() - start_time, 2)
        result["total_latency"] = elapsed
        result["retrieved_chunks"] = retrieved_chunks

        # 4. Save to database
        try:
            save_chat_message(
                session_id=session_id,
                question=user_query,
                response=result["answer"],
                language=effective_language,
                sources=result.get("citations", []),
                response_time=elapsed
            )
        except Exception as e:
            logger.warning(f"Could not persist chat message: {e}")

        return result
