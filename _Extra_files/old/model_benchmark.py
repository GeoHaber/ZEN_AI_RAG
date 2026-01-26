# -*- coding: utf-8 -*-
"""
model_benchmark.py - LLM Model Benchmark & Task Router
Measures speed, quality, and recommends models for specific tasks.
"""
import time
import json
import asyncio
import logging
import subprocess
import httpx
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, List, Any
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("ModelBenchmark")

# ============================================================================
# CONFIGURATION
# ============================================================================
MODELS_DIR = Path("C:/AI/Models")
LLAMA_SERVER = Path("C:/AI/_bin/llama-server.exe")
API_URL = "http://127.0.0.1:8001/v1/chat/completions"
BENCHMARK_PORT = 8099  # Use different port for benchmarks to not interfere

# Benchmark test prompts for different categories
BENCHMARK_PROMPTS = {
    "code_generation": {
        "prompt": "Write a Python function that implements binary search on a sorted list. Include type hints and docstring.",
        "max_tokens": 300,
        "expected_keywords": ["def", "binary", "mid", "return", "left", "right"],
        "quality_weight": 0.7  # Quality matters more for code
    },
    "code_explanation": {
        "prompt": "Explain what this code does: `sorted(set(x for x in lst if x > 0), reverse=True)[:5]`",
        "max_tokens": 150,
        "expected_keywords": ["filter", "positive", "unique", "sort", "descending", "first"],
        "quality_weight": 0.6
    },
    "general_qa": {
        "prompt": "What are the main differences between Python lists and tuples? Give 3 key points.",
        "max_tokens": 200,
        "expected_keywords": ["mutable", "immutable", "brackets", "parentheses", "performance"],
        "quality_weight": 0.5
    },
    "summarization": {
        "prompt": "Summarize the benefits of using async/await in Python in 2-3 sentences.",
        "max_tokens": 100,
        "expected_keywords": ["concurrent", "non-blocking", "I/O", "performance", "await"],
        "quality_weight": 0.5
    },
    "creative": {
        "prompt": "Write a haiku about programming bugs.",
        "max_tokens": 50,
        "expected_keywords": [],  # Creative - no keyword check
        "quality_weight": 0.3  # Speed matters more for creative
    },
    "reasoning": {
        "prompt": "If a train leaves station A at 9am traveling 60mph, and another train leaves station B (120 miles away) at 10am traveling 80mph toward A, when do they meet?",
        "max_tokens": 200,
        "expected_keywords": ["11", "hour", "miles", "meet"],
        "quality_weight": 0.8  # Quality critical for reasoning
    },
    "extraction": {
        "prompt": "Extract the email addresses from this text: 'Contact john@example.com or support@company.org for help. Old address: test@old.net'",
        "max_tokens": 50,
        "expected_keywords": ["john@example.com", "support@company.org", "test@old.net"],
        "quality_weight": 0.9  # Accuracy critical
    }
}

# ============================================================================
# DATA CLASSES
# ============================================================================
@dataclass
class BenchmarkResult:
    """Result of a single benchmark run."""
    model_name: str
    task: str
    prompt: str
    response: str
    time_to_first_token: float  # ms
    total_time: float  # ms
    tokens_generated: int
    tokens_per_second: float
    quality_score: float  # 0-100
    overall_score: float  # Weighted combination
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    error: Optional[str] = None

@dataclass
class ModelProfile:
    """Complete profile of a model's capabilities."""
    model_name: str
    file_path: str
    size_gb: float
    benchmarks: Dict[str, BenchmarkResult] = field(default_factory=dict)
    avg_tokens_per_second: float = 0.0
    avg_quality_score: float = 0.0
    recommended_tasks: List[str] = field(default_factory=list)
    load_time: float = 0.0  # seconds to load model
    
    def to_dict(self) -> dict:
        """Convert to serializable dict."""
        return {
            "model_name": self.model_name,
            "file_path": self.file_path,
            "size_gb": self.size_gb,
            "avg_tokens_per_second": self.avg_tokens_per_second,
            "avg_quality_score": self.avg_quality_score,
            "recommended_tasks": self.recommended_tasks,
            "load_time": self.load_time,
            "benchmarks": {k: asdict(v) for k, v in self.benchmarks.items()}
        }


# ============================================================================
# BENCHMARK ENGINE
# ============================================================================
class ModelBenchmarker:
    """
    Benchmark LLM models for speed and quality.
    
    Features:
    - Measures time-to-first-token (TTFT)
    - Measures tokens/second throughput
    - Scores quality based on expected keywords/patterns
    - Generates task recommendations
    """
    
    def __init__(self, models_dir: Path = MODELS_DIR, 
                 llama_server: Path = LLAMA_SERVER,
                 port: int = BENCHMARK_PORT):
        self.models_dir = models_dir
        self.llama_server = llama_server
        self.port = port
        self.api_url = f"http://127.0.0.1:{port}/v1/chat/completions"
        self.results_file = Path("benchmark_results.json")
        self.profiles: Dict[str, ModelProfile] = {}
        self.server_process: Optional[subprocess.Popen] = None
        
        # Load existing results
        self._load_results()
    
    def _load_results(self):
        """Load previous benchmark results."""
        if self.results_file.exists():
            try:
                with open(self.results_file, 'r') as f:
                    data = json.load(f)
                    # Reconstruct profiles (simplified - just load raw data)
                    self.profiles = data.get("profiles", {})
                    logger.info(f"Loaded {len(self.profiles)} cached model profiles")
            except Exception as e:
                logger.warning(f"Could not load cached results: {e}")
    
    def _save_results(self):
        """Save benchmark results to disk."""
        data = {
            "last_updated": datetime.now().isoformat(),
            "profiles": {k: v.to_dict() if isinstance(v, ModelProfile) else v 
                        for k, v in self.profiles.items()}
        }
        with open(self.results_file, 'w') as f:
            json.dump(data, f, indent=2)
        logger.info(f"Saved benchmark results to {self.results_file}")
    
    def discover_models(self) -> List[Dict[str, Any]]:
        """Find all GGUF models in the models directory."""
        models = []
        for f in self.models_dir.glob("*.gguf"):
            size_gb = f.stat().st_size / (1024**3)
            models.append({
                "name": f.stem,
                "path": str(f),
                "size_gb": round(size_gb, 2)
            })
        models.sort(key=lambda x: x["size_gb"])
        logger.info(f"Discovered {len(models)} models")
        return models
    
    async def _start_server(self, model_path: str, ctx_size: int = 4096) -> float:
        """Start llama-server with specified model. Returns load time."""
        # Kill existing server on benchmark port
        self._stop_server()
        await asyncio.sleep(1)
        
        logger.info(f"Starting server with model: {Path(model_path).name}")
        start_time = time.time()
        
        self.server_process = subprocess.Popen(
            [str(self.llama_server), 
             "--model", model_path,
             "--ctx-size", str(ctx_size),
             "--port", str(self.port),
             "--threads", "8"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        
        # Wait for server to be ready
        async with httpx.AsyncClient() as client:
            for attempt in range(60):  # 60 second timeout
                try:
                    resp = await client.get(f"http://127.0.0.1:{self.port}/health", timeout=1)
                    if resp.status_code == 200:
                        load_time = time.time() - start_time
                        logger.info(f"Server ready in {load_time:.2f}s")
                        return load_time
                except:
                    pass
                await asyncio.sleep(1)
        
        raise RuntimeError("Server failed to start within 60 seconds")
    
    def _stop_server(self):
        """Stop the benchmark server."""
        if self.server_process:
            self.server_process.terminate()
            try:
                self.server_process.wait(timeout=5)
            except:
                self.server_process.kill()
            self.server_process = None
    
    async def _run_prompt(self, prompt: str, max_tokens: int = 200) -> Dict[str, Any]:
        """Run a single prompt and measure timing."""
        messages = [{"role": "user", "content": prompt}]
        
        async with httpx.AsyncClient() as client:
            start_time = time.time()
            first_token_time = None
            full_response = ""
            token_count = 0
            
            async with client.stream(
                "POST",
                self.api_url,
                json={
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": 0.7,
                    "stream": True
                },
                timeout=120
            ) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data)
                            delta = chunk.get("choices", [{}])[0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                if first_token_time is None:
                                    first_token_time = time.time()
                                full_response += content
                                token_count += 1  # Approximate
                        except json.JSONDecodeError:
                            pass
            
            end_time = time.time()
            
            total_time = (end_time - start_time) * 1000  # ms
            ttft = (first_token_time - start_time) * 1000 if first_token_time else total_time
            tps = token_count / (end_time - start_time) if end_time > start_time else 0
            
            return {
                "response": full_response,
                "time_to_first_token": ttft,
                "total_time": total_time,
                "tokens_generated": token_count,
                "tokens_per_second": tps
            }
    
    def _score_quality(self, response: str, expected_keywords: List[str], 
                       quality_weight: float) -> float:
        """
        Score response quality based on keywords and basic heuristics.
        Returns 0-100 score.
        """
        score = 0
        response_lower = response.lower()
        
        # Keyword matching (50% of score)
        if expected_keywords:
            matches = sum(1 for kw in expected_keywords if kw.lower() in response_lower)
            keyword_score = (matches / len(expected_keywords)) * 50
        else:
            keyword_score = 25  # Neutral if no keywords expected
        
        score += keyword_score
        
        # Length appropriateness (20% of score)
        length = len(response)
        if 50 < length < 2000:
            score += 20
        elif 20 < length < 3000:
            score += 10
        
        # Coherence heuristics (30% of score)
        # - Starts with capital or code
        if response and (response[0].isupper() or response.startswith("```") or response.startswith("def ")):
            score += 10
        
        # - Has proper sentence structure
        if ". " in response or response.strip().endswith(".") or "```" in response:
            score += 10
        
        # - Not just repeating prompt
        if len(set(response.split())) > 10:
            score += 10
        
        return min(100, score)
    
    async def benchmark_model(self, model_path: str, model_name: str, 
                             size_gb: float, tasks: Optional[List[str]] = None) -> ModelProfile:
        """Run full benchmark suite on a model."""
        logger.info(f"\n{'='*60}")
        logger.info(f"BENCHMARKING: {model_name} ({size_gb} GB)")
        logger.info(f"{'='*60}")
        
        profile = ModelProfile(
            model_name=model_name,
            file_path=model_path,
            size_gb=size_gb
        )
        
        try:
            # Start server and measure load time
            profile.load_time = await self._start_server(model_path)
            
            # Run each benchmark task
            tasks_to_run = tasks or list(BENCHMARK_PROMPTS.keys())
            
            for task_name in tasks_to_run:
                if task_name not in BENCHMARK_PROMPTS:
                    continue
                    
                task = BENCHMARK_PROMPTS[task_name]
                logger.info(f"  Running task: {task_name}")
                
                try:
                    result = await self._run_prompt(task["prompt"], task["max_tokens"])
                    
                    quality = self._score_quality(
                        result["response"],
                        task["expected_keywords"],
                        task["quality_weight"]
                    )
                    
                    # Calculate overall score (weighted quality + speed)
                    # Speed score: tokens/sec normalized (assume 100 tps = perfect)
                    speed_score = min(100, result["tokens_per_second"] * 2)
                    overall = (quality * task["quality_weight"] + 
                              speed_score * (1 - task["quality_weight"]))
                    
                    benchmark = BenchmarkResult(
                        model_name=model_name,
                        task=task_name,
                        prompt=task["prompt"][:100] + "...",
                        response=result["response"][:500],
                        time_to_first_token=result["time_to_first_token"],
                        total_time=result["total_time"],
                        tokens_generated=result["tokens_generated"],
                        tokens_per_second=result["tokens_per_second"],
                        quality_score=quality,
                        overall_score=overall
                    )
                    profile.benchmarks[task_name] = benchmark
                    
                    logger.info(f"    TTFT: {result['time_to_first_token']:.0f}ms | "
                               f"TPS: {result['tokens_per_second']:.1f} | "
                               f"Quality: {quality:.0f} | Overall: {overall:.0f}")
                    
                except Exception as e:
                    logger.error(f"    Task failed: {e}")
                    profile.benchmarks[task_name] = BenchmarkResult(
                        model_name=model_name,
                        task=task_name,
                        prompt=task["prompt"][:100],
                        response="",
                        time_to_first_token=0,
                        total_time=0,
                        tokens_generated=0,
                        tokens_per_second=0,
                        quality_score=0,
                        overall_score=0,
                        error=str(e)
                    )
            
            # Calculate averages
            valid_benchmarks = [b for b in profile.benchmarks.values() 
                               if isinstance(b, BenchmarkResult) and not b.error]
            if valid_benchmarks:
                profile.avg_tokens_per_second = sum(b.tokens_per_second for b in valid_benchmarks) / len(valid_benchmarks)
                profile.avg_quality_score = sum(b.quality_score for b in valid_benchmarks) / len(valid_benchmarks)
            
            # Determine recommended tasks
            profile.recommended_tasks = self._get_recommendations(profile)
            
        finally:
            self._stop_server()
        
        # Save profile
        self.profiles[model_name] = profile
        self._save_results()
        
        return profile
    
    def _get_recommendations(self, profile: ModelProfile) -> List[str]:
        """Determine which tasks this model is best suited for."""
        recommendations = []
        
        for task_name, benchmark in profile.benchmarks.items():
            if isinstance(benchmark, BenchmarkResult) and not benchmark.error:
                # Recommend if overall score > 60
                if benchmark.overall_score >= 60:
                    recommendations.append(task_name)
        
        # Special recommendations based on model characteristics
        if profile.size_gb < 1:
            recommendations.append("quick_classification")
            recommendations.append("keyword_extraction")
        elif profile.size_gb > 6:
            recommendations.append("complex_reasoning")
            recommendations.append("long_form_writing")
        
        return list(set(recommendations))
    
    async def benchmark_all(self, skip_cached: bool = True) -> Dict[str, ModelProfile]:
        """Benchmark all discovered models."""
        models = self.discover_models()
        
        for model in models:
            if skip_cached and model["name"] in self.profiles:
                logger.info(f"Skipping {model['name']} (cached)")
                continue
            
            try:
                await self.benchmark_model(
                    model["path"],
                    model["name"],
                    model["size_gb"]
                )
            except Exception as e:
                logger.error(f"Failed to benchmark {model['name']}: {e}")
        
        return self.profiles
    
    def get_best_model_for_task(self, task: str) -> Optional[str]:
        """Get the best model for a specific task."""
        best_model = None
        best_score = 0
        
        for name, profile in self.profiles.items():
            if isinstance(profile, dict):
                benchmarks = profile.get("benchmarks", {})
                if task in benchmarks:
                    score = benchmarks[task].get("overall_score", 0)
                    if score > best_score:
                        best_score = score
                        best_model = name
            elif isinstance(profile, ModelProfile):
                if task in profile.benchmarks:
                    score = profile.benchmarks[task].overall_score
                    if score > best_score:
                        best_score = score
                        best_model = name
        
        return best_model
    
    def generate_report(self) -> str:
        """Generate a markdown report of all benchmarks."""
        lines = [
            "# 🚀 Model Benchmark Report",
            f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*\n",
            "## 📊 Model Comparison\n",
            "| Model | Size | Avg TPS | Avg Quality | Best For |",
            "|-------|------|---------|-------------|----------|"
        ]
        
        for name, profile in sorted(self.profiles.items(), 
                                    key=lambda x: x[1].get("size_gb", 0) if isinstance(x[1], dict) else x[1].size_gb):
            if isinstance(profile, dict):
                size = profile.get("size_gb", 0)
                tps = profile.get("avg_tokens_per_second", 0)
                quality = profile.get("avg_quality_score", 0)
                tasks = profile.get("recommended_tasks", [])[:3]
            else:
                size = profile.size_gb
                tps = profile.avg_tokens_per_second
                quality = profile.avg_quality_score
                tasks = profile.recommended_tasks[:3]
            
            tasks_str = ", ".join(tasks) if tasks else "General"
            lines.append(f"| {name[:30]} | {size:.1f}GB | {tps:.1f} | {quality:.0f}/100 | {tasks_str} |")
        
        lines.extend([
            "\n## 🎯 Task Router Recommendations\n",
            "| Task | Best Model | Score |",
            "|------|------------|-------|"
        ])
        
        for task in BENCHMARK_PROMPTS.keys():
            best = self.get_best_model_for_task(task)
            if best and best in self.profiles:
                profile = self.profiles[best]
                if isinstance(profile, dict):
                    score = profile.get("benchmarks", {}).get(task, {}).get("overall_score", 0)
                else:
                    score = profile.benchmarks.get(task, BenchmarkResult("", "", "", "", 0, 0, 0, 0, 0, 0)).overall_score
                lines.append(f"| {task} | {best[:25]} | {score:.0f} |")
        
        return "\n".join(lines)


# ============================================================================
# TASK ROUTER
# ============================================================================
class TaskRouter:
    """
    Intelligent task router that selects the best model for each task.
    Uses benchmark results to make decisions.
    """
    
    def __init__(self, benchmarker: ModelBenchmarker):
        self.benchmarker = benchmarker
        
        # Manual overrides for specific task types
        self.task_hints = {
            "code": ["code_generation", "code_explanation"],
            "python": ["code_generation"],
            "explain": ["code_explanation", "general_qa"],
            "summarize": ["summarization"],
            "creative": ["creative"],
            "math": ["reasoning"],
            "calculate": ["reasoning"],
            "extract": ["extraction"],
        }
    
    def classify_query(self, query: str) -> str:
        """Classify a user query into a task category."""
        query_lower = query.lower()
        
        # Check for task hints
        for hint, tasks in self.task_hints.items():
            if hint in query_lower:
                return tasks[0]  # Return primary task
        
        # Default classification
        if "?" in query:
            return "general_qa"
        elif len(query) > 200:
            return "summarization"
        else:
            return "general_qa"
    
    def route(self, query: str) -> Dict[str, Any]:
        """
        Route a query to the best model.
        
        Returns:
            {
                "task": str,
                "model": str,
                "confidence": float,
                "fallback": str
            }
        """
        task = self.classify_query(query)
        best_model = self.benchmarker.get_best_model_for_task(task)
        
        # Get fallback (fastest model)
        fallback = None
        fastest_tps = 0
        for name, profile in self.benchmarker.profiles.items():
            if isinstance(profile, dict):
                tps = profile.get("avg_tokens_per_second", 0)
            else:
                tps = profile.avg_tokens_per_second
            if tps > fastest_tps:
                fastest_tps = tps
                fallback = name
        
        return {
            "task": task,
            "model": best_model or fallback,
            "confidence": 0.8 if best_model else 0.5,
            "fallback": fallback
        }


# ============================================================================
# CLI
# ============================================================================
async def main():
    """Run benchmarks from command line."""
    import argparse
    
    parser = argparse.ArgumentParser(description="LLM Model Benchmarker")
    parser.add_argument("--all", action="store_true", help="Benchmark all models")
    parser.add_argument("--model", type=str, help="Benchmark specific model (name or path)")
    parser.add_argument("--report", action="store_true", help="Generate report from cached results")
    parser.add_argument("--task", type=str, help="Get best model for task")
    parser.add_argument("--fresh", action="store_true", help="Ignore cached results")
    
    args = parser.parse_args()
    
    benchmarker = ModelBenchmarker()
    
    if args.report:
        print(benchmarker.generate_report())
        return
    
    if args.task:
        best = benchmarker.get_best_model_for_task(args.task)
        print(f"Best model for '{args.task}': {best}")
        return
    
    if args.model:
        # Find model
        models = benchmarker.discover_models()
        match = next((m for m in models if args.model.lower() in m["name"].lower()), None)
        if match:
            await benchmarker.benchmark_model(match["path"], match["name"], match["size_gb"])
        else:
            print(f"Model not found: {args.model}")
            print("Available models:", [m["name"] for m in models])
        return
    
    if args.all:
        await benchmarker.benchmark_all(skip_cached=not args.fresh)
        print(benchmarker.generate_report())
        return
    
    # Interactive mode
    print("LLM Model Benchmarker")
    print("=" * 40)
    print("Commands:")
    print("  --all        Benchmark all models")
    print("  --model X    Benchmark specific model")
    print("  --report     Show benchmark report")
    print("  --task X     Get best model for task")
    print("\nAvailable models:")
    for m in benchmarker.discover_models():
        print(f"  - {m['name']} ({m['size_gb']} GB)")


if __name__ == "__main__":
    asyncio.run(main())
