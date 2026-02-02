#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
intelligent_router.py - The Brain and Heart of ZEN AI RAG

Multi-tier intelligent routing system combining:
- Tier 0: Semantic Cache (instant responses)
- Tier 1: Mini RAG (local knowledge)
- Tier 2: Traffic Controller (fast classifier)
- Tier 3: Smart Routing (cost-optimal LLM selection)
- Tier 4: Full Consensus (hard questions)

Based on 2024-2025 production research from OpenAI, Anthropic, Stanford, ETH Zurich.
Target: 90%+ queries < 200ms, 70%+ cost savings, 95%+ accuracy.
"""
import asyncio
import time
import logging
import json
from pathlib import Path
from typing import AsyncGenerator, Optional, Tuple, Dict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger("IntelligentRouter")

# Optional imports
try:
    from semantic_cache import SemanticCache, CacheConfig
    from mini_rag import MiniRAG, MiniRAGConfig
    CACHE_AVAILABLE = True
except ImportError:
    CACHE_AVAILABLE = False
    logger.warning("[Router] semantic_cache or mini_rag not available")


# =============================================================================
# Configuration
# =============================================================================
class RoutingTier(Enum):
    """Routing tier for tracking."""
    CACHE = "cache"
    MINI_RAG = "mini_rag"
    FAST_LLM = "fast_llm"
    POWERFUL_LLM = "powerful_llm"
    CONSENSUS = "consensus"
    ERROR = "error"


@dataclass
class RouterConfig:
    """Intelligent router configuration."""

    # Tier enablement
    enable_cache: bool = True
    enable_mini_rag: bool = True
    enable_traffic_controller: bool = True

    # Cache settings
    cache_dir: Path = field(default_factory=lambda: Path("cache"))

    # Mini RAG settings
    knowledge_file: Path = field(default_factory=lambda: Path("knowledge_base.json"))

    # Traffic controller settings
    traffic_controller_port: int = 8020
    traffic_controller_enabled: bool = True

    # Confidence thresholds
    mini_rag_confidence: float = 0.85
    fast_llm_confidence: float = 0.7
    consensus_threshold: float = 0.7

    # Cost tracking
    track_costs: bool = True
    cost_per_token_fast: float = 0.00001    # $0.01 per 1M tokens
    cost_per_token_powerful: float = 0.00003  # $0.03 per 1M tokens

    # Monitoring
    log_routing_decisions: bool = True
    save_routing_history: bool = True


@dataclass
class RoutingDecision:
    """Single routing decision record."""
    query: str
    query_hash: str
    tier: RoutingTier
    latency_ms: float
    cost_usd: float
    confidence: float
    timestamp: datetime = field(default_factory=datetime.now)
    success: bool = True
    error_msg: str = ""

    def to_dict(self) -> Dict:
        return {
            "query_hash": self.query_hash,
            "tier": self.tier.value,
            "latency_ms": self.latency_ms,
            "cost_usd": self.cost_usd,
            "confidence": self.confidence,
            "timestamp": self.timestamp.isoformat(),
            "success": self.success,
            "error_msg": self.error_msg
        }


@dataclass
class RouterStats:
    """Router statistics."""
    total_queries: int = 0
    tier_counts: Dict[str, int] = field(default_factory=dict)
    total_cost_usd: float = 0.0
    total_latency_ms: float = 0.0
    errors: int = 0

    def record(self, decision: RoutingDecision):
        """Record a routing decision."""
        self.total_queries += 1
        tier = decision.tier.value
        self.tier_counts[tier] = self.tier_counts.get(tier, 0) + 1
        self.total_cost_usd += decision.cost_usd
        self.total_latency_ms += decision.latency_ms
        if not decision.success:
            self.errors += 1

    def get_summary(self) -> Dict:
        """Get summary statistics."""
        if self.total_queries == 0:
            return {"total_queries": 0}

        return {
            "total_queries": self.total_queries,
            "avg_latency_ms": self.total_latency_ms / self.total_queries,
            "avg_cost_usd": self.total_cost_usd / self.total_queries,
            "total_cost_usd": self.total_cost_usd,
            "error_rate": f"{self.errors / self.total_queries * 100:.2f}%",
            "tier_distribution": {
                tier: f"{count / self.total_queries * 100:.1f}%"
                for tier, count in self.tier_counts.items()
            },
            "cost_savings_vs_all_powerful": self._calculate_savings()
        }

    def _calculate_savings(self) -> str:
        """Calculate cost savings vs always using powerful LLM."""
        # Assume powerful LLM would cost 3x more on average
        baseline_cost = self.total_queries * 0.0003  # $0.0003 per query
        if baseline_cost == 0:
            return "0%"
        savings = (baseline_cost - self.total_cost_usd) / baseline_cost * 100
        return f"{savings:.1f}%"


# =============================================================================
# Intelligent Router
# =============================================================================
class IntelligentRouter:
    """
    Multi-tier intelligent routing system.

    Flow:
    1. Check semantic cache (Tier 0)
    2. Check mini RAG (Tier 1)
    3. Classify with traffic controller (Tier 2)
    4. Route to appropriate LLM(s) (Tier 3/4)
    """

    def __init__(
        self,
        config: Optional[RouterConfig] = None,
        swarm_arbitrator: Optional[object] = None
    ):
        self.config = config or RouterConfig()
        self.swarm = swarm_arbitrator  # Reference to SwarmArbitrator

        # Initialize cache (Tier 0)
        self.cache: Optional[SemanticCache] = None
        if CACHE_AVAILABLE and self.config.enable_cache:
            try:
                cache_config = CacheConfig()
                self.cache = SemanticCache(cache_config, self.config.cache_dir)
                logger.info("[Router] Semantic cache initialized")
            except Exception as e:
                logger.warning(f"[Router] Failed to initialize cache: {e}")

        # Initialize mini RAG (Tier 1)
        self.mini_rag: Optional[MiniRAG] = None
        if CACHE_AVAILABLE and self.config.enable_mini_rag:
            try:
                mini_rag_config = MiniRAGConfig()
                self.mini_rag = MiniRAG(mini_rag_config, self.config.knowledge_file)
                logger.info("[Router] Mini RAG initialized")
            except Exception as e:
                logger.warning(f"[Router] Failed to initialize mini RAG: {e}")

        # Statistics
        self.stats = RouterStats()
        self.routing_history: List[RoutingDecision] = []

        logger.info("[Router] Intelligent router initialized")

    # =========================================================================
    # Main Routing Method
    # =========================================================================

    async def route(
        self,
        query: str,
        system_prompt: str = "You are a helpful AI assistant.",
        stream: bool = True
    ) -> AsyncGenerator[str, None]:
        """
        Main routing method - the brain of the system.

        Args:
            query: User query
            system_prompt: System prompt for LLM
            stream: Whether to stream response

        Yields:
            Response chunks
        """
        start_time = time.time()
        query_hash = self._hash_query(query)

        try:
            # TIER 0: Semantic Cache (instant)
            if self.cache:
                cache_result = self.cache.get(query)

                if cache_result:
                    answer, source, confidence = cache_result
                    latency_ms = (time.time() - start_time) * 1000

                    # Record decision
                    decision = RoutingDecision(
                        query=query[:100],
                        query_hash=query_hash,
                        tier=RoutingTier.CACHE,
                        latency_ms=latency_ms,
                        cost_usd=0.0,  # No cost for cache
                        confidence=confidence
                    )
                    self._record_decision(decision)

                    # Show cache indicator
                    yield f"⚡ **Instant (cached)** - {source}\n\n"
                    yield answer
                    return

            # TIER 1: Mini RAG (local knowledge)
            if self.mini_rag:
                mini_rag_result = self.mini_rag.search(query)

                if mini_rag_result:
                    answer, confidence, category = mini_rag_result

                    if confidence >= self.config.mini_rag_confidence:
                        latency_ms = (time.time() - start_time) * 1000

                        # Record decision
                        decision = RoutingDecision(
                            query=query[:100],
                            query_hash=query_hash,
                            tier=RoutingTier.MINI_RAG,
                            latency_ms=latency_ms,
                            cost_usd=0.0,  # No LLM cost
                            confidence=confidence
                        )
                        self._record_decision(decision)

                        # Cache this answer
                        if self.cache:
                            self.cache.put(
                                query, answer,
                                source="mini_rag",
                                confidence=confidence
                            )

                        # Show mini RAG indicator
                        yield f"📚 **Knowledge Base** ({category}, {confidence:.0%} confidence)\n\n"
                        yield answer
                        return

            # TIER 2-4: Route to LLM(s) via SwarmArbitrator
            if self.swarm:
                # Delegate to SwarmArbitrator which handles:
                # - Tier 2: Traffic controller classification
                # - Tier 3: Smart routing (fast vs powerful)
                # - Tier 4: Full consensus (if needed)

                tier = RoutingTier.FAST_LLM  # Will be updated by swarm
                response_text = ""

                async for chunk in self.swarm.get_consensus(
                    query,
                    system_prompt=system_prompt,
                    verbose=False
                ):
                    response_text += chunk
                    yield chunk

                # Estimate tier from swarm (simplified)
                # In production, SwarmArbitrator would report this
                if len(response_text) > 0:
                    latency_ms = (time.time() - start_time) * 1000

                    # Estimate cost (simplified)
                    tokens = len(response_text.split()) * 1.3  # Rough estimate
                    cost_usd = tokens * self.config.cost_per_token_fast

                    decision = RoutingDecision(
                        query=query[:100],
                        query_hash=query_hash,
                        tier=tier,
                        latency_ms=latency_ms,
                        cost_usd=cost_usd,
                        confidence=0.8  # Default
                    )
                    self._record_decision(decision)

                    # Cache high-quality LLM responses
                    if self.cache and len(response_text) > 20:
                        self.cache.put(
                            query, response_text,
                            source="llm",
                            confidence=0.8
                        )

            else:
                # No swarm available - error
                yield "❌ **Error:** No LLM backend available\n"
                decision = RoutingDecision(
                    query=query[:100],
                    query_hash=query_hash,
                    tier=RoutingTier.ERROR,
                    latency_ms=(time.time() - start_time) * 1000,
                    cost_usd=0.0,
                    confidence=0.0,
                    success=False,
                    error_msg="No swarm arbitrator"
                )
                self._record_decision(decision)

        except Exception as e:
            logger.error(f"[Router] Error routing query: {e}")
            yield f"❌ **Error:** {str(e)}\n"

            decision = RoutingDecision(
                query=query[:100],
                query_hash=query_hash,
                tier=RoutingTier.ERROR,
                latency_ms=(time.time() - start_time) * 1000,
                cost_usd=0.0,
                confidence=0.0,
                success=False,
                error_msg=str(e)
            )
            self._record_decision(decision)

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _hash_query(self, query: str) -> str:
        """Generate hash of query."""
        import hashlib
        normalized = ' '.join(query.lower().strip().split())
        return hashlib.sha256(normalized.encode()).hexdigest()[:16]

    def _record_decision(self, decision: RoutingDecision):
        """Record routing decision."""
        self.stats.record(decision)
        self.routing_history.append(decision)

        if self.config.log_routing_decisions:
            logger.info(
                f"[Router] {decision.tier.value.upper()}: "
                f"{decision.latency_ms:.1f}ms, "
                f"${decision.cost_usd:.6f}, "
                f"{decision.confidence:.0%} confidence"
            )

    def get_stats(self) -> Dict:
        """Get router statistics."""
        stats = self.stats.get_summary()

        # Add tier-specific stats
        if self.cache:
            stats["cache_stats"] = self.cache.get_stats()

        if self.mini_rag:
            stats["mini_rag_stats"] = self.mini_rag.get_stats()

        return stats

    def export_history(self, filepath: Path):
        """Export routing history to JSON."""
        try:
            data = {
                "summary": self.get_stats(),
                "history": [d.to_dict() for d in self.routing_history[-1000:]],  # Last 1000
                "timestamp": datetime.now().isoformat()
            }

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)

            logger.info(f"[Router] Exported history to {filepath}")

        except Exception as e:
            logger.error(f"[Router] Failed to export history: {e}")

    def print_performance_report(self):
        """Print detailed performance report."""
        stats = self.get_stats()

        print("\n" + "="*70)
        print("INTELLIGENT ROUTER PERFORMANCE REPORT")
        print("="*70)

        print(f"\n📊 Overall Statistics:")
        print(f"  Total Queries:    {stats['total_queries']}")
        print(f"  Avg Latency:      {stats.get('avg_latency_ms', 0):.1f}ms")
        print(f"  Avg Cost:         ${stats.get('avg_cost_usd', 0):.6f}")
        print(f"  Total Cost:       ${stats.get('total_cost_usd', 0):.4f}")
        print(f"  Error Rate:       {stats.get('error_rate', '0%')}")
        print(f"  Cost Savings:     {stats.get('cost_savings_vs_all_powerful', '0%')}")

        print(f"\n🎯 Tier Distribution:")
        for tier, percentage in stats.get('tier_distribution', {}).items():
            print(f"  {tier:20s}: {percentage}")

        if 'cache_stats' in stats:
            cache_stats = stats['cache_stats']
            print(f"\n⚡ Cache Performance:")
            print(f"  Hit Rate:         {cache_stats.get('hit_rate', '0%')}")
            print(f"  Total Entries:    {cache_stats.get('total_entries', 0)}")
            print(f"  Exact Matches:    {cache_stats.get('exact_matches', 0)}")
            print(f"  Semantic Matches: {cache_stats.get('semantic_matches', 0)}")

        if 'mini_rag_stats' in stats:
            rag_stats = stats['mini_rag_stats']
            print(f"\n📚 Mini RAG Performance:")
            print(f"  Hit Rate:         {rag_stats.get('hit_rate', '0%')}")
            print(f"  Total Entries:    {rag_stats.get('total_entries', 0)}")
            print(f"  High Conf Hits:   {rag_stats.get('high_confidence_hits', 0)}")

        print("\n" + "="*70)


# =============================================================================
# Factory Functions
# =============================================================================
def create_intelligent_router(
    swarm_arbitrator: Optional[object] = None,
    config: Optional[RouterConfig] = None
) -> IntelligentRouter:
    """Create intelligent router with default configuration."""
    return IntelligentRouter(config=config, swarm_arbitrator=swarm_arbitrator)


# =============================================================================
# Main (for testing)
# =============================================================================
if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)

    # Create router (without swarm for testing cache/rag only)
    router = create_intelligent_router()

    # Test queries
    async def test_router():
        test_queries = [
            "How do I start the LLM?",
            "What is SWARM_ENABLED?",
            "How to launch the model?",  # Should hit cache
            "What is the meaning of life?",  # Should miss all tiers
        ]

        for query in test_queries:
            print(f"\n{'='*70}")
            print(f"Query: {query}")
            print(f"{'='*70}")

            async for chunk in router.route(query):
                print(chunk, end='', flush=True)

            print("\n")

        # Print report
        router.print_performance_report()

    # Run test
    asyncio.run(test_router())
