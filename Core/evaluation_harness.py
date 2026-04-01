"""
Core/evaluation_harness.py — RAG Evaluation Harness for ZEN_RAG.

Phase 3.3: Compute standard IR and NLP metrics for RAG quality assessment.

Metrics:
  - NDCG@k  (Normalized Discounted Cumulative Gain)
  - MRR     (Mean Reciprocal Rank)
  - Hit@k   (fraction of queries with at least one relevant doc in top-k)
  - BLEU    (BiLingual Evaluation Understudy, requires nltk)
  - ROUGE-L (Longest Common Subsequence recall, requires rouge-score)
  - Precision@k, Recall@k

Usage:
    harness = EvaluationHarness(rag=my_rag, llm=my_llm)
    results = harness.run(test_cases=[
        {"query": "What is X?", "expected": "X is ...", "relevant_docs": ["url1"]},
    ])
    harness.print_report(results)
    harness.save_report(results, "eval_results.json")
"""

import json
import logging
import math
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


# =============================================================================
# Metric Implementations (pure Python, no heavy deps)
# =============================================================================


def _dcg(relevances: List[float], k: int) -> float:
    """Discounted Cumulative Gain at k."""
    return sum(rel / math.log2(i + 2) for i, rel in enumerate(relevances[:k]))


def _ndcg(retrieved: List[float], ideal: List[float], k: int) -> float:
    """NDCG@k. relevances[i] = relevance score of i-th retrieved doc."""
    idcg = _dcg(sorted(ideal, reverse=True), k)
    if idcg == 0:
        return 0.0
    return _dcg(retrieved, k) / idcg


def _mrr(retrieved: List[float]) -> float:
    """Mean Reciprocal Rank (expects relevances list; returns 1/rank for first relevant)."""
    for rank, rel in enumerate(retrieved, 1):
        if rel > 0:
            return 1.0 / rank
    return 0.0


def _hit_at_k(retrieved: List[float], k: int) -> float:
    """1 if any relevant doc in top-k, else 0."""
    return 1.0 if any(r > 0 for r in retrieved[:k]) else 0.0


def _precision_at_k(retrieved: List[float], k: int) -> float:
    """Fraction of top-k retrieved docs that are relevant."""
    if k == 0:
        return 0.0
    return sum(1 for r in retrieved[:k] if r > 0) / k


def _recall_at_k(retrieved: List[float], n_relevant: int, k: int) -> float:
    """Fraction of all relevant docs found in top-k."""
    if n_relevant == 0:
        return 0.0
    return sum(1 for r in retrieved[:k] if r > 0) / n_relevant


def _bleu_score(reference: str, hypothesis: str) -> float:
    """Compute sentence BLEU-1 (unigram precision). No external deps."""
    ref_tokens = reference.lower().split()
    hyp_tokens = hypothesis.lower().split()
    if not hyp_tokens or not ref_tokens:
        return 0.0
    ref_set = set(ref_tokens)
    matches = sum(1 for t in hyp_tokens if t in ref_set)
    return matches / len(hyp_tokens)


def _rouge_l(reference: str, hypothesis: str) -> float:
    """ROUGE-L F1 via LCS (pure Python)."""
    ref = reference.lower().split()
    hyp = hypothesis.lower().split()
    if not ref or not hyp:
        return 0.0

    # LCS dynamic programming
    m, n = len(ref), len(hyp)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            dp[i][j] = dp[i - 1][j - 1] + 1 if ref[i - 1] == hyp[j - 1] else max(dp[i - 1][j], dp[i][j - 1])
    lcs = dp[m][n]

    precision = lcs / n
    recall = lcs / m
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


# =============================================================================
# EvaluationHarness
# =============================================================================


class EvaluationHarness:
    """
    End-to-end RAG evaluation harness.

    Supports:
      - Retrieval metrics: NDCG@k, MRR, Hit@k, Precision@k, Recall@k
      - Generation metrics: BLEU, ROUGE-L
      - Latency tracking
      - JSON report export
    """

    def __init__(
        self,
        rag: Any,
        llm: Any = None,
        k: int = 5,
        output_dir: str = "eval_results",
    ):
        """
        Args:
            rag: LocalRAG instance.
            llm: Optional LLM for answer generation evaluation.
            k: Top-k for retrieval metrics.
            output_dir: Directory for saved reports.
        """
        self.rag = rag
        self.llm = llm
        self.k = k
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def run(
        self,
        test_cases: List[Dict],
        verbose: bool = True,
    ) -> Dict:
        """
        Run evaluation over a list of test cases.

        Each test case dict:
          - query (str): The question
          - expected (str): Reference answer for BLEU/ROUGE
          - relevant_docs (List[str]): URLs/titles of relevant documents
          - relevance_scores (Dict[str, float]): Optional graded relevance (0-1)

        Returns:
            Aggregated metrics dict + per-sample results.
        """
        per_sample = []
        t0_total = time.time()

        for i, tc in enumerate(test_cases):
            query = tc.get("query", "")
            expected = tc.get("expected", "")
            relevant_docs = set(tc.get("relevant_docs", []))
            rel_scores_map = tc.get("relevance_scores", {})

            if not query:
                continue

            if verbose:
                logger.info(f"[Eval] Sample {i + 1}/{len(test_cases)}: {query[:60]}...")

            # Retrieve
            t0 = time.time()
            try:
                retrieved = self.rag.hybrid_search(query, k=self.k, rerank=True)
            except Exception as e:
                logger.warning(f"[Eval] Search failed for query '{query}': {e}")
                retrieved = []
            latency = time.time() - t0

            # Compute relevance labels
            relevances = self._compute_relevances(retrieved, relevant_docs, rel_scores_map)
            ideal = sorted(relevances, reverse=True)

            # Retrieval metrics
            sample_metrics = {
                "query": query,
                "latency_s": round(latency, 3),
                "n_retrieved": len(retrieved),
                f"ndcg@{self.k}": round(_ndcg(relevances, ideal, self.k), 4),
                "mrr": round(_mrr(relevances), 4),
                f"hit@{self.k}": _hit_at_k(relevances, self.k),
                f"precision@{self.k}": round(_precision_at_k(relevances, self.k), 4),
                f"recall@{self.k}": round(_recall_at_k(relevances, len(relevant_docs), self.k), 4),
                "bleu": 0.0,
                "rouge_l": 0.0,
                "generated_answer": "",
            }

            # Generation metrics (if LLM available and expected answer given)
            if self.llm and expected:
                generated = self._generate_answer(query, retrieved)
                sample_metrics["generated_answer"] = generated
                if generated:
                    sample_metrics["bleu"] = round(_bleu_score(expected, generated), 4)
                    sample_metrics["rouge_l"] = round(_rouge_l(expected, generated), 4)

            per_sample.append(sample_metrics)

        total_time = time.time() - t0_total

        # Aggregate
        agg = self._aggregate(per_sample, total_time)
        return {"summary": agg, "samples": per_sample}

    def _compute_relevances(
        self,
        retrieved: List[Dict],
        relevant_docs: set,
        rel_scores_map: Dict[str, float],
    ) -> List[float]:
        """Compute relevance score for each retrieved chunk."""
        relevances = []
        for chunk in retrieved:
            url = chunk.get("url", "") or ""
            title = chunk.get("title", "") or ""
            combined = url + " " + title

            # Graded relevance if provided
            if rel_scores_map:
                score = max(
                    rel_scores_map.get(url, 0.0),
                    rel_scores_map.get(title, 0.0),
                )
                relevances.append(score)
            else:
                # Binary: relevant if url/title matches any relevant_doc
                is_rel = any(rd in combined or combined in rd for rd in relevant_docs if rd)
                relevances.append(1.0 if is_rel else 0.0)

        return relevances

    def _generate_answer(self, query: str, context_chunks: List[Dict]) -> str:
        """Generate answer using LLM for BLEU/ROUGE evaluation."""
        try:
            context = "\n\n".join(c.get("text", "")[:500] for c in context_chunks[:5])
            prompt = f"Answer concisely based on context:\n\nContext:\n{context}\n\nQuestion: {query}\n\nAnswer:"
            if hasattr(self.llm, "query_sync"):
                return self.llm.query_sync(prompt, max_tokens=200).strip()
            elif hasattr(self.llm, "generate"):
                return self.llm.generate(prompt).strip()
        except Exception as e:
            logger.warning(f"[Eval] LLM generation failed: {e}")
        return ""

    def _aggregate(self, per_sample: List[Dict], total_time: float) -> Dict:
        """Compute mean metrics across all samples."""
        if not per_sample:
            return {}

        metric_keys = [k for k in per_sample[0] if isinstance(per_sample[0][k], (int, float))]
        agg = {
            "n_samples": len(per_sample),
            "total_time_s": round(total_time, 2),
            "avg_latency_s": round(sum(s["latency_s"] for s in per_sample) / len(per_sample), 3),
        }
        for key in metric_keys:
            values = [s[key] for s in per_sample if key in s]
            if values:
                agg[f"mean_{key}"] = round(sum(values) / len(values), 4)

        return agg

    def print_report(self, results: Dict):
        """Print formatted evaluation report."""
        summary = results.get("summary", {})
        print("\n" + "=" * 60)
        print("ZEN_RAG EVALUATION REPORT")
        print("=" * 60)
        print(f"Samples evaluated : {summary.get('n_samples', 0)}")
        print(f"Total time        : {summary.get('total_time_s', 0):.1f}s")
        print(f"Avg latency       : {summary.get('avg_latency_s', 0):.3f}s")
        print("-" * 60)
        for key, val in summary.items():
            if key.startswith("mean_") and "latency" not in key:
                metric_name = key.replace("mean_", "").upper()
                print(f"{metric_name:<20}: {val:.4f}")
        print("=" * 60)

    def save_report(self, results: Dict, filename: str = None) -> Path:
        """Save evaluation results to JSON."""
        if not filename:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"eval_{ts}.json"
        out_path = self.output_dir / filename
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        logger.info(f"[Eval] Report saved to {out_path}")
        return out_path
