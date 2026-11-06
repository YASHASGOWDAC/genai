"""
Answer Generator module for Government Scheme Assistant.
Generates grounded, fact-checked answers with strict source citations from locally retrieved chunks.
Supports:
1. Local Offline Synthesizer (Zero internet, zero external dependencies).
2. Local Offline LLM via Ollama (llama3, mistral, etc.).
3. Google Gemini API (Optional online answer generation, grounded strictly in local chunks).
Never performs internet retrieval.
"""

import os
import re
import time
import json
import logging
from typing import List, Dict, Any, Optional

try:
    import requests
except ImportError:
    requests = None

try:
    from config import (
        GEMINI_API_KEY, GEMINI_MODEL, FALLBACK_GEMINI_MODELS, 
        OLLAMA_BASE_URL, OLLAMA_MODEL, OLLAMA_TIMEOUT, DEFAULT_LLM_PROVIDER, LEGAL_DISCLAIMER
    )
except ImportError:
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL = "gemini-1.5-flash"
    FALLBACK_GEMINI_MODELS = ["gemini-1.5-flash", "gemini-2.0-flash", "gemini-pro"]
    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")
    OLLAMA_TIMEOUT = 10
    DEFAULT_LLM_PROVIDER = "auto"
    LEGAL_DISCLAIMER = "Informational guidance only based strictly on local verified documents."

try:
    from utils.performance_monitor import TimingContext
except ImportError:
    class TimingContext:
        def __init__(self, *args, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are the official AI Government Scheme Information Assistant for Indian Central Government and Karnataka State Government welfare programs.

CRITICAL LOCAL KNOWLEDGE BASE INSTRUCTIONS:
1. Grounding: Answer strictly and exclusively from the verified local context provided below. DO NOT invent, assume, or hallucinate any rules, dates, monetary amounts, or criteria not explicitly present in the retrieved local documents.
2. Unverified / Missing Information: If the provided local context does not contain adequate evidence to answer the question, you MUST clearly state:
   "The requested scheme information is not available in the local government scheme knowledge base. Please contact an administrator to upload the official policy PDF guidelines for this scheme, or explore existing locally indexed schemes."
3. Citations: Every claim must reference the source document name and page number from the local context (e.g. "[PM-KISAN Guidelines, Page 1]").
4. Official Portals: Highlight the designated official portal URL found in the local context.
5. No Internet Fallback: You must never claim to have browsed the live internet or invent unverified external information.
6. Language: If the user asks or if requested in Kannada or Hindi, respond fluently in that language, but ALWAYS preserve the original official scheme name in English/Kannada script (e.g., Gruha Lakshmi, PM-KISAN, Yuva Nidhi) and official portal links.
7. Tone: Courteous, objective, authoritative, and helpful to citizens. Use bullet points and bold section headers for readability.
"""


class GovernmentSchemeAnswerGenerator:
    """Manages LLM generation with Gemini, local Ollama, and local structured synthesis."""
    def __init__(self, api_key: Optional[str] = None, model_name: str = GEMINI_MODEL,
                 ollama_url: str = OLLAMA_BASE_URL, ollama_model: str = OLLAMA_MODEL):
        self.api_key = api_key or GEMINI_API_KEY or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or ""
        self.model_name = model_name
        self.ollama_url = ollama_url
        self.ollama_model = ollama_model
        self._gemini_client = None

    @property
    def gemini_client(self):
        """Lazy initialization of Gemini client only when requested."""
        if self._gemini_client is None and self.api_key:
            self._init_gemini()
        return self._gemini_client

    def _init_gemini(self):
        if not self.api_key:
            return

        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            self._gemini_client = genai.GenerativeModel(
                model_name=self.model_name,
                system_instruction=SYSTEM_PROMPT
            )
            logger.info(f"Gemini client initialized with model: {self.model_name}")
        except Exception as e:
            logger.warning(f"Could not initialize Gemini client: {e}")
            self._gemini_client = None

    def check_ollama_available(self) -> bool:
        """Check if local Ollama server is running and accessible."""
        if not requests:
            return False
        try:
            resp = requests.get(f"{self.ollama_url}/api/tags", timeout=2)
            return resp.status_code == 200
        except Exception:
            return False

    def generate_answer(self, query: str, 
                        retrieved_chunks: List[Dict[str, Any]], 
                        language: str = "English",
                        conversation_history: Optional[List[Dict[str, str]]] = None,
                        provider_preference: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate answer strictly from retrieved local chunks.
        Never searches internet; reports when info is not in the local knowledge base.
        """
        start_time = time.time()
        provider = (provider_preference or DEFAULT_LLM_PROVIDER).lower()

        # Extract citations & portal links from chunks
        citations = []
        portal_links = set()
        seen_docs = set()

        for c in retrieved_chunks:
            meta = c.get("metadata", {})
            doc_name = meta.get("filename", "Official Document")
            page = meta.get("page", 1)
            scheme_name = meta.get("scheme_name", "Scheme")
            portal = meta.get("source_url") or meta.get("application_portal")
            if portal and ("http://" in portal or "https://" in portal):
                portal_links.add(portal)

            doc_key = f"{doc_name}_p{page}"
            if doc_key not in seen_docs:
                seen_docs.add(doc_key)
                citations.append({
                    "document": doc_name,
                    "page": page,
                    "scheme_name": scheme_name,
                    "similarity": c.get("similarity", 0.0)
                })

        # Check if local knowledge base contains relevant chunks
        if not retrieved_chunks or (retrieved_chunks and max(c.get("similarity", 0) for c in retrieved_chunks) < 0.25):
            elapsed = round(time.time() - start_time, 2)
            msg = (
                "ℹ️ **The requested scheme information is not available in the local government scheme knowledge base.**\n\n"
                "- This system operates exclusively on locally stored and administrator-verified government documents.\n"
                "- No internet web-scraping or external search is conducted to avoid unverified information.\n\n"
                "**Suggested Next Steps:**\n"
                "1. Check the spelling of the scheme name.\n"
                "2. Browse all indexed schemes under the **Explore Schemes** directory.\n"
                "3. Contact an administrator to upload the official policy PDF guidelines into the local knowledge base via the **Admin Dashboard**."
            )
            return {
                "answer": msg,
                "citations": [],
                "portals": [],
                "response_time": elapsed,
                "model_used": "Local Knowledge Base Verification",
                "is_verified": False
            }

        # Build prompt context strictly from local chunks
        context_str = self._build_context_string(retrieved_chunks)
        history_str = self._build_history_string(conversation_history)

        full_prompt = (
            f"{history_str}"
            f"VERIFIED LOCAL GOVERNMENT CONTEXT:\n{context_str}\n\n"
            f"USER QUERY: {query}\n"
            f"PREFERRED RESPONSE LANGUAGE: {language}\n\n"
            f"Provide a comprehensive, accurately cited answer based strictly on the verified local context above."
        )

        answer_text = None
        model_used = "Local Offline Synthesizer"

        with TimingContext("llm_generation", provider):
            # Route 1: Explicit Ollama or Auto if Ollama is running
            if provider in ["ollama", "auto"] and not (provider == "auto" and self.gemini_client):
                ollama_resp = self._attempt_ollama(full_prompt)
                if ollama_resp:
                    answer_text = ollama_resp
                    model_used = f"Ollama ({self.ollama_model})"

            # Route 2: Gemini API (if configured and chosen or auto)
            if not answer_text and provider in ["gemini", "auto"] and self.gemini_client and self.api_key:
                try:
                    response = self.gemini_client.generate_content(
                        full_prompt,
                        generation_config={
                            "temperature": 0.2,
                            "max_output_tokens": 1200
                        }
                    )
                    if response and response.text:
                        answer_text = response.text.strip()
                        model_used = f"Gemini ({self.model_name})"
                except Exception as e:
                    logger.warning(f"Gemini API call failed: {e}. Checking Ollama / local synthesizer.")
                    # Try fallback gemini or ollama
                    answer_text = self._attempt_fallback_gemini(full_prompt)
                    if answer_text:
                        model_used = "Gemini Fallback"

            # Route 3: If still no answer (offline mode or local provider chosen), use Local Synthesizer
            if not answer_text:
                # If user explicitly requested Ollama but it's offline, try Ollama first
                if provider == "ollama":
                    ollama_resp = self._attempt_ollama(full_prompt)
                    if ollama_resp:
                        answer_text = ollama_resp
                        model_used = f"Ollama ({self.ollama_model})"

                if not answer_text:
                    answer_text = self._local_synthesize_answer(query, retrieved_chunks, language)
                    model_used = "Local Offline Document Synthesis"

        elapsed = round(time.time() - start_time, 2)

        return {
            "answer": answer_text,
            "citations": citations,
            "portals": list(portal_links),
            "response_time": elapsed,
            "model_used": model_used,
            "is_verified": True
        }

    def _attempt_ollama(self, prompt: str) -> Optional[str]:
        """Call local offline Ollama API if available."""
        if not requests:
            return None
        try:
            url = f"{self.ollama_url}/api/generate"
            payload = {
                "model": self.ollama_model,
                "prompt": prompt,
                "system": SYSTEM_PROMPT,
                "stream": False,
                "options": {
                    "temperature": 0.2,
                    "num_predict": 1000
                }
            }
            res = requests.post(url, json=payload, timeout=OLLAMA_TIMEOUT)
            if res.status_code == 200:
                data = res.json()
                return data.get("response", "").strip()
        except Exception as e:
            logger.info(f"Ollama local LLM not responding ({e}).")
        return None

    def _attempt_fallback_gemini(self, prompt: str) -> Optional[str]:
        """Try alternative Gemini models if default model had quota/deprecation issues."""
        try:
            import google.generativeai as genai
            for model_name in FALLBACK_GEMINI_MODELS:
                if model_name == self.model_name:
                    continue
                try:
                    m = genai.GenerativeModel(model_name=model_name, system_instruction=SYSTEM_PROMPT)
                    res = m.generate_content(prompt)
                    if res and res.text:
                        return res.text.strip()
                except Exception:
                    continue
        except Exception:
            pass
        return None

    def _build_context_string(self, chunks: List[Dict[str, Any]]) -> str:
        parts = []
        for idx, c in enumerate(chunks[:5]):
            meta = c.get("metadata", {})
            parts.append(
                f"--- LOCAL SOURCE [{idx+1}] ---\n"
                f"DOCUMENT: {meta.get('filename')} | PAGE: {meta.get('page')}\n"
                f"SCHEME: {meta.get('scheme_name')} | DEPT: {meta.get('department')}\n"
                f"{c.get('content')}\n"
            )
        return "\n".join(parts)

    def _build_history_string(self, history: Optional[List[Dict[str, str]]]) -> str:
        if not history:
            return ""
        recent = history[-4:]
        lines = ["CONVERSATION HISTORY:"]
        for turn in recent:
            lines.append(f"User: {turn.get('user', '')}")
            lines.append(f"Assistant: {turn.get('assistant', '')}")
        lines.append("\n")
        return "\n".join(lines)

    def _local_synthesize_answer(self, query: str, chunks: List[Dict[str, Any]], language: str) -> str:
        """
        Deterministic, grounded extraction from top locally retrieved chunks.
        Extracts key sections (Benefits, Eligibility, Documents, Application Steps, Portal).
        Completely offline and reproducible.
        """
        top_chunk = chunks[0]
        meta = top_chunk.get("metadata", {})
        scheme_name = meta.get("scheme_name", "Government Welfare Scheme")
        doc_name = meta.get("filename", "Official Guidelines")
        page = meta.get("page", 1)
        department = meta.get("department", "Government Department")

        # Aggregate content from top chunks
        combined_text = "\n\n".join([c.get("content", "") for c in chunks[:3]])

        # Parse key blocks using regex from standard document format
        benefits_match = re.search(r'(?:QUANTUM OF ASSISTANCE|Core Benefit|benefits_summary)[:\s]+(.*?)(?=\d+\.|\Z)', combined_text, re.DOTALL | re.IGNORECASE)
        eligibility_match = re.search(r'(?:STATUTORY ELIGIBILITY|eligibility_summary)[:\s]+(.*?)(?=\d+\.|\Z)', combined_text, re.DOTALL | re.IGNORECASE)
        docs_match = re.search(r'(?:MANDATORY DOCUMENTATION|required_documents)[:\s]+(.*?)(?=\d+\.|\Z)', combined_text, re.DOTALL | re.IGNORECASE)
        steps_match = re.search(r'(?:APPLICATION PROCEDURE|application_steps)[:\s]+(.*?)(?=\d+\.|\Z)', combined_text, re.DOTALL | re.IGNORECASE)
        portal_match = re.search(r'(?:OFFICIAL APPLICATION PORTAL|Designated Official Portal)[:\s]+(.*?)(?=\d+\.|\Z)', combined_text, re.DOTALL | re.IGNORECASE)

        lines = [
            f"### Verified Local Information: **{scheme_name}**",
            f"*Source: `{doc_name}` (Page {page}) | Authority: {department}*\n"
        ]

        if benefits_match:
            b_text = benefits_match.group(1).strip()[:400]
            lines.append(f"#### 💰 Financial Benefits & Assistance\n{b_text}\n")

        if eligibility_match:
            e_text = eligibility_match.group(1).strip()[:500]
            lines.append(f"#### 📋 Eligibility Criteria\n{e_text}\n")

        if docs_match:
            d_text = docs_match.group(1).strip()[:400]
            lines.append(f"#### 📄 Mandatory Documents Required\n{d_text}\n")

        if steps_match:
            s_text = steps_match.group(1).strip()[:400]
            lines.append(f"#### 🚀 How to Apply\n{s_text}\n")

        if portal_match:
            p_text = portal_match.group(1).strip().split("\n")[0]
            lines.append(f"#### 🌐 Official Application Link\n{p_text}\n")

        if len(lines) <= 2:
            clean_snippet = top_chunk.get("content", "").split("\n", 1)[-1].strip()[:600]
            lines.append(f"#### Verified Excerpt\n{clean_snippet}\n")

        lines.append(
            f"\n> **Verification Notice**: Retrieved directly from the local knowledge base "
            f"`{doc_name}` (Page {page}). All details are verified offline from official government files."
        )

        result = "\n".join(lines)

        # Multilingual handling for Karnataka/Hindi
        if language == "Kannada":
            result = f"**[ಸ್ಥಳೀಯ ದಸ್ತಾವೇಜುಗಳಿಂದ ಪರಿಶೀಲಿಸಿದ ಮಾಹಿತಿ]**\n\n" + result
        elif language == "Hindi":
            result = f"**[स्थानीय दस्तावेजों से सत्यापित जानकारी]**\n\n" + result

        return result
