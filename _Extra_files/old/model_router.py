# -*- coding: utf-8 -*-
"""
model_router.py - Intelligent Model Orchestrator
Uses fast model for intent classification, routes to best model for task execution.
"""
import json
import asyncio
import logging
import time
import subprocess
import httpx
import re
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any, Tuple
from datetime import datetime, timedelta
from enum import Enum
from utils import safe_print
from config_system import EMOJI

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("ModelRouter")

# ============================================================================
# CONFIGURATION
# ============================================================================
MODELS_DIR = Path("C:/AI/Models")
LLAMA_SERVER = Path("C:/AI/_bin/llama-server.exe")
ROUTER_PORT = 8099  # Fast classifier model
WORKER_PORT = 8001  # Main worker model
CONFIG_FILE = Path("model_router_config.json")

class TaskType(Enum):
    """Task categories for routing."""
    CODE_GENERATION = "code_generation"
    CODE_EXPLANATION = "code_explanation"
    CODE_DEBUG = "code_debug"
    REASONING = "reasoning"
    MATH = "math"
    GENERAL_CHAT = "general_chat"
    SUMMARIZATION = "summarization"
    EXTRACTION = "extraction"
    CLASSIFICATION = "classification"
    CREATIVE = "creative"
    PROFESSIONAL = "professional"
    QUICK_QA = "quick_qa"


# ============================================================================
# INTENT CLASSIFIER
# ============================================================================
class IntentClassifier:
    """
    Ultra-fast intent classification using tiny model.
    Runs on a separate port to not block main inference.
    """
    
    CLASSIFICATION_PROMPT = """Classify the user's intent into exactly ONE category.

Categories:
- code_generation: Writing new code, functions, classes
- code_explanation: Explaining what code does
- code_debug: Finding and fixing bugs
- reasoning: Complex logic, analysis, step-by-step thinking
- math: Mathematical calculations, equations, proofs
- general_chat: Casual conversation, greetings
- summarization: Condensing text or information
- extraction: Pulling specific data from text
- classification: Categorizing or labeling items
- creative: Writing stories, poems, creative content
- professional: Formal documents, emails, reports
- quick_qa: Simple factual questions

User query: "{query}"

Respond with ONLY the category name, nothing else."""

    def __init__(self, port: int = ROUTER_PORT):
        self.port = port
        self.api_url = f"http://127.0.0.1:{port}/v1/chat/completions"
        self.process: Optional[subprocess.Popen] = None
        self.model_path: Optional[str] = None
        
    async def start(self, model_path: str) -> bool:
        """Start the classifier model server."""
        self.model_path = model_path
        
        # Check if already running
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"http://127.0.0.1:{self.port}/health", timeout=1)
                if resp.status_code == 200:
                    logger.info(f"[Classifier] Already running on port {self.port}")
                    return True
        except:
            pass
        
        logger.info(f"[Classifier] Starting with {Path(model_path).name}")
        self.process = subprocess.Popen(
            [str(LLAMA_SERVER),
             "--model", model_path,
             "--ctx-size", "2048",
             "--port", str(self.port),
             "--threads", "4"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        
        # Wait for ready
        async with httpx.AsyncClient() as client:
            for _ in range(30):
                try:
                    resp = await client.get(f"http://127.0.0.1:{self.port}/health", timeout=1)
                    if resp.status_code == 200:
                        logger.info("[Classifier] Ready")
                        return True
                except:
                    pass
                await asyncio.sleep(0.5)
        
        logger.error("[Classifier] Failed to start")
        return False
    
    def stop(self):
        """Stop the classifier server."""
        if self.process:
            self.process.terminate()
            self.process = None
    
    async def classify_and_take(self, query: str) -> Tuple[TaskType, str]:
        """
        Classify intent AND get an immediate 'Butler' take.
        Returns (task_type, butler_response).
        """
        prompt = f"""You are the ZenAI Butler. First, classify the user's intent into ONE category. 
Second, provide an extremely brief (1 sentence) immediate acknowledgement or 'first take'.

Categories: code_generation, code_explanation, code_debug, reasoning, math, general_chat, summarization, extraction, classification, creative, professional, quick_qa.

User Query: "{query[:200]}"

Format:
CATEGORY: <category>
BUTLER: <one sentence take>"""
        
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    self.api_url,
                    json={
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": 100,
                        "temperature": 0.3
                    },
                    timeout=5
                )
                
                if resp.status_code == 200:
                    content = resp.json()["choices"][0]["message"]["content"].strip()
                    
                    category = "general_chat"
                    butler_take = "Processing your request..."
                    
                    for line in content.split('\n'):
                        if line.upper().startswith("CATEGORY:"):
                            cat_str = line.split(":", 1)[1].strip().lower()
                            for t in TaskType:
                                if t.value in cat_str:
                                    category = t.value
                                    break
                        if line.upper().startswith("BUTLER:"):
                            butler_take = line.split(":", 1)[1].strip()
                    
                    return TaskType(category), butler_take
                    
        except Exception as e:
            logger.warning(f"[Butler] Error: {e}")
        
        return self._keyword_fallback(query), "I'll look into that for you immediately."
    
    def _keyword_fallback(self, query: str) -> TaskType:
        """Keyword-based fallback classification."""
        q = query.lower()
        
        if any(kw in q for kw in ["write", "create", "implement", "function", "class", "code"]):
            return TaskType.CODE_GENERATION
        elif any(kw in q for kw in ["explain", "what does", "how does", "understand"]):
            return TaskType.CODE_EXPLANATION
        elif any(kw in q for kw in ["bug", "fix", "error", "wrong", "debug", "issue"]):
            return TaskType.CODE_DEBUG
        elif any(kw in q for kw in ["calculate", "math", "equation", "solve", "compute"]):
            return TaskType.MATH
        elif any(kw in q for kw in ["think", "analyze", "reason", "why", "logic"]):
            return TaskType.REASONING
        elif any(kw in q for kw in ["summarize", "summary", "tldr", "brief"]):
            return TaskType.SUMMARIZATION
        elif any(kw in q for kw in ["extract", "find", "get", "pull out"]):
            return TaskType.EXTRACTION
        elif any(kw in q for kw in ["write a story", "poem", "creative", "imagine"]):
            return TaskType.CREATIVE
        elif any(kw in q for kw in ["email", "report", "formal", "professional"]):
            return TaskType.PROFESSIONAL
        elif "?" in q and len(q) < 100:
            return TaskType.QUICK_QA
        else:
            return TaskType.GENERAL_CHAT


# ============================================================================
# MODEL REGISTRY
# ============================================================================
@dataclass
class ModelInfo:
    """Information about an available model."""
    name: str
    path: str
    size_gb: float
    tasks: List[str] = field(default_factory=list)
    avg_tps: float = 0.0
    quality_score: float = 0.0
    last_benchmark: Optional[str] = None
    
    def score_for_task(self, task: TaskType) -> float:
        """Calculate suitability score for a task."""
        if task.value in self.tasks:
            # Primary task match
            return self.quality_score * 1.2
        return self.quality_score * 0.5


class ModelRegistry:
    """Registry of available models with their capabilities."""
    
    # Default task assignments based on model characteristics
    DEFAULT_ASSIGNMENTS = {
        # Tiny models - classification/routing
        "SmolLM2-135M": ["classification", "quick_qa"],
        "qwen2.5-0.5b": ["classification", "extraction", "quick_qa"],
        
        # Small models - fast tasks  
        "Llama-3.2-3B": ["quick_qa", "summarization", "general_chat"],
        "Phi-3.5-mini": ["quick_qa", "math", "general_chat"],
        
        # Medium models - balanced
        "Mistral-7B": ["general_chat", "summarization", "quick_qa", "extraction"],
        "deepseek-coder-6.7b": ["code_generation", "code_explanation", "code_debug"],
        "qwen2.5-coder-7b": ["code_generation", "code_explanation", "code_debug"],
        "gemma-2-9b": ["general_chat", "summarization", "creative"],
        
        # Large models - quality tasks
        "Qwen2.5-14B": ["reasoning", "general_chat", "professional"],
        "Qwen2.5-Coder-14B": ["code_generation", "code_explanation", "code_debug"],
        "DeepSeek-R1-Distill": ["reasoning", "math", "code_debug"],
        
        # Premium models - best quality
        "Mistral-Small-24B": ["professional", "creative", "reasoning", "general_chat"],
        "GLM-4.7-Flash": ["reasoning", "code_generation", "general_chat", "math"],
    }
    
    # Quality tiers (0-100)
    QUALITY_TIERS = {
        "SmolLM2": 30,
        "qwen2.5-0.5b": 40,
        "Llama-3.2-3B": 55,
        "Phi-3.5-mini": 60,
        "Mistral-7B": 70,
        "deepseek-coder-6.7b": 72,
        "qwen2.5-coder-7b": 75,
        "gemma-2-9b": 75,
        "Qwen2.5-14B": 82,
        "Qwen2.5-Coder-14B": 85,
        "DeepSeek-R1-Distill": 88,
        "Mistral-Small-24B": 90,
        "GLM-4.7-Flash": 88,
    }
    
    def __init__(self, models_dir: Path = MODELS_DIR):
        self.models_dir = models_dir
        self.models: Dict[str, ModelInfo] = {}
        self.scan_models()
    
    def scan_models(self):
        """Scan for available GGUF models."""
        self.models.clear()
        
        for f in self.models_dir.glob("*.gguf"):
            name = f.stem
            size_gb = f.stat().st_size / (1024**3)
            
            # Determine tasks and quality
            tasks = []
            quality = 50  # default
            
            for key, assigned_tasks in self.DEFAULT_ASSIGNMENTS.items():
                if key.lower() in name.lower():
                    tasks = assigned_tasks
                    break
            
            for key, tier_quality in self.QUALITY_TIERS.items():
                if key.lower() in name.lower():
                    quality = tier_quality
                    break
            
            self.models[name] = ModelInfo(
                name=name,
                path=str(f),
                size_gb=round(size_gb, 2),
                tasks=tasks,
                quality_score=quality
            )
        
        logger.info(f"[Registry] Found {len(self.models)} models")
    
    def get_best_for_task(self, task: TaskType, max_size_gb: Optional[float] = None) -> Optional[ModelInfo]:
        """Get the best model for a specific task."""
        candidates = []
        
        for model in self.models.values():
            if max_size_gb and model.size_gb > max_size_gb:
                continue
            
            score = model.score_for_task(task)
            if score > 0:
                candidates.append((score, model))
        
        if not candidates:
            # Fallback: return largest model that fits
            valid = [m for m in self.models.values() 
                    if not max_size_gb or m.size_gb <= max_size_gb]
            if valid:
                return max(valid, key=lambda m: m.quality_score)
            return None
        
        # Return highest scoring
        candidates.sort(key=lambda x: x[0], reverse=True)
        return candidates[0][1]
    
    def get_fastest_model(self) -> Optional[ModelInfo]:
        """Get the smallest/fastest model for classification."""
        if not self.models:
            return None
        return min(self.models.values(), key=lambda m: m.size_gb)
    
    def list_models(self) -> List[Dict[str, Any]]:
        """List all models with their info."""
        return [
            {
                "name": m.name,
                "size_gb": m.size_gb,
                "tasks": m.tasks,
                "quality": m.quality_score
            }
            for m in sorted(self.models.values(), key=lambda x: x.size_gb)
        ]


# ============================================================================
# MODEL ROUTER
# ============================================================================
class ModelRouter:
    """
    Intelligent model routing system.
    
    Flow:
    1. User query comes in
    2. Fast classifier determines intent
    3. Router selects best model for that intent
    4. If model not loaded, hot-swap to it
    5. Execute query on selected model
    """
    
    def __init__(self):
        self.registry = ModelRegistry()
        self.classifier = IntentClassifier()
        self.current_worker_model: Optional[str] = None
        self.worker_process: Optional[subprocess.Popen] = None
        self.worker_port = WORKER_PORT
        self.worker_url = f"http://127.0.0.1:{self.worker_port}/v1/chat/completions"
        
        # Performance tracking
        self.route_history: List[Dict] = []
        self.model_switch_count = 0
        
        # Config
        self.config = self._load_config()
    
    def _load_config(self) -> Dict:
        """Load router configuration."""
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE) as f:
                    return json.load(f)
            except:
                pass
        
        return {
            "auto_switch": True,
            "min_switch_interval_seconds": 30,
            "max_model_size_gb": 20,
            "prefer_quality_over_speed": True,
            "classifier_model": None,  # Auto-select smallest
            "last_switch": None
        }
    
    def _save_config(self):
        """Save router configuration."""
        with open(CONFIG_FILE, 'w') as f:
            json.dump(self.config, f, indent=2)
    
    async def initialize(self) -> bool:
        """Initialize the router with classifier model."""
        # Find smallest model for classifier
        fastest = self.registry.get_fastest_model()
        if not fastest:
            logger.error("[Router] No models found!")
            return False
        
        classifier_model = self.config.get("classifier_model") or fastest.path
        
        # Start classifier
        success = await self.classifier.start(classifier_model)
        if not success:
            logger.warning("[Router] Classifier failed, will use keyword fallback")
        
        logger.info("[Router] Initialized")
        return True
    
    async def _ensure_worker_model(self, model_path: str) -> bool:
        """Ensure the worker model is loaded."""
        if self.current_worker_model == model_path:
            return True
        
        # Check switch interval
        last_switch = self.config.get("last_switch")
        if last_switch:
            elapsed = (datetime.now() - datetime.fromisoformat(last_switch)).total_seconds()
            min_interval = self.config.get("min_switch_interval_seconds", 30)
            if elapsed < min_interval:
                logger.info(f"[Router] Skipping switch, last switch was {elapsed:.0f}s ago")
                return self.current_worker_model is not None
        
        # Stop existing worker
        if self.worker_process:
            logger.info(f"[Router] Stopping current model: {Path(self.current_worker_model).stem if self.current_worker_model else 'none'}")
            self.worker_process.terminate()
            try:
                self.worker_process.wait(timeout=5)
            except:
                self.worker_process.kill()
            await asyncio.sleep(1)
        
        # Start new worker
        logger.info(f"[Router] Loading model: {Path(model_path).stem}")
        self.worker_process = subprocess.Popen(
            [str(LLAMA_SERVER),
             "--model", model_path,
             "--ctx-size", "4096",
             "--port", str(self.worker_port),
             "--threads", "8"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        
        # Wait for ready
        async with httpx.AsyncClient() as client:
            for _ in range(60):
                try:
                    resp = await client.get(f"http://127.0.0.1:{self.worker_port}/health", timeout=1)
                    if resp.status_code == 200:
                        self.current_worker_model = model_path
                        self.model_switch_count += 1
                        self.config["last_switch"] = datetime.now().isoformat()
                        self._save_config()
                        logger.info(f"[Router] Model ready: {Path(model_path).stem}")
                        return True
                except:
                    pass
                await asyncio.sleep(1)
        
        logger.error(f"[Router] Failed to load model: {model_path}")
        return False
    
    async def route_and_execute(self, query: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        """
        Route query to best model and execute.
        
        Returns:
            {
                "response": str,
                "model_used": str,
                "task_type": str,
                "classification_time_ms": float,
                "inference_time_ms": float,
                "model_switched": bool
            }
        """
        start_time = time.time()
        result = {
            "response": "",
            "model_used": "",
            "task_type": "",
            "classification_time_ms": 0,
            "inference_time_ms": 0,
            "model_switched": False
        }
        
        # Step 1: Classify intent
        classify_start = time.time()
        task_type, confidence = await self.classifier.classify(query)
        result["classification_time_ms"] = (time.time() - classify_start) * 1000
        result["task_type"] = task_type.value
        
        # Step 2: Get best model for task
        max_size = self.config.get("max_model_size_gb")
        best_model = self.registry.get_best_for_task(task_type, max_size)
        
        if not best_model:
            result["response"] = "Error: No suitable model found"
            return result
        
        result["model_used"] = best_model.name
        
        # Step 3: Ensure model is loaded
        if self.config.get("auto_switch", True):
            old_model = self.current_worker_model
            await self._ensure_worker_model(best_model.path)
            result["model_switched"] = (old_model != self.current_worker_model)
        elif not self.current_worker_model:
            # Load default model if none loaded
            await self._ensure_worker_model(best_model.path)
        
        # Step 4: Execute query
        inference_start = time.time()
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": query})
        
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    self.worker_url,
                    json={
                        "messages": messages,
                        "max_tokens": 2048,
                        "temperature": 0.7,
                        "stream": False
                    },
                    timeout=120
                )
                
                if resp.status_code == 200:
                    data = resp.json()
                    result["response"] = data["choices"][0]["message"]["content"]
                else:
                    result["response"] = f"Error: API returned {resp.status_code}"
                    
        except Exception as e:
            result["response"] = f"Error: {str(e)}"
        
        result["inference_time_ms"] = (time.time() - inference_start) * 1000
        
        # Log routing decision
        self.route_history.append({
            "timestamp": datetime.now().isoformat(),
            "query_preview": query[:100],
            "task": task_type.value,
            "model": best_model.name,
            "switched": result["model_switched"]
        })
        
        # Keep history bounded
        if len(self.route_history) > 100:
            self.route_history = self.route_history[-100:]
        
        total_time = (time.time() - start_time) * 1000
        logger.info(f"[Router] Complete: {task_type.value} -> {best_model.name} "
                   f"(classify: {result['classification_time_ms']:.0f}ms, "
                   f"inference: {result['inference_time_ms']:.0f}ms, "
                   f"total: {total_time:.0f}ms)")
        
        return result
    
    async def stream_butler_master(self, query: str, system_prompt: Optional[str] = None):
        """
        Two-stage Butler/Master streaming flow.
        1. Butler (Fast) acknowledges and classifies.
        2. Master (Robust) elaborates.
        """
        # --- STAGE 1: BUTLER ---
        # Get Butler's quick take and classification
        task_type, butler_take = await self.classifier.classify_and_take(query)
        
        # Yield Butler's take immediately
        yield f"**{EMOJI.get('butler', '🤵')} Butler**: {butler_take}\n\n"
        yield "---\n\n" # Visual separator
        
        # --- STAGE 2: MASTER ---
        # Select and ensure Master model is loaded
        max_size = self.config.get("max_model_size_gb")
        best_model = self.registry.get_best_for_task(task_type, max_size)
        
        if not best_model:
            yield f"*{EMOJI.get('error', '❌')} Master unavailable for this task.*"
            return
            
        if self.config.get("auto_switch", True):
            await self._ensure_worker_model(best_model.path)
            
        yield f"**{EMOJI.get('thinking', '🧠')} {task_type.value.replace('_', ' ').title()} ({best_model.name})**:\n\n"
        
        # Stream Master's deep response
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": query})
        
        try:
            async with httpx.AsyncClient() as client:
                async with client.stream(
                    "POST",
                    self.worker_url,
                    json={
                        "messages": messages,
                        "max_tokens": 4096,
                        "temperature": 0.7,
                        "stream": True
                    },
                    timeout=180
                ) as resp:
                    async for line in resp.aiter_lines():
                        if line.startswith("data: "):
                            data = line[6:]
                            if data == "[DONE]": break
                            try:
                                chunk = json.loads(data)
                                content = chunk["choices"][0]["delta"].get("content", "")
                                if content: yield content
                            except: pass
        except Exception as e:
            yield f"\n\n*Master Error: {str(e)}*"

    async def rerank_chunks(self, query: str, chunks: List[Dict], top_n: int = 5) -> List[Dict]:
        """
        Use the fast Butler LLM to re-rank chunks for high precision.
        Returns the top_n most relevant chunks.
        """
        if not chunks:
            return []
            
        logger.info(f"[Butler] Re-ranking {len(chunks)} chunks...")
        scored_chunks = []
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            tasks = []
            for chunk in chunks:
                # Prepare a rapid evaluation prompt
                prompt = (
                    f"Critique the following text chunk for its relevance to the user's query.\n"
                    f"Query: {query}\n"
                    f"Chunk: {chunk['text'][:500]}...\n\n"
                    f"Return ONLY a JSON object with a 'relevance' score (0.0 to 1.0) and a brief 'reason'.\n"
                    f"Example: {{\"relevance\": 0.95, \"reason\": \"Contains exact version number\"}}"
                )
                
                tasks.append(client.post(
                    self.classifier.api_url,
                    json={
                        "model": self.classifier.model_path,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.1,
                        "max_tokens": 100
                    }
                ))
            
            # Run evaluations in parallel
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            
            for i, resp in enumerate(responses):
                if isinstance(resp, Exception):
                    logger.error(f"[Reranker] Evaluation failed: {resp}")
                    continue
                    
                if resp.status_code == 200:
                    try:
                        content = resp.json()["choices"][0]["message"]["content"]
                        # Clean potential markdown from output
                        clean_content = re.sub(r'```json\n?|\n?```', '', content).strip()
                        data = json.loads(clean_content)
                        score = float(data.get("relevance", 0.0))
                        
                        chunk_copy = chunks[i].copy()
                        chunk_copy["rerank_score"] = score
                        chunk_copy["rerank_reason"] = data.get("reason", "")
                        scored_chunks.append(chunk_copy)
                    except Exception as e:
                        logger.warning(f"[Reranker] Failed to parse output for chunk {i}: {e}")
                        # Fallback to neutral score
                        chunk_copy = chunks[i].copy()
                        chunk_copy["rerank_score"] = 0.5
                        scored_chunks.append(chunk_copy)
                else:
                    logger.warning(f"[Reranker] API Error {resp.status_code}")
        
        # Sort by score and take top_n
        scored_chunks.sort(key=lambda x: x.get("rerank_score", 0.0), reverse=True)
        results = scored_chunks[:top_n]
        
        logger.info(f"[Reranker] Kept {len(results)}/{len(chunks)} chunks. High score: {results[0]['rerank_score'] if results else 0}")
        return results

    async def expand_query(self, query: str) -> List[str]:
        """
        Use the fast Butler LLM to generate semantic variations of the query.
        Helps improve recall by covering different ways to ask the same thing.
        """
        safe_print(f"🤵 [Butler] Expanding query: {query}")
        variations = [query] # Always include the original
        
        async with httpx.AsyncClient(timeout=15.0) as client:
            prompt = (
                f"Generate 3 diverse semantic variations of the following user query for a search engine.\n"
                f"Query: {query}\n\n"
                f"Return ONLY a JSON list of strings.\n"
                f"Example: [\"variation 1\", \"variation 2\", \"variation 3\"]"
            )
            
            try:
                resp = await client.post(
                    self.classifier.api_url,
                    json={
                        "model": self.classifier.model_path,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.4,
                        "max_tokens": 150
                    }
                )
                
                if resp.status_code == 200:
                    content = resp.json()["choices"][0]["message"]["content"]
                    # Clean potential markdown
                    clean_content = re.sub(r'```json\n?|\n?```', '', content).strip()
                    new_variations = json.loads(clean_content)
                    if isinstance(new_variations, list):
                        variations.extend([v for v in new_variations if v.lower() != query.lower()])
            except Exception as e:
                logger.warning(f"[Expansion] Failed to expand query: {e}")
        
        logger.info(f"[Expansion] Integrated {len(variations)} variations.")
        return list(set(variations)) # Deduplicate

    async def precise_rag_search(self, query: str, rag_system, k: int = 5, 
                             alpha: float = 0.6, expand: bool = True) -> List[Dict]:
        """
        Orchestrate the full 'Precise RAG' flow.
        """
        # 1. Expand
        queries = [query]
        if expand:
            queries = await self.expand_query(query)
        
        # 2. Retrieve (Multi-query Hybrid Search)
        all_chunks = {}
        for q in queries:
            # We search more (k*3) per query to ensure high recall for rerank
            search_k = max(k * 3, 10)
            chunks = rag_system.hybrid_search(q, k=search_k, alpha=alpha)
            for c in chunks:
                # Deduplicate by text/url
                chunk_id = f"{c.get('url')}_{c.get('text')[:50]}"
                if chunk_id not in all_chunks:
                    all_chunks[chunk_id] = c
        
        # 3. Rerank
        raw_chunks = list(all_chunks.values())
        if len(raw_chunks) > k:
            precise_chunks = await self.rerank_chunks(query, raw_chunks, top_n=k)
        else:
            precise_chunks = sorted(raw_chunks, key=lambda x: x.get('fusion_score', 0), reverse=True)
            
        return precise_chunks[:k]
    
    async def classify_intent(self, query: str) -> TaskType:
        """Classify query intent. Returns TaskType."""
        task_type, _ = await self.classifier.classify(query)
        return task_type
    
    def select_model(self, task_type: TaskType) -> str:
        """Select best model for task type. Returns model path."""
        max_size = self.config.get("max_model_size_gb")
        best_model = self.registry.get_best_for_task(task_type, max_size)
        return best_model.path if best_model else ""
    
    def get_stats(self) -> Dict[str, Any]:
        """Get router statistics."""
        return {
            "total_models": len(self.registry.models),
            "current_model": Path(self.current_worker_model).stem if self.current_worker_model else None,
            "model_switches": self.model_switch_count,
            "recent_routes": self.route_history[-10:],
            "task_distribution": self._get_task_distribution()
        }
    
    def _get_task_distribution(self) -> Dict[str, int]:
        """Get distribution of tasks routed."""
        dist = {}
        for route in self.route_history:
            task = route.get("task", "unknown")
            dist[task] = dist.get(task, 0) + 1
        return dist
    
    def shutdown(self):
        """Clean shutdown."""
        self.classifier.stop()
        if self.worker_process:
            self.worker_process.terminate()
            self.worker_process = None
        logger.info("[Router] Shutdown complete")


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================
_router: Optional[ModelRouter] = None

async def get_router() -> ModelRouter:
    """Get or create the global router instance."""
    global _router
    if _router is None:
        _router = ModelRouter()
        await _router.initialize()
    return _router

async def smart_query(query: str, system_prompt: Optional[str] = None) -> str:
    """Simple interface for smart model routing."""
    router = await get_router()
    result = await router.route_and_execute(query, system_prompt)
    return result["response"]


# ============================================================================
# CLI
# ============================================================================
async def interactive_mode():
    """Interactive testing mode."""
    router = ModelRouter()
    await router.initialize()
    
    safe_print("\n🤖 Smart Model Router - Interactive Mode")
    safe_print("=" * 50)
    safe_print("Type your query. The router will automatically select the best model.")
    safe_print("Commands: /stats, /models, /quit\n")
    
    while True:
        try:
            query = input("\n> ").strip()
            
            if not query:
                continue
            
            if query == "/quit":
                break
            
            if query == "/stats":
                stats = router.get_stats()
                safe_print(f"\nCurrent Model: {stats['current_model']}")
                safe_print(f"Model Switches: {stats['model_switches']}")
                safe_print(f"Task Distribution: {stats['task_distribution']}")
                continue
            
            if query == "/models":
                for m in router.registry.list_models():
                    safe_print(f"  {m['name'][:40]:40} {m['size_gb']:6.2f}GB  Q:{m['quality']:3.0f}  {m['tasks']}")
                continue
            
            result = await router.route_and_execute(query)
            
            safe_print(f"\n[{result['task_type']} → {result['model_used']}]")
            if result['model_switched']:
                safe_print("[Model switched]")
            safe_print(f"\n{result['response']}")
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            safe_print(f"Error: {e}")
    
    router.shutdown()
    safe_print("\nGoodbye!")


if __name__ == "__main__":
    asyncio.run(interactive_mode())
