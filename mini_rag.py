#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mini_rag.py - Tier 1: Mini RAG Knowledge Base

Ultra-fast local knowledge base for trivial questions.
No LLM calls needed - instant answers from curated Q&A pairs.

Target: 20-30% query coverage, 99%+ accuracy, <50ms latency.

Features:
- Curated high-quality Q&A pairs
- FAISS vector search
- Multi-answer validation (top-K agreement)
- Category-based organization
- Easy update and maintenance
"""
import time
import logging
import json
from pathlib import Path
from typing import Optional, Tuple, List, Dict
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)

# Core dependencies
try:
    from sentence_transformers import SentenceTransformer
    import faiss
    import numpy as np
    DEPS_AVAILABLE = True
except ImportError:
    DEPS_AVAILABLE = False
    logger.warning("[MiniRAG] sentence-transformers or faiss-cpu not installed")


# =============================================================================
# Configuration
# =============================================================================
@dataclass
class MiniRAGConfig:
    """Mini RAG configuration."""

    # Confidence thresholds
    HIGH_CONFIDENCE: float = 0.90      # Very confident match
    MEDIUM_CONFIDENCE: float = 0.85    # Confident match
    LOW_CONFIDENCE: float = 0.75       # Uncertain (don't answer)

    # Top-K validation
    TOP_K: int = 3                     # Check top-3 matches
    AGREEMENT_THRESHOLD: float = 0.9   # All must be similar

    # Performance
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"

    # Organization
    ENABLE_CATEGORIES: bool = True


# =============================================================================
# Data Classes
# =============================================================================
@dataclass
class KnowledgeEntry:
    """Single Q&A knowledge entry."""
    question: str                # Canonical question
    answer: str                  # Canonical answer
    category: str                # "setup" | "config" | "usage" | "troubleshoot" | "faq"
    confidence: float = 0.99     # Entry quality (0-1)
    aliases: List[str] = field(default_factory=list)  # Alternative phrasings
    tags: List[str] = field(default_factory=list)     # Keywords
    source: str = "curated"      # "curated" | "user_feedback" | "auto_generated"
    created: datetime = field(default_factory=datetime.now)
    updated: Optional[datetime] = None

    def to_dict(self) -> Dict:
        """Serialize to dict."""
        return {
            "question": self.question,
            "answer": self.answer,
            "category": self.category,
            "confidence": self.confidence,
            "aliases": self.aliases,
            "tags": self.tags,
            "source": self.source,
            "created": self.created.isoformat(),
            "updated": self.updated.isoformat() if self.updated else None
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'KnowledgeEntry':
        """Deserialize from dict."""
        return cls(
            question=data["question"],
            answer=data["answer"],
            category=data["category"],
            confidence=data.get("confidence", 0.99),
            aliases=data.get("aliases", []),
            tags=data.get("tags", []),
            source=data.get("source", "curated"),
            created=datetime.fromisoformat(data["created"]) if "created" in data else datetime.now(),
            updated=datetime.fromisoformat(data["updated"]) if data.get("updated") else None
        )


@dataclass
class MiniRAGStats:
    """Statistics tracking."""
    total_queries: int = 0
    hits: int = 0
    misses: int = 0
    high_conf_hits: int = 0
    medium_conf_hits: int = 0

    @property
    def hit_rate(self) -> float:
        if self.total_queries == 0:
            return 0.0
        return (self.hits / self.total_queries) * 100

    def to_dict(self) -> Dict:
        return {
            "total_queries": self.total_queries,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": f"{self.hit_rate:.2f}%",
            "high_confidence_hits": self.high_conf_hits,
            "medium_confidence_hits": self.medium_conf_hits
        }


# =============================================================================
# Mini RAG Implementation
# =============================================================================
class MiniRAG:
    """
    Ultra-fast local knowledge base.

    No LLM calls - instant answers from curated knowledge.
    """

    def __init__(
        self,
        config: Optional[MiniRAGConfig] = None,
        knowledge_file: Optional[Path] = None
    ):
        if not DEPS_AVAILABLE:
            raise ImportError("Install: pip install sentence-transformers faiss-cpu")

        self.config = config or MiniRAGConfig()
        self.knowledge_file = knowledge_file or Path("knowledge_base.json")

        # Load embedding model
        logger.info(f"[MiniRAG] Loading model: {self.config.EMBEDDING_MODEL}")
        self.model = SentenceTransformer(self.config.EMBEDDING_MODEL)
        self.embedding_dim = self.model.get_sentence_embedding_dimension()

        # Storage
        self.entries: List[KnowledgeEntry] = []
        self.index: Optional[faiss.IndexFlatIP] = None
        self.embeddings: List[np.ndarray] = []

        # Statistics
        self.stats = MiniRAGStats()

        # Load knowledge base
        self._load_knowledge_base()

    # =========================================================================
    # Core Operations
    # =========================================================================

    def search(self, query: str) -> Optional[Tuple[str, float, str]]:
        """
        Search mini RAG for answer.

        Returns:
            (answer, confidence, category) if confident match
            None if no confident match
        """
        start_time = time.time()
        self.stats.total_queries += 1

        if self.index is None or len(self.entries) == 0:
            self.stats.misses += 1
            return None

        # Embed query
        query_embedding = self.model.encode(query, convert_to_numpy=True)
        query_embedding = query_embedding.reshape(1, -1).astype(np.float32)
        faiss.normalize_L2(query_embedding)

        # Search (top-K for validation)
        k = min(self.config.TOP_K, len(self.entries))
        distances, indices = self.index.search(query_embedding, k)

        # Check best match
        best_similarity = float(distances[0][0])
        best_idx = indices[0][0]

        # Confidence classification
        if best_similarity >= self.config.HIGH_CONFIDENCE:
            # Very confident - validate with top-K agreement
            if self._validate_top_k_agreement(indices[0], distances[0]):
                entry = self.entries[best_idx]
                self.stats.hits += 1
                self.stats.high_conf_hits += 1

                latency_ms = (time.time() - start_time) * 1000
                logger.debug(
                    f"[MiniRAG] HIGH CONF HIT: {query[:40]}... "
                    f"(sim: {best_similarity:.3f}, {latency_ms:.1f}ms)"
                )

                return entry.answer, best_similarity, entry.category

        elif best_similarity >= self.config.MEDIUM_CONFIDENCE:
            # Medium confidence - still answer but track separately
            if self._validate_top_k_agreement(indices[0], distances[0]):
                entry = self.entries[best_idx]
                self.stats.hits += 1
                self.stats.medium_conf_hits += 1

                latency_ms = (time.time() - start_time) * 1000
                logger.debug(
                    f"[MiniRAG] MEDIUM CONF HIT: {query[:40]}... "
                    f"(sim: {best_similarity:.3f}, {latency_ms:.1f}ms)"
                )

                return entry.answer, best_similarity, entry.category

        # Low confidence or disagreement - don't answer
        self.stats.misses += 1
        return None

    def add_entry(
        self,
        question: str,
        answer: str,
        category: str,
        confidence: float = 0.99,
        aliases: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        source: str = "curated"
    ):
        """Add new knowledge entry."""
        entry = KnowledgeEntry(
            question=question,
            answer=answer,
            category=category,
            confidence=confidence,
            aliases=aliases or [],
            tags=tags or [],
            source=source
        )

        self.entries.append(entry)

        # Embed and add to index
        embedding = self.model.encode(question, convert_to_numpy=True)
        self.embeddings.append(embedding)

        # Rebuild index (simple for now, optimize later)
        self._rebuild_index()

        logger.info(f"[MiniRAG] Added entry: {question[:50]}...")

    def get_stats(self) -> Dict:
        """Get statistics."""
        return {
            **self.stats.to_dict(),
            "total_entries": len(self.entries),
            "categories": self._count_by_category()
        }

    # =========================================================================
    # Internal Helpers
    # =========================================================================

    def _validate_top_k_agreement(
        self,
        indices: np.ndarray,
        distances: np.ndarray
    ) -> bool:
        """
        Validate top-K results agree on the answer.

        This prevents returning wrong answer when multiple
        similar but different questions exist.
        """
        if len(indices) < 2:
            return True  # Only one result, trust it

        # Get answers for top-K
        top_answers = [self.entries[idx].answer for idx in indices[:self.config.TOP_K]]

        # Check if all answers are identical or very similar
        first_answer = top_answers[0]

        # Strict check: all must be exactly the same
        # (Can enhance with semantic similarity later)
        agreement = all(ans == first_answer for ans in top_answers)

        return agreement

    def _rebuild_index(self):
        """Rebuild FAISS index from scratch."""
        if len(self.embeddings) == 0:
            self.index = None
            return

        # Create index
        self.index = faiss.IndexFlatIP(self.embedding_dim)

        # Add all embeddings
        embeddings_matrix = np.array(self.embeddings, dtype=np.float32)
        faiss.normalize_L2(embeddings_matrix)
        self.index.add(embeddings_matrix)

        logger.debug(f"[MiniRAG] Index rebuilt: {len(self.embeddings)} entries")

    def _count_by_category(self) -> Dict[str, int]:
        """Count entries by category."""
        counts = {}
        for entry in self.entries:
            counts[entry.category] = counts.get(entry.category, 0) + 1
        return counts

    # =========================================================================
    # Persistence
    # =========================================================================

    def _load_knowledge_base(self):
        """Load knowledge base from JSON."""
        if not self.knowledge_file.exists():
            logger.warning(f"[MiniRAG] No knowledge base found at {self.knowledge_file}")
            logger.info("[MiniRAG] Creating default knowledge base...")
            self._create_default_knowledge_base()
            return

        try:
            with open(self.knowledge_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            for entry_data in data.get("entries", []):
                entry = KnowledgeEntry.from_dict(entry_data)
                self.entries.append(entry)

                # Embed question
                embedding = self.model.encode(entry.question, convert_to_numpy=True)
                self.embeddings.append(embedding)

            # Build index
            self._rebuild_index()

            logger.info(f"[MiniRAG] Loaded {len(self.entries)} knowledge entries")

        except Exception as e:
            logger.error(f"[MiniRAG] Failed to load knowledge base: {e}")
            self._create_default_knowledge_base()

    def save_knowledge_base(self):
        """Save knowledge base to JSON."""
        try:
            data = {
                "entries": [entry.to_dict() for entry in self.entries],
                "metadata": {
                    "total_entries": len(self.entries),
                    "categories": self._count_by_category(),
                    "last_updated": datetime.now().isoformat()
                }
            }

            with open(self.knowledge_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            logger.info(f"[MiniRAG] Saved {len(self.entries)} entries")

        except Exception as e:
            logger.error(f"[MiniRAG] Failed to save: {e}")

    def _create_default_knowledge_base(self):
        """Create default curated knowledge base."""
        logger.info("[MiniRAG] Creating default knowledge base...")

        # SETUP CATEGORY
        setup_entries = [
            ("How do I start the LLM?",
             "Run `python start_llm.py` in your terminal. The LLM will start on port 8001.",
             ["start llm", "launch model", "run server"]),

            ("How do I start the UI?",
             "Run `python zena_modern.py` to start the modern web UI on port 8080. Open http://localhost:8080 in your browser.",
             ["launch ui", "start interface", "open gui"]),

            ("What ports does ZEN AI RAG use?",
             "Port 8001: Main LLM, Port 8002: Hub, Port 8003: Voice, Port 8080: Web UI, Port 8020: Traffic Controller (Phi-3-mini).",
             ["which ports", "port numbers", "network ports"]),

            ("How do I install dependencies?",
             "Run `pip install -r requirements.txt` to install all required packages.",
             ["install packages", "setup dependencies", "pip install"]),
        ]

        for q, a, aliases in setup_entries:
            self.add_entry(q, a, "setup", aliases=aliases, tags=["getting_started"])

        # CONFIG CATEGORY
        config_entries = [
            ("What is SWARM_ENABLED?",
             "SWARM_ENABLED controls multi-LLM consensus mode. Set to True in config.json to enable multiple LLMs voting on answers for better quality.",
             ["swarm mode", "consensus mode", "multiple llms"]),

            ("What is SWARM_SIZE?",
             "SWARM_SIZE sets how many LLMs participate in consensus voting (default: 3). Only used when SWARM_ENABLED=True.",
             ["number of llms", "swarm count", "llm count"]),

            ("How do I enable traffic controller?",
             "Set TRAFFIC_CONTROLLER_ENABLED=True in config.json. This activates intelligent query routing for cost optimization.",
             ["enable routing", "activate traffic controller", "turn on smart routing"]),

            ("Where is the configuration file?",
             "Main configuration is in config.json at the root directory. You can also use settings.json for UI-specific settings.",
             ["config location", "settings file", "where config"]),
        ]

        for q, a, aliases in config_entries:
            self.add_entry(q, a, "config", aliases=aliases, tags=["configuration"])

        # USAGE CATEGORY
        usage_entries = [
            ("How do I upload a document?",
             "Click the 'Upload Document' button in the UI, select your file (PDF, TXT, MD, etc.), and it will be processed for RAG retrieval.",
             ["add document", "upload file", "ingest document"]),

            ("How do I clear the chat history?",
             "Click the 'Clear Chat' button in the UI sidebar, or use /clear command in the chat.",
             ["reset conversation", "delete history", "clear messages"]),

            ("What file types are supported?",
             "Supported: .txt, .md, .py, .js, .html, .css, .json, .xml, .csv, .log, .yaml, .yml, .pdf, and more. See config.py for full list.",
             ["file formats", "document types", "supported extensions"]),
        ]

        for q, a, aliases in usage_entries:
            self.add_entry(q, a, "usage", aliases=aliases, tags=["how_to"])

        # TROUBLESHOOTING CATEGORY
        trouble_entries = [
            ("LLM is not responding",
             "Check if start_llm.py is running. Verify port 8001 is available. Check logs in the terminal for errors.",
             ["llm not working", "model not responding", "server down"]),

            ("UI shows connection error",
             "Ensure the LLM is running on port 8001. Check if your firewall is blocking the connection. Restart both LLM and UI.",
             ["cannot connect", "connection refused", "network error"]),

            ("Out of memory error",
             "Your system may not have enough RAM for the LLM. Try a smaller model, reduce context length, or close other applications.",
             ["memory error", "oom", "ram issue"]),
        ]

        for q, a, aliases in trouble_entries:
            self.add_entry(q, a, "troubleshoot", aliases=aliases, tags=["errors", "debugging"])

        # FAQ CATEGORY
        faq_entries = [
            ("What is ZEN AI RAG?",
             "ZEN AI RAG is a local, privacy-focused AI assistant with Retrieval-Augmented Generation (RAG) and multi-LLM orchestration.",
             ["what is zen", "about zen ai", "what does zen do"]),

            ("Is my data private?",
             "Yes! Everything runs locally on your machine. No data is sent to external servers unless you explicitly configure external LLM APIs.",
             ["privacy", "data security", "confidential"]),

            ("Can I use multiple LLMs?",
             "Yes! Enable SWARM_ENABLED=True to use multi-LLM consensus for better quality, or use traffic controller for cost-optimal routing.",
             ["multiple models", "several llms", "model ensemble"]),

            ("What is the traffic controller?",
             "A fast classifier (Phi-3-mini) that routes easy queries to a fast LLM and hard queries to a powerful LLM, saving 60%+ cost.",
             ["query routing", "smart routing", "cost optimization"]),
        ]

        for q, a, aliases in faq_entries:
            self.add_entry(q, a, "faq", aliases=aliases, tags=["general"])

        # Save to disk
        self.save_knowledge_base()

        logger.info(f"[MiniRAG] Created default knowledge base with {len(self.entries)} entries")


# =============================================================================
# Utility Functions
# =============================================================================
def create_default_mini_rag(knowledge_file: Optional[Path] = None) -> MiniRAG:
    """Create mini RAG with default configuration."""
    return MiniRAG(knowledge_file=knowledge_file)


if __name__ == "__main__":
    # Test the mini RAG
    logging.basicConfig(level=logging.DEBUG)

    rag = create_default_mini_rag(Path("knowledge_base.json"))

    # Test queries
    test_queries = [
        "How do I start the LLM?",
        "how to launch the model?",
        "What ports are used?",
        "Is my data safe?",
        "How to enable swarm mode?",
        "What is the meaning of life?",  # Should miss
    ]

    print("\nTesting Mini RAG:")
    print("=" * 70)

    for query in test_queries:
        result = rag.search(query)

        if result:
            answer, confidence, category = result
            print(f"\nQuery: {query}")
            print(f"Answer: {answer[:100]}...")
            print(f"Confidence: {confidence:.3f} | Category: {category}")
        else:
            print(f"\nQuery: {query}")
            print("Answer: [NO MATCH]")

    # Stats
    print(f"\n{'='*70}")
    print(f"Statistics:")
    print(json.dumps(rag.get_stats(), indent=2))
