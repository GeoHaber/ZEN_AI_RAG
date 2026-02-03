import asyncio
import logging
import json
import time
from pathlib import Path
from async_backend import AsyncZenAIBackend
from zena_mode.rag_pipeline import LocalRAG

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("QualityBench")

# Test Dataset: [Question, Reference Answer]
QA_PAIRS = [
    ["What is ZenAI?", "ZenAI is an AI-powered assistant integrated with Qwen and RAG capabilities."],
    ["How many experts can run in a swarm?", "The swarm can be dynamically scaled, often up to 5 or more experts depending on hardware."],
    ["What is RAG?", "RAG or Retrieval-Augmented Generation is a technique to provide external knowledge to an LLM."],
    ["Who created Qwen?", "Qwen was created by the Alibaba Cloud (Qwen team)."],
    ["If ZenAI 2.0 has 5 pillars and we finish 3, how many are left?", "There are 2 pillars left (5 minus 3 is 2)."],
    ["Which file handles the multi-LLM consensus logic?", "The consensus logic is handled in arbitrage.py (specifically the SwarmArbitrator class)."],
    ["Explain the benefit of latency-aware routing in one sentence.", "Latency-aware routing ensures that queries are sent to the fastest available experts, minimizing overall response time."],
    ["What happens if an expert provides a response with low fact-check score?", "The arbitrator applies a hallucination penalty, marking the agent as not selected for reliability tracking."],
]

async def run_benchmark():
    logger.info("🚀 Starting ZenAI Quality Benchmark...")
    backend = AsyncZenAIBackend()
    rag = LocalRAG() # Used for semantic similarity comparison
    
    results = []
    
    async with backend:
        if not await backend.health_check():
            logger.error("❌ Backend offline! Start 'python start_llm.py' first.")
            return

        for question, reference in QA_PAIRS:
            logger.info(f"❓ Testing: {question}")
            
            # --- RAG INJECTION ---
            final_prompt = question
            try:
                # Use the same RAG logic as ui/handlers.py
                logger.info(f"[RAG] Searching knowledge base for: '{question[:30]}...'")
                relevant_chunks = rag.hybrid_search(question, k=5, alpha=0.5)
                if relevant_chunks:
                    logger.info(f"[RAG] Found {len(relevant_chunks)} chunks.")
                    context_parts = [f"Source: {c.get('title', 'Unknown')}\n{c['text']}" for c in relevant_chunks]
                    context = "\n\n".join(context_parts)
                    final_prompt = f"SOURCES:\n{context}\n\nUSER QUESTION: {question}\n\nANSWER:"
            except Exception as re:
                logger.error(f"[RAG] Search failed: {re}")

            full_response = ""
            start_time = time.time()
            
            async for chunk in backend.send_message_async(final_prompt):
                full_response += chunk
            
            duration = time.time() - start_time
            
            # --- Evaluation ---
            # 1. Semantic Similarity using RAG's embedding model
            ref_emb = rag.model.encode([reference], normalize_embeddings=True)[0]
            ans_emb = rag.model.encode([full_response], normalize_embeddings=True)[0]
            
            import numpy as np
            similarity = np.dot(ref_emb, ans_emb)
            
            logger.info(f"✅ Score: {similarity:.2f} | Time: {duration:.1f}s")
            
            results.append({
                "question": question,
                "response": full_response,
                "score": float(similarity),
                "duration": duration
            })
            
    # Save results
    avg_score = sum(r['score'] for r in results) / len(results)
    avg_duration = sum(r['duration'] for r in results) / len(results)
    
    summary = {
        "timestamp": time.time(),
        "avg_quality_score": avg_score,
        "avg_latency": avg_duration,
        "detailed_results": results
    }
    
    report_path = Path("tests/quality_report.json")
    with open(report_path, "w") as f:
        json.dump(summary, f, indent=4)
        
    logger.info(f"\n🏆 Benchmark Complete!")
    logger.info(f"📊 AVG Quality: {avg_score:.2f}")
    logger.info(f"⏱️ AVG Latency: {avg_duration:.1f}s")
    logger.info(f"📄 Report saved to {report_path}")

if __name__ == "__main__":
    asyncio.run(run_benchmark())
