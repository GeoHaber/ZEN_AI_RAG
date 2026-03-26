# -*- coding: utf-8 -*-
"""
backend_impl.py — Concrete ``UIBackend`` implementation
========================================================

Wraps *all* Core modules, services, and HTTP APIs behind the single
``UIBackend`` protocol so both NiceGUI and Flet UIs call the same code.
"""
from __future__ import annotations

import asyncio
import logging
import time
from pathlib import Path
from typing import Any, AsyncIterator

from backend_protocol import (
    HealthStatus,
    ModelInfo,
    RAGResult,
    ScanResult,
    UIBackend,
)

logger = logging.getLogger(__name__)


def _safe_import(module_path: str, attr: str | None = None):
    """Import *module_path* and optionally get *attr*; return None on failure."""
    try:
        import importlib

        mod = importlib.import_module(module_path)
        return getattr(mod, attr) if attr else mod
    except Exception:
        return None


class ConcreteBackend:
    """Production implementation of :class:`UIBackend`.

    Heavy services are initialised lazily so startup stays fast.
    """

    def __init__(self) -> None:
        self._rag_system = None
        self._conversation_memory = None
        self._universal_extractor = None
        self._enhanced_rag_service = None
        self._async_backend = None

    # ── Lazy initialisers ─────────────────────────────────────────────────

    def _get_rag_system(self):
        if self._rag_system is None:
            try:
                from zena_mode import LocalRAG
                from config_system import config

                cache_dir = Path(config.BASE_DIR) / "rag_cache"
                cache_dir.mkdir(parents=True, exist_ok=True)
                self._rag_system = LocalRAG(cache_dir=str(cache_dir))
            except Exception as exc:
                logger.warning("RAG system unavailable: %s", exc)
        return self._rag_system

    def _get_conversation_memory(self):
        if self._conversation_memory is None:
            try:
                from zena_mode import ConversationMemory
                from config_system import config

                cache_dir = Path(config.BASE_DIR) / "conversation_cache"
                cache_dir.mkdir(parents=True, exist_ok=True)
                self._conversation_memory = ConversationMemory(
                    cache_dir=str(cache_dir)
                )
            except Exception as exc:
                logger.warning("Conversation memory unavailable: %s", exc)
        return self._conversation_memory

    def _get_extractor(self):
        if self._universal_extractor is None:
            try:
                from zena_mode.universal_extractor import UniversalExtractor

                self._universal_extractor = UniversalExtractor()
            except Exception as exc:
                logger.warning("Universal extractor unavailable: %s", exc)
        return self._universal_extractor

    def _get_enhanced_rag(self):
        """Initialise the Enhanced RAG service (C-RAG, HyDE, FLARE, etc.)."""
        if self._enhanced_rag_service is not None:
            return self._enhanced_rag_service
        try:
            from Core.enhanced_rag_wrapper import EnhancedRAGService
            from config_system import config

            rag = self._get_rag_system()
            if rag is None:
                return None

            LLM_API_URL = f"http://127.0.0.1:{config.llm_port}"

            def retrieve_fn(query, top_k=5):
                if hasattr(rag, "hybrid_search"):
                    return rag.hybrid_search(query, k=top_k, alpha=0.5)
                return rag.search(query, k=top_k)

            def generate_fn(query, chunks):
                import requests

                context = "\n\n".join(
                    c.get("text", c.get("content", ""))
                    for c in (chunks or [])
                )
                resp = requests.post(
                    f"{LLM_API_URL}/v1/chat/completions",
                    json={
                        "messages": [
                            {
                                "role": "system",
                                "content": f"Answer based on context:\n{context}",
                            },
                            {"role": "user", "content": query},
                        ],
                        "stream": False,
                        "temperature": 0.7,
                    },
                    timeout=120,
                )
                resp.raise_for_status()
                return resp.json()["choices"][0]["message"]["content"]

            def llm_fn(prompt):
                import requests

                resp = requests.post(
                    f"{LLM_API_URL}/v1/chat/completions",
                    json={
                        "messages": [{"role": "user", "content": prompt}],
                        "stream": False,
                        "temperature": 0.5,
                    },
                    timeout=120,
                )
                resp.raise_for_status()
                return resp.json()["choices"][0]["message"]["content"]

            embed_fn = None
            search_by_embedding_fn = None
            if hasattr(rag, "_embed_mgr") and rag._embed_mgr:
                embed_fn = lambda text: rag._embed_mgr.encode_single(
                    text, normalize=True
                )
            if hasattr(rag, "qdrant") and rag.qdrant:
                search_by_embedding_fn = lambda emb, top_k: rag.qdrant.query_points(
                    collection_name=getattr(rag, "collection_name", "zen_rag"),
                    query=emb.tolist() if hasattr(emb, "tolist") else emb,
                    limit=top_k,
                )

            service = EnhancedRAGService(
                retrieve_fn=retrieve_fn,
                generate_fn=generate_fn,
            )
            service.initialize(
                llm_fn=llm_fn,
                embed_fn=embed_fn,
                search_by_embedding_fn=search_by_embedding_fn,
            )
            self._enhanced_rag_service = service
        except Exception as exc:
            logger.warning("Enhanced RAG service unavailable: %s", exc)
        return self._enhanced_rag_service

    def _get_async_backend(self):
        if self._async_backend is None:
            try:
                from async_backend import AsyncZenAIBackend

                self._async_backend = AsyncZenAIBackend()
            except Exception:
                try:
                    from _backend_stub import StubBackend

                    self._async_backend = StubBackend()
                except Exception as exc:
                    logger.warning("No async backend available: %s", exc)
        return self._async_backend

    # ── Chat ──────────────────────────────────────────────────────────────

    async def chat(
        self,
        prompt: str,
        *,
        session_id: str = "",
        temperature: float = 0.7,
        max_tokens: int = 2048,
        rag_enabled: bool = True,
        rag_mode: str = "enhanced",
        streaming: bool = False,
    ) -> RAGResult:
        t0 = time.perf_counter()
        result = RAGResult()

        # Build conversational context
        mem = self._get_conversation_memory()
        context_prompt = prompt
        if mem:
            try:
                context_prompt = mem.build_contextual_prompt(prompt, session_id)
            except Exception:
                pass

        # RAG retrieval
        rag = self._get_rag_system()
        rag_context = ""
        rag_sources: list[dict] = []

        if rag_enabled and rag and getattr(rag, "index", None):
            if rag_mode == "enhanced":
                svc = self._get_enhanced_rag()
                if svc:
                    try:
                        enh_result = await asyncio.to_thread(
                            svc.query, prompt, 5
                        )
                        result.answer = enh_result.get("answer", "")
                        result.sources = enh_result.get("sources", [])
                        result.confidence = enh_result.get("confidence", 0.0)
                        result.hallucination_score = enh_result.get(
                            "hallucination_score", 0.0
                        )
                        result.conflicts = enh_result.get("conflicts", [])
                        result.stages = enh_result.get("stages", [])
                        result.mode = "enhanced"
                        result.latency_ms = (
                            time.perf_counter() - t0
                        ) * 1000
                        if mem:
                            try:
                                mem.add_message("user", prompt, session_id)
                                mem.add_message(
                                    "assistant", result.answer, session_id
                                )
                            except Exception:
                                pass
                        return result
                    except Exception as exc:
                        logger.warning("Enhanced RAG failed, falling back: %s", exc)

            # Classic RAG
            try:
                if hasattr(rag, "hybrid_search_async"):
                    rag_sources = await rag.hybrid_search_async(
                        prompt, k=5, alpha=0.5
                    )
                elif hasattr(rag, "hybrid_search"):
                    rag_sources = await asyncio.to_thread(
                        rag.hybrid_search, prompt, k=5, alpha=0.5
                    )
                else:
                    rag_sources = await asyncio.to_thread(
                        rag.search, prompt, k=5
                    )
                rag_context = "\n\n".join(
                    s.get("text", s.get("content", ""))
                    for s in (rag_sources or [])
                )
                result.sources = rag_sources
                result.mode = "classic"
            except Exception as exc:
                logger.warning("Classic RAG search failed: %s", exc)

        # LLM generation
        backend = self._get_async_backend()
        if backend:
            try:
                full_prompt = (
                    f"Context:\n{rag_context}\n\nUser: {context_prompt}"
                    if rag_context
                    else context_prompt
                )
                answer_chunks = []
                async for chunk in backend.send_message_async(full_prompt):
                    answer_chunks.append(chunk)
                result.answer = "".join(answer_chunks)
            except Exception as exc:
                logger.error("LLM backend error: %s", exc)
                result.answer = f"Error: {exc}"
        else:
            result.answer = (
                "No LLM backend available. Please start the backend server."
            )

        result.latency_ms = (time.perf_counter() - t0) * 1000

        # Save to memory
        if mem:
            try:
                mem.add_message("user", prompt, session_id)
                mem.add_message("assistant", result.answer, session_id)
            except Exception:
                pass

        return result

    async def chat_stream(
        self,
        prompt: str,
        *,
        session_id: str = "",
        temperature: float = 0.7,
        max_tokens: int = 2048,
        rag_enabled: bool = True,
        rag_mode: str = "enhanced",
    ) -> AsyncIterator[str]:
        backend = self._get_async_backend()
        if not backend:
            yield "No LLM backend available."
            return
        try:
            async for chunk in backend.send_message_async(prompt):
                yield chunk
        except Exception as exc:
            yield f"\n\nError: {exc}"

    async def council_chat(
        self, prompt: str, *, mode: str = "council"
    ) -> dict[str, Any]:
        try:
            import requests
            from config_system import config

            resp = requests.post(
                config.get_mgmt_url("/api/chat/swarm"),
                json={"message": prompt, "mode": mode},
                timeout=120,
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:
            return {"error": str(exc), "consensus_answer": f"Council error: {exc}"}

    # ── RAG Scanning ─────────────────────────────────────────────────────

    async def scan_web(self, url: str, *, max_pages: int = 10) -> ScanResult:
        t0 = time.perf_counter()
        try:
            from zena_mode.website_scraper import WebsiteScraper

            scraper = WebsiteScraper(url)
            raw = await asyncio.to_thread(scraper.scrape, max_pages=max_pages)
            docs = raw.get("documents", [])
            text = "\n\n".join(d.get("text", "") for d in docs)
            sources = [
                {"title": d.get("title", ""), "url": d.get("url", "")}
                for d in docs
            ]
            rag = self._get_rag_system()
            if rag:
                await asyncio.to_thread(rag.build_index, docs)
            return ScanResult(
                text=text,
                sources=sources,
                images=raw.get("images", []),
                chunks=len(docs),
                elapsed_s=time.perf_counter() - t0,
            )
        except Exception as exc:
            logger.error("Web scan failed: %s", exc)
            return ScanResult()

    async def scan_folder(self, path: str, *, max_files: int = 500) -> ScanResult:
        t0 = time.perf_counter()
        try:
            extractor = self._get_extractor()
            if not extractor:
                return ScanResult()
            chunks, stats = await asyncio.to_thread(
                extractor.process_directory, path, max_files=max_files
            )
            text = "\n\n".join(c.get("text", "") for c in chunks)
            sources = [
                {"title": c.get("source", ""), "path": c.get("path", "")}
                for c in chunks
            ]
            rag = self._get_rag_system()
            if rag:
                await asyncio.to_thread(rag.build_index, chunks)
            return ScanResult(
                text=text,
                sources=sources,
                chunks=len(chunks),
                elapsed_s=time.perf_counter() - t0,
            )
        except Exception as exc:
            logger.error("Folder scan failed: %s", exc)
            return ScanResult()

    async def scan_email(
        self, path_or_config: str, *, mode: str = "local"
    ) -> ScanResult:
        t0 = time.perf_counter()
        try:
            from zena_mode.email_ingestor import EmailIngestor

            ingestor = EmailIngestor()
            docs = await asyncio.to_thread(ingestor.ingest, path_or_config)
            text = "\n\n".join(d.get("text", "") for d in docs)
            sources = [
                {"title": d.get("subject", ""), "path": d.get("path", "")}
                for d in docs
            ]
            rag = self._get_rag_system()
            if rag:
                await asyncio.to_thread(rag.build_index, docs)
            return ScanResult(
                text=text,
                sources=sources,
                chunks=len(docs),
                elapsed_s=time.perf_counter() - t0,
            )
        except Exception as exc:
            logger.error("Email scan failed: %s", exc)
            return ScanResult()

    async def build_index(self, documents: list[str]) -> None:
        rag = self._get_rag_system()
        if rag:
            await asyncio.to_thread(rag.build_index, documents)

    # ── RAG Query ─────────────────────────────────────────────────────────

    async def rag_search(
        self, query: str, *, top_k: int = 5, alpha: float = 0.5
    ) -> list[dict[str, Any]]:
        rag = self._get_rag_system()
        if not rag:
            return []
        try:
            if hasattr(rag, "hybrid_search"):
                return await asyncio.to_thread(
                    rag.hybrid_search, query, k=top_k, alpha=alpha
                )
            return await asyncio.to_thread(rag.search, query, k=top_k)
        except Exception:
            return []

    async def rag_stats(self) -> dict[str, Any]:
        rag = self._get_rag_system()
        if not rag:
            return {"chunks": 0, "sources": 0}
        try:
            total = getattr(rag, "ntotal", 0)
            return {"chunks": total, "index_ready": bool(getattr(rag, "index", None))}
        except Exception:
            return {"chunks": 0}

    async def rag_cleanup(self) -> dict[str, Any]:
        try:
            ConflictDetector = _safe_import("Core.conflict_detector", "ConflictDetector")
            if ConflictDetector is None:
                return {"status": "conflict_detector unavailable"}
            detector = ConflictDetector()
            rag = self._get_rag_system()
            if not rag:
                return {"status": "RAG unavailable"}
            docs = await asyncio.to_thread(
                lambda: getattr(rag, "list_documents", lambda: [])()
            )
            conflicts = detector.detect(docs) if docs else []
            return {"conflicts": conflicts, "count": len(conflicts)}
        except Exception as exc:
            return {"error": str(exc)}

    async def rag_dedup(self) -> dict[str, Any]:
        try:
            ContentDeduplicator = _safe_import(
                "Core.deduplication", "ContentDeduplicator"
            )
            if ContentDeduplicator is None:
                return {"status": "deduplication unavailable"}
            dedup = ContentDeduplicator()
            rag = self._get_rag_system()
            if not rag:
                return {"status": "RAG unavailable"}
            docs = await asyncio.to_thread(
                lambda: getattr(rag, "list_documents", lambda: [])()
            )
            duplicates = dedup.find_duplicates(docs) if docs else []
            return {"duplicates": duplicates, "count": len(duplicates)}
        except Exception as exc:
            return {"error": str(exc)}

    # ── Models ────────────────────────────────────────────────────────────

    async def list_models(self) -> list[ModelInfo]:
        try:
            from config_system import config

            models_dir = Path(config.MODEL_DIR) if hasattr(config, "MODEL_DIR") else None
            if models_dir and models_dir.exists():
                return [
                    ModelInfo(
                        name=f.stem,
                        filename=f.name,
                        size=f"{f.stat().st_size / (1024**3):.1f} GB",
                    )
                    for f in models_dir.glob("*.gguf")
                    if f.is_file()
                ]
        except Exception:
            pass
        return []

    async def load_model(self, filename: str) -> bool:
        try:
            import requests
            resp = requests.post(
                "http://127.0.0.1:8002/models/load",
                json={"model": filename},
                timeout=30,
            )
            return resp.ok
        except Exception:
            return False

    async def download_model(
        self, repo_id: str, filename: str
    ) -> dict[str, Any]:
        try:
            import requests
            resp = requests.post(
                "http://127.0.0.1:8002/models/download",
                json={"repo_id": repo_id, "filename": filename},
                timeout=600,
            )
            return resp.json() if resp.ok else {"error": resp.text}
        except Exception as exc:
            return {"error": str(exc)}

    # ── Voice ─────────────────────────────────────────────────────────────

    async def speak(self, text: str) -> dict[str, Any]:
        try:
            import requests
            resp = requests.post(
                "http://127.0.0.1:8001/voice/speak",
                json={"text": text},
                timeout=30,
            )
            return resp.json() if resp.ok else {"error": resp.text}
        except Exception as exc:
            return {"error": str(exc)}

    async def voice_devices(self) -> list[dict[str, Any]]:
        try:
            import requests
            resp = requests.get(
                "http://127.0.0.1:8001/voice/devices", timeout=5
            )
            return resp.json().get("devices", []) if resp.ok else []
        except Exception:
            return []

    # ── Health & Diagnostics ──────────────────────────────────────────────

    async def health(self) -> HealthStatus:
        status = HealthStatus()
        try:
            import requests
            from config_system import config

            # LLM backend
            try:
                r = requests.get(
                    f"http://127.0.0.1:{config.llm_port}/v1/models", timeout=3
                )
                if r.ok:
                    status.llm_online = True
                    data = r.json().get("data", [])
                    if data:
                        status.model_name = data[0].get("id", "")
            except Exception:
                pass

            # Hub
            try:
                r = requests.get(
                    f"http://127.0.0.1:{config.mgmt_port}/health", timeout=3
                )
                status.hub_online = r.ok
            except Exception:
                pass

            # RAG
            rag = self._get_rag_system()
            status.rag_ready = bool(rag and getattr(rag, "index", None))
        except Exception as exc:
            status.error = str(exc)
        return status

    async def benchmark(self) -> dict[str, Any]:
        try:
            import requests
            from config_system import config

            prompt = "Explain what a neural network is in one paragraph."
            t0 = time.perf_counter()
            resp = requests.post(
                f"http://127.0.0.1:{config.llm_port}/v1/chat/completions",
                json={
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False,
                    "max_tokens": 200,
                },
                timeout=60,
            )
            elapsed = time.perf_counter() - t0
            if resp.ok:
                data = resp.json()
                usage = data.get("usage", {})
                tokens = usage.get("completion_tokens", 0)
                return {
                    "tokens": tokens,
                    "elapsed_s": elapsed,
                    "tok_per_s": tokens / elapsed if elapsed > 0 else 0,
                }
        except Exception as exc:
            return {"error": str(exc)}
        return {}

    # ── Conversation Memory ───────────────────────────────────────────────

    async def save_message(
        self, role: str, content: str, *, session_id: str = ""
    ) -> None:
        mem = self._get_conversation_memory()
        if mem:
            try:
                mem.add_message(role, content, session_id)
            except Exception:
                pass

    async def build_context(
        self, prompt: str, *, session_id: str = ""
    ) -> str:
        mem = self._get_conversation_memory()
        if mem:
            try:
                return mem.build_contextual_prompt(prompt, session_id)
            except Exception:
                pass
        return prompt

    # ── Evaluation & Cache ────────────────────────────────────────────────

    async def cache_stats(self) -> dict[str, Any]:
        try:
            SemanticCache = _safe_import("Core.semantic_cache", "SemanticCache")
            if SemanticCache:
                cache = SemanticCache()
                return cache.get_stats()
        except Exception:
            pass
        return {"hits": 0, "misses": 0}

    async def eval_stats(self) -> dict[str, Any]:
        try:
            AnswerEvaluator = _safe_import("Core.evaluation", "AnswerEvaluator")
            if AnswerEvaluator:
                evaluator = AnswerEvaluator()
                return {"available": True}
        except Exception:
            pass
        return {"available": False}

    # ── Background Services ───────────────────────────────────────────────

    async def start_gateways(self) -> dict[str, bool]:
        result: dict[str, bool] = {"telegram": False, "whatsapp": False}
        try:
            from config_system import config

            if getattr(config, "telegram_token", None):
                import threading

                from zena_mode.gateway_telegram import run_telegram_gateway

                threading.Thread(
                    target=run_telegram_gateway, daemon=True
                ).start()
                result["telegram"] = True
        except Exception:
            pass
        try:
            from config_system import config

            if getattr(config, "whatsapp_whitelist", None):
                import threading

                from zena_mode.gateway_whatsapp import run_whatsapp_gateway

                threading.Thread(
                    target=run_whatsapp_gateway, daemon=True
                ).start()
                result["whatsapp"] = True
        except Exception:
            pass
        return result

    async def check_updates(self) -> dict[str, Any]:
        try:
            from zena_mode.auto_updater import check_for_updates

            return await asyncio.to_thread(check_for_updates)
        except Exception as exc:
            return {"error": str(exc)}

    # ── File Extraction ───────────────────────────────────────────────────

    async def extract_text(self, data: bytes, filename: str) -> str:
        extractor = self._get_extractor()
        if extractor:
            try:
                chunks, _ = await asyncio.to_thread(
                    extractor.process, data, filename, parallel=False
                )
                return "\n".join(c.get("text", "") for c in chunks)
            except Exception:
                pass
        # Fallback: try UTF-8 decode
        try:
            return data.decode("utf-8")
        except Exception:
            return ""


# ── Factory ───────────────────────────────────────────────────────────────────


def create_backend() -> ConcreteBackend:
    """Create and return a ready-to-use backend instance."""
    return ConcreteBackend()
