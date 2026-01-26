# -*- coding: utf-8 -*-
"""
model_discovery.py - Intelligent Model Discovery & Recommendation System

This system acts as an AI advisor that:
1. Monitors HuggingFace for trending/new GGUF models
2. Analyzes them against your current model arsenal
3. Identifies capability gaps and potential upgrades  
4. Presents a compelling case to YOU before downloading
5. Only downloads after explicit user approval

The goal: Keep ZenAI AI equipped with the BEST tools for every task.
"""
import json
import asyncio
import logging
import subprocess
import time
import httpx
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, List, Any, Tuple
from datetime import datetime, timedelta
from enum import Enum

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("ModelDiscovery")

# ============================================================================
# CONFIGURATION  
# ============================================================================
MODELS_DIR = Path("C:/AI/Models")
DISCOVERY_CACHE = Path("model_discovery_cache.json")
PENDING_RECOMMENDATIONS = Path("pending_recommendations.json")
HF_API_BASE = "https://huggingface.co/api"

# Capability categories we track
CAPABILITY_CATEGORIES = [
    "code_generation", "reasoning", "math", "general_chat", 
    "creative_writing", "summarization", "function_calling", 
    "multilingual", "long_context", "fast_inference"
]

# Quality indicators by model family
MODEL_FAMILY_PROFILES = {
    "qwen": {"quality": 0.88, "strengths": ["code_generation", "reasoning", "multilingual"], "speed": "medium"},
    "deepseek": {"quality": 0.92, "strengths": ["code_generation", "reasoning", "math"], "speed": "medium"},
    "mistral": {"quality": 0.87, "strengths": ["function_calling", "general_chat", "fast_inference"], "speed": "fast"},
    "llama": {"quality": 0.82, "strengths": ["general_chat", "creative_writing"], "speed": "fast"},
    "phi": {"quality": 0.80, "strengths": ["reasoning", "math", "fast_inference"], "speed": "very_fast"},
    "gemma": {"quality": 0.83, "strengths": ["general_chat", "summarization"], "speed": "medium"},
    "glm": {"quality": 0.88, "strengths": ["reasoning", "code_generation", "multilingual"], "speed": "medium"},
    "yi": {"quality": 0.82, "strengths": ["multilingual", "long_context"], "speed": "medium"},
    "codestral": {"quality": 0.89, "strengths": ["code_generation"], "speed": "medium"},
    "starcoder": {"quality": 0.84, "strengths": ["code_generation"], "speed": "fast"},
    "command": {"quality": 0.85, "strengths": ["function_calling", "reasoning"], "speed": "medium"},
    "granite": {"quality": 0.82, "strengths": ["code_generation", "reasoning"], "speed": "fast"},
}

# Curated list of high-quality GGUF models to track
TRACKED_MODELS = {
    # Coding specialists
    "qwen2.5-coder-7b": {
        "repo": "bartowski/Qwen2.5-Coder-7B-Instruct-GGUF",
        "file": "Qwen2.5-Coder-7B-Instruct-Q4_K_M.gguf",
        "category": "code",
        "size_gb": 4.4,
        "priority": "high"
    },
    "qwen2.5-coder-14b": {
        "repo": "bartowski/Qwen2.5-Coder-14B-Instruct-GGUF",
        "file": "Qwen2.5-Coder-14B-Instruct-Q4_K_M.gguf",
        "category": "code",
        "size_gb": 8.5,
        "priority": "high"
    },
    "qwen2.5-coder-32b": {
        "repo": "bartowski/Qwen2.5-Coder-32B-Instruct-GGUF",
        "file": "Qwen2.5-Coder-32B-Instruct-Q4_K_M.gguf",
        "category": "code",
        "size_gb": 18,
        "priority": "optional"
    },
    
    # Reasoning specialists
    "deepseek-r1-distill-14b": {
        "repo": "unsloth/DeepSeek-R1-Distill-Qwen-14B-GGUF",
        "file": "DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf",
        "category": "reasoning",
        "size_gb": 8.5,
        "priority": "high"
    },
    "deepseek-r1-distill-32b": {
        "repo": "unsloth/DeepSeek-R1-Distill-Qwen-32B-GGUF",
        "file": "DeepSeek-R1-Distill-Qwen-32B-Q4_K_M.gguf",
        "category": "reasoning",
        "size_gb": 18,
        "priority": "optional"
    },
    
    # General powerhouses
    "glm-4.7-flash": {
        "repo": "unsloth/GLM-4.7-Flash-GGUF",
        "file": "GLM-4.7-Flash-Q4_K_M.gguf",
        "category": "general",
        "size_gb": 17,
        "priority": "high"
    },
    "mistral-small-24b": {
        "repo": "unsloth/Mistral-Small-24B-Instruct-2501-GGUF",
        "file": "Mistral-Small-24B-Instruct-2501-Q4_K_M.gguf",
        "category": "general",
        "size_gb": 14,
        "priority": "high"
    },
    "qwen2.5-14b": {
        "repo": "bartowski/Qwen2.5-14B-Instruct-GGUF",
        "file": "Qwen2.5-14B-Instruct-Q4_K_M.gguf",
        "category": "general",
        "size_gb": 8.5,
        "priority": "medium"
    },
    
    # Fast models
    "mistral-7b": {
        "repo": "bartowski/Mistral-7B-Instruct-v0.3-GGUF",
        "file": "Mistral-7B-Instruct-v0.3-Q4_K_M.gguf",
        "category": "fast",
        "size_gb": 4,
        "priority": "medium"
    },
    "phi-3.5-mini": {
        "repo": "bartowski/Phi-3.5-mini-instruct-GGUF",
        "file": "Phi-3.5-mini-instruct-Q4_K_M.gguf",
        "category": "fast",
        "size_gb": 2.2,
        "priority": "medium"
    },
    "llama-3.2-3b": {
        "repo": "bartowski/Llama-3.2-3B-Instruct-GGUF",
        "file": "Llama-3.2-3B-Instruct-Q4_K_M.gguf",
        "category": "fast",
        "size_gb": 1.9,
        "priority": "medium"
    },
    
    # Tiny models (for classification)
    "qwen2.5-0.5b": {
        "repo": "Qwen/Qwen2.5-0.5B-Instruct-GGUF",
        "file": "qwen2.5-0.5b-instruct-q5_k_m.gguf",
        "category": "tiny",
        "size_gb": 0.5,
        "priority": "high"
    },
    "smollm2-135m": {
        "repo": "bartowski/SmolLM2-135M-Instruct-GGUF",
        "file": "SmolLM2-135M-Instruct-Q4_K_M.gguf",
        "category": "tiny",
        "size_gb": 0.1,
        "priority": "high"
    },
    
    # New/Trending (update this list periodically)
    "gemma-2-9b": {
        "repo": "bartowski/gemma-2-9b-it-GGUF",
        "file": "gemma-2-9b-it-Q4_K_M.gguf",
        "category": "general",
        "size_gb": 5.4,
        "priority": "medium"
    },
}

# Minimum recommended models for each category
MINIMUM_ARSENAL = {
    "code": ["qwen2.5-coder-7b"],
    "reasoning": ["deepseek-r1-distill-14b"],
    "general": ["mistral-small-24b", "glm-4.7-flash"],
    "fast": ["mistral-7b", "phi-3.5-mini"],
    "tiny": ["qwen2.5-0.5b"]
}


# ============================================================================
# RECOMMENDATION STATUS
# ============================================================================
class RecommendationStatus(Enum):
    PENDING = "pending"          # Awaiting user decision
    APPROVED = "approved"        # User said yes, ready to download
    DOWNLOADING = "downloading"  # Currently downloading
    COMPLETED = "completed"      # Downloaded successfully
    REJECTED = "rejected"        # User said no
    DEFERRED = "deferred"        # User said "maybe later"


# ============================================================================
# DATA CLASSES
# ============================================================================
@dataclass
class ModelStatus:
    """Status of a tracked model."""
    name: str
    installed: bool
    local_path: Optional[str]
    size_gb: float
    category: str
    priority: str
    last_checked: Optional[str] = None
    benchmark_score: Optional[float] = None


@dataclass
class ModelCandidate:
    """A model discovered that might be worth downloading."""
    model_id: str           # HuggingFace repo ID
    display_name: str       # Human-friendly name
    size_gb: float
    downloads: int
    likes: int
    trending_score: float
    last_modified: str
    
    # Analysis results  
    estimated_quality: float = 0.0
    strengths: List[str] = field(default_factory=list)
    fills_gap: bool = False
    gap_description: str = ""
    is_upgrade: bool = False
    upgrades_from: Optional[str] = None
    
    # Recommendation
    score: float = 0.0
    case_summary: str = ""      # Brief summary
    case_detailed: str = ""     # Full reasoning
    status: str = "pending"
    
    # Metadata
    discovered_at: str = field(default_factory=lambda: datetime.now().isoformat())
    gguf_files: List[Dict] = field(default_factory=list)
    recommended_file: Optional[str] = None
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> "ModelCandidate":
        return cls(**data)


@dataclass
class ArsenalAnalysis:
    """Analysis of current model capabilities."""
    total_models: int = 0
    total_size_gb: float = 0.0
    capability_coverage: Dict[str, List[str]] = field(default_factory=dict)
    capability_gaps: List[str] = field(default_factory=list)
    strongest_areas: List[str] = field(default_factory=list)
    weakest_areas: List[str] = field(default_factory=list)
    size_distribution: Dict[str, int] = field(default_factory=dict)  # tiny/small/medium/large counts


# ============================================================================
# INTELLIGENT MODEL ADVISOR
# ============================================================================
class ModelAdvisor:
    """
    AI-like advisor that analyzes models and presents compelling cases.
    Think of it as your personal model scout.
    """
    
    def __init__(self, models_dir: Path = MODELS_DIR):
        self.models_dir = models_dir
        self.pending_file = PENDING_RECOMMENDATIONS
        self.pending: List[ModelCandidate] = []
        self._load_pending()
    
    def _load_pending(self):
        """Load pending recommendations."""
        if self.pending_file.exists():
            try:
                with open(self.pending_file, 'r') as f:
                    data = json.load(f)
                    self.pending = [ModelCandidate.from_dict(r) for r in data.get("recommendations", [])]
            except Exception as e:
                logger.warning(f"Could not load pending: {e}")
                self.pending = []
    
    def _save_pending(self):
        """Save pending recommendations."""
        data = {
            "last_updated": datetime.now().isoformat(),
            "recommendations": [r.to_dict() for r in self.pending]
        }
        with open(self.pending_file, 'w') as f:
            json.dump(data, f, indent=2, default=str)
    
    def analyze_arsenal(self) -> ArsenalAnalysis:
        """Deep analysis of current model capabilities."""
        analysis = ArsenalAnalysis()
        
        # Initialize capability buckets
        for cap in CAPABILITY_CATEGORIES:
            analysis.capability_coverage[cap] = []
        
        # Scan installed models
        installed = list(self.models_dir.glob("*.gguf"))
        analysis.total_models = len(installed)
        
        for model_file in installed:
            size_gb = model_file.stat().st_size / (1024**3)
            analysis.total_size_gb += size_gb
            name_lower = model_file.stem.lower()
            
            # Size distribution
            if size_gb < 1:
                analysis.size_distribution["tiny"] = analysis.size_distribution.get("tiny", 0) + 1
            elif size_gb < 5:
                analysis.size_distribution["small"] = analysis.size_distribution.get("small", 0) + 1
            elif size_gb < 12:
                analysis.size_distribution["medium"] = analysis.size_distribution.get("medium", 0) + 1
            else:
                analysis.size_distribution["large"] = analysis.size_distribution.get("large", 0) + 1
            
            # Match to family profiles
            for family, profile in MODEL_FAMILY_PROFILES.items():
                if family in name_lower:
                    for strength in profile["strengths"]:
                        if strength in analysis.capability_coverage:
                            analysis.capability_coverage[strength].append(model_file.stem)
                    break
            
            # Special pattern matching
            if "coder" in name_lower or "code" in name_lower:
                analysis.capability_coverage["code_generation"].append(model_file.stem)
            if "instruct" in name_lower:
                analysis.capability_coverage["function_calling"].append(model_file.stem)
        
        # Calculate gaps and strengths
        coverage_counts = {cap: len(models) for cap, models in analysis.capability_coverage.items()}
        sorted_caps = sorted(coverage_counts.items(), key=lambda x: x[1])
        
        # Weakest (0-1 models)
        analysis.capability_gaps = [cap for cap, count in sorted_caps if count <= 1]
        analysis.weakest_areas = [cap for cap, _ in sorted_caps[:3]]
        analysis.strongest_areas = [cap for cap, _ in sorted_caps[-3:]]
        
        return analysis
    
    async def discover_trending(self, limit: int = 50) -> List[Dict]:
        """Fetch trending GGUF models from HuggingFace."""
        async with httpx.AsyncClient() as client:
            try:
                # Multiple search strategies
                all_models = []
                
                # Strategy 1: Trending GGUF
                resp = await client.get(
                    f"{HF_API_BASE}/models",
                    params={"sort": "trending", "search": "gguf", "limit": limit},
                    timeout=30
                )
                if resp.status_code == 200:
                    all_models.extend(resp.json())
                
                # Strategy 2: Most downloaded GGUF
                resp = await client.get(
                    f"{HF_API_BASE}/models",
                    params={"sort": "downloads", "search": "gguf instruct", "limit": 30},
                    timeout=30
                )
                if resp.status_code == 200:
                    all_models.extend(resp.json())
                
                # Dedupe by ID
                seen = set()
                unique = []
                for m in all_models:
                    mid = m.get("id", "")
                    if mid not in seen and "gguf" in mid.lower():
                        seen.add(mid)
                        unique.append(m)
                
                logger.info(f"Found {len(unique)} GGUF models to analyze")
                return unique
                
            except Exception as e:
                logger.error(f"Failed to fetch models: {e}")
                return []
    
    async def get_model_files(self, model_id: str) -> List[Dict]:
        """Get available GGUF files for a model."""
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(
                    f"{HF_API_BASE}/models/{model_id}/tree/main",
                    timeout=15
                )
                if resp.status_code == 200:
                    files = resp.json()
                    gguf_files = []
                    for f in files:
                        path = f.get("path", "")
                        if path.endswith(".gguf"):
                            gguf_files.append({
                                "name": path,
                                "size_gb": round(f.get("size", 0) / (1024**3), 2)
                            })
                    return gguf_files
            except:
                pass
        return []
    
    def _analyze_candidate(self, model_data: Dict, gguf_files: List[Dict], arsenal: ArsenalAnalysis) -> ModelCandidate:
        """Analyze a model and build the recommendation case."""
        model_id = model_data.get("id", "")
        name = model_id.split("/")[-1] if "/" in model_id else model_id
        
        # Find best Q4_K_M file
        best_file = None
        for f in gguf_files:
            if "Q4_K_M" in f["name"]:
                best_file = f
                break
        if not best_file and gguf_files:
            # Prefer medium quantizations
            for f in gguf_files:
                if any(q in f["name"] for q in ["Q5_K_M", "Q4_K_S", "Q5_K_S"]):
                    best_file = f
                    break
            if not best_file:
                best_file = gguf_files[0]
        
        size_gb = best_file["size_gb"] if best_file else 0
        
        candidate = ModelCandidate(
            model_id=model_id,
            display_name=name.replace("-GGUF", "").replace("-gguf", ""),
            size_gb=size_gb,
            downloads=model_data.get("downloads", 0),
            likes=model_data.get("likes", 0),
            trending_score=model_data.get("trendingScore", 0),
            last_modified=model_data.get("lastModified", ""),
            gguf_files=gguf_files,
            recommended_file=best_file["name"] if best_file else None
        )
        
        # Identify model family and estimate quality
        name_lower = name.lower()
        for family, profile in MODEL_FAMILY_PROFILES.items():
            if family in name_lower:
                candidate.estimated_quality = profile["quality"]
                candidate.strengths = profile["strengths"].copy()
                break
        
        # Boost for specific patterns
        if "coder" in name_lower:
            if "code_generation" not in candidate.strengths:
                candidate.strengths.append("code_generation")
            candidate.estimated_quality = min(1.0, candidate.estimated_quality + 0.03)
        if "r1" in name_lower or "reasoning" in name_lower:
            if "reasoning" not in candidate.strengths:
                candidate.strengths.append("reasoning")
            candidate.estimated_quality = min(1.0, candidate.estimated_quality + 0.05)
        if "instruct" in name_lower:
            if "function_calling" not in candidate.strengths:
                candidate.strengths.append("function_calling")
        
        # Check if fills capability gaps
        for gap in arsenal.capability_gaps:
            if gap in candidate.strengths:
                candidate.fills_gap = True
                candidate.gap_description = f"Fills gap in '{gap.replace('_', ' ')}'"
                break
        
        # Check if it's an upgrade
        candidate.is_upgrade, candidate.upgrades_from = self._check_if_upgrade(name, arsenal)
        
        # Calculate recommendation score
        candidate.score = self._calculate_score(candidate, arsenal)
        
        # Build the case
        candidate.case_summary, candidate.case_detailed = self._build_case(candidate, arsenal)
        
        return candidate
    
    def _check_if_upgrade(self, new_name: str, arsenal: ArsenalAnalysis) -> Tuple[bool, Optional[str]]:
        """Check if this model is an upgrade from something we have."""
        import re
        new_lower = new_name.lower()
        
        # Get installed model names
        installed = [f.stem.lower() for f in self.models_dir.glob("*.gguf")]
        
        for family in MODEL_FAMILY_PROFILES.keys():
            if family in new_lower:
                # Extract parameter size from new model
                new_size = re.search(r'(\d+)b', new_lower)
                if not new_size:
                    continue
                new_params = int(new_size.group(1))
                
                # Find matching installed model
                for inst in installed:
                    if family in inst:
                        inst_size = re.search(r'(\d+)b', inst)
                        if inst_size:
                            inst_params = int(inst_size.group(1))
                            if new_params > inst_params:
                                return True, inst
        return False, None
    
    def _calculate_score(self, candidate: ModelCandidate, arsenal: ArsenalAnalysis) -> float:
        """Calculate recommendation score (0-100)."""
        score = 0.0
        
        # Quality factor (35 points max)
        score += candidate.estimated_quality * 35
        
        # Fills gap (30 points) - This is huge
        if candidate.fills_gap:
            score += 30
        
        # Is upgrade (15 points)
        if candidate.is_upgrade:
            score += 15
        
        # Popularity signal (10 points max)
        pop_score = min(10, (candidate.downloads / 100000) * 5 + (candidate.likes / 1000) * 5)
        score += pop_score
        
        # Trending bonus (10 points max)
        if candidate.trending_score > 0:
            score += min(10, candidate.trending_score * 3)
        
        # Size consideration - sweet spot is 5-15GB
        if 5 <= candidate.size_gb <= 15:
            score += 5
        elif candidate.size_gb > 25:
            score -= 10  # Penalty for very large
        
        # Recency bonus
        try:
            mod_date = datetime.fromisoformat(candidate.last_modified.replace("Z", "+00:00"))
            days_old = (datetime.now(mod_date.tzinfo) - mod_date).days
            if days_old < 30:
                score += 5
        except:
            pass
        
        return min(100, max(0, score))
    
    def _build_case(self, candidate: ModelCandidate, arsenal: ArsenalAnalysis) -> Tuple[str, str]:
        """Build a compelling case for why to download this model."""
        reasons = []
        detailed_lines = []
        
        # Opening
        detailed_lines.append(f"## 🤖 {candidate.display_name}")
        detailed_lines.append(f"**Score: {candidate.score:.0f}/100** | Size: {candidate.size_gb:.1f} GB")
        detailed_lines.append("")
        
        # The case
        detailed_lines.append("### Why you should consider this model:")
        detailed_lines.append("")
        
        if candidate.fills_gap:
            reasons.append(f"🎯 {candidate.gap_description}")
            detailed_lines.append("**1. Fills a Capability Gap**")
            gap_area = candidate.gap_description.split("'")[1] if "'" in candidate.gap_description else "this area"
            detailed_lines.append(f"   Your arsenal currently lacks strong coverage in '{gap_area}'.")
            detailed_lines.append("   This model specializes in that area.")
            detailed_lines.append("")
        
        if candidate.is_upgrade:
            reasons.append(f"⬆️ Upgrades {candidate.upgrades_from}")
            detailed_lines.append("**2. Direct Upgrade**")
            detailed_lines.append(f"   This is a larger/newer version of `{candidate.upgrades_from}` you already have.")
            detailed_lines.append("   Expect better quality with similar characteristics.")
            detailed_lines.append("")
        
        if candidate.estimated_quality >= 0.87:
            reasons.append("⭐ High-quality model family")
            detailed_lines.append(f"**3. Quality Pedigree**")
            detailed_lines.append(f"   This model comes from a highly-rated family with proven benchmark results.")
            detailed_lines.append("")
        
        if candidate.downloads > 50000:
            reasons.append(f"📥 {candidate.downloads:,} downloads")
            detailed_lines.append(f"**4. Community Validated**")
            detailed_lines.append(f"   With {candidate.downloads:,} downloads, this model has been battle-tested by the community.")
            detailed_lines.append("")
        
        if candidate.trending_score > 1:
            reasons.append("🔥 Currently trending")
            detailed_lines.append(f"**5. Trending Now**")
            detailed_lines.append(f"   This model is gaining rapid popularity - often indicates strong real-world performance.")
            detailed_lines.append("")
        
        if candidate.strengths:
            strengths_str = ", ".join(s.replace("_", " ") for s in candidate.strengths[:4])
            reasons.append(f"💪 {strengths_str}")
            detailed_lines.append(f"**Strengths:** {strengths_str}")
            detailed_lines.append("")
        
        # Size consideration
        detailed_lines.append("### Resource Consideration:")
        if candidate.size_gb < 5:
            detailed_lines.append(f"   ✅ Lightweight ({candidate.size_gb:.1f} GB) - Fast loading, low VRAM")
        elif candidate.size_gb < 12:
            detailed_lines.append(f"   ✅ Medium size ({candidate.size_gb:.1f} GB) - Good balance of quality and speed")
        else:
            detailed_lines.append(f"   ⚠️ Large model ({candidate.size_gb:.1f} GB) - Needs adequate VRAM but delivers best quality")
        
        # Build summary
        if not reasons:
            reasons.append("📊 General arsenal improvement")
        
        summary = " | ".join(reasons[:3])
        detailed = "\n".join(detailed_lines)
        
        return summary, detailed
    
    async def discover_and_analyze(self, force: bool = False) -> List[ModelCandidate]:
        """
        Main discovery workflow:
        1. Analyze current arsenal
        2. Fetch trending models
        3. Analyze each candidate
        4. Build recommendations with cases
        5. Save for user review
        """
        logger.info("🔍 Starting intelligent model discovery...")
        
        # Analyze what we have
        arsenal = self.analyze_arsenal()
        logger.info(f"Current arsenal: {arsenal.total_models} models, {arsenal.total_size_gb:.1f} GB")
        logger.info(f"Capability gaps: {arsenal.capability_gaps}")
        
        # Get already processed
        processed_ids = set()
        rejected_ids = set()
        try:
            if DISCOVERY_CACHE.exists():
                with open(DISCOVERY_CACHE) as f:
                    cache = json.load(f)
                    processed_ids = set(cache.get("processed_ids", []))
                    rejected_ids = set(cache.get("rejected_ids", []))
        except:
            pass
        
        # Fetch trending
        trending = await self.discover_trending(limit=60)
        if not trending:
            logger.warning("No models found to analyze")
            return []
        
        # Get installed model stems
        installed_stems = {f.stem.lower().replace("-", "").replace("_", "") 
                         for f in self.models_dir.glob("*.gguf")}
        
        candidates = []
        
        for model in trending:
            model_id = model.get("id", "")
            
            # Skip already processed/rejected
            if not force:
                if model_id in processed_ids or model_id in rejected_ids:
                    continue
            
            # Skip if already installed (fuzzy match)
            name_normalized = model_id.split("/")[-1].lower().replace("-", "").replace("_", "").replace("gguf", "")
            if any(name_normalized in inst or inst in name_normalized for inst in installed_stems):
                processed_ids.add(model_id)
                continue
            
            logger.info(f"Analyzing: {model_id}")
            
            # Get GGUF files
            gguf_files = await self.get_model_files(model_id)
            if not gguf_files:
                continue
            
            # Analyze and build case
            candidate = self._analyze_candidate(model, gguf_files, arsenal)
            
            # Only recommend if score is meaningful
            if candidate.score >= 45:
                candidates.append(candidate)
                logger.info(f"  ✓ Score: {candidate.score:.0f} - {candidate.case_summary}")
            
            processed_ids.add(model_id)
        
        # Save processed IDs
        try:
            cache = {"processed_ids": list(processed_ids), "rejected_ids": list(rejected_ids)}
            with open(DISCOVERY_CACHE, 'w') as f:
                json.dump(cache, f)
        except:
            pass
        
        # Sort by score
        candidates.sort(key=lambda x: x.score, reverse=True)
        
        # Add top candidates to pending (avoid duplicates)
        existing_ids = {p.model_id for p in self.pending}
        for c in candidates[:15]:
            if c.model_id not in existing_ids:
                self.pending.append(c)
        
        self._save_pending()
        
        return candidates[:10]
    
    def get_pending_for_review(self) -> List[ModelCandidate]:
        """Get models awaiting user decision."""
        return [r for r in self.pending if r.status == "pending"]
    
    def approve(self, model_id: str) -> Optional[ModelCandidate]:
        """User approves a recommendation."""
        for r in self.pending:
            if r.model_id == model_id:
                r.status = "approved"
                self._save_pending()
                return r
        return None
    
    def reject(self, model_id: str):
        """User rejects a recommendation."""
        for r in self.pending:
            if r.model_id == model_id:
                r.status = "rejected"
                self._save_pending()
                # Add to rejection cache
                try:
                    cache = {}
                    if DISCOVERY_CACHE.exists():
                        with open(DISCOVERY_CACHE) as f:
                            cache = json.load(f)
                    rejected = set(cache.get("rejected_ids", []))
                    rejected.add(model_id)
                    cache["rejected_ids"] = list(rejected)
                    with open(DISCOVERY_CACHE, 'w') as f:
                        json.dump(cache, f)
                except:
                    pass
                return
    
    def defer(self, model_id: str):
        """User defers decision (ask me later)."""
        for r in self.pending:
            if r.model_id == model_id:
                r.status = "deferred"
                self._save_pending()
                return
    
    def get_download_command(self, candidate: ModelCandidate) -> str:
        """Generate download command for approved model."""
        if candidate.recommended_file:
            return f'huggingface-cli download {candidate.model_id} {candidate.recommended_file} --local-dir C:\\AI\\Models'
        return ""
    
    def format_recommendation_card(self, candidate: ModelCandidate, show_detailed: bool = False) -> str:
        """Format recommendation as displayable card."""
        width = 65
        lines = [
            f"┌{'─' * (width-2)}┐",
            f"│ {'🤖 ' + candidate.display_name[:width-8]:<{width-4}} │",
            f"├{'─' * (width-2)}┤",
        ]
        
        # Score bar
        filled = int(candidate.score / 5)
        bar = '█' * filled + '░' * (20 - filled)
        lines.append(f"│ Score: {candidate.score:5.0f}/100  {bar} │")
        lines.append(f"│ Size: {candidate.size_gb:5.1f} GB  │  Downloads: {candidate.downloads:>12,} │")
        lines.append(f"├{'─' * (width-2)}┤")
        
        # Summary
        summary = candidate.case_summary
        while summary:
            chunk = summary[:width-4]
            lines.append(f"│ {chunk:<{width-4}} │")
            summary = summary[width-4:]
        
        lines.append(f"├{'─' * (width-2)}┤")
        
        # Strengths
        strengths = ", ".join(s.replace("_", " ") for s in candidate.strengths[:4])
        lines.append(f"│ Strengths: {strengths[:width-14]:<{width-14}} │")
        
        lines.append(f"└{'─' * (width-2)}┘")
        
        if show_detailed:
            lines.append("")
            lines.append(candidate.case_detailed)
        
        return "\n".join(lines)
    
    def generate_report(self, detailed: bool = False) -> str:
        """Generate full discovery report."""
        arsenal = self.analyze_arsenal()
        pending = self.get_pending_for_review()
        
        lines = [
            "# 🔍 Model Discovery Report",
            f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*",
            "",
            "## 📊 Current Arsenal Analysis",
            f"- **Models Installed:** {arsenal.total_models}",
            f"- **Total Storage:** {arsenal.total_size_gb:.1f} GB",
            f"- **Size Distribution:** {json.dumps(arsenal.size_distribution)}",
            f"- **Strongest Areas:** {', '.join(arsenal.strongest_areas)}",
            f"- **Weakest Areas:** {', '.join(arsenal.weakest_areas)}",
            f"- **Capability Gaps:** {', '.join(arsenal.capability_gaps) or 'None! 🎉'}",
            "",
        ]
        
        if pending:
            lines.extend([
                "## 🎯 Models Awaiting Your Approval",
                f"*{len(pending)} recommendations pending*",
                "",
            ])
            for r in pending[:7]:
                lines.append(self.format_recommendation_card(r, show_detailed=detailed))
                lines.append(f"   **Approve:** `python model_discovery.py --approve \"{r.model_id}\"`")
                lines.append(f"   **Reject:**  `python model_discovery.py --reject \"{r.model_id}\"`")
                lines.append("")
        else:
            lines.extend([
                "## ✅ No Pending Recommendations",
                "Run `python model_discovery.py --discover` to find new models.",
                ""
            ])
        
        return "\n".join(lines)


# ============================================================================
# MODEL DISCOVERY SERVICE (Legacy + Tracked Models)
# ============================================================================
class ModelDiscoveryService:
    """
    Service to discover, download, and manage tracked models.
    Works alongside ModelAdvisor for complete model management.
    
    Features:
    - Track recommended models from curated list
    - Check what's installed vs available
    - Download missing high-priority models
    - Benchmark new models after download
    """
    
    def __init__(self, models_dir: Path = MODELS_DIR):
        self.models_dir = models_dir
        self.cache = self._load_cache()
    
    def _load_cache(self) -> Dict:
        """Load discovery cache."""
        if DISCOVERY_CACHE.exists():
            try:
                with open(DISCOVERY_CACHE) as f:
                    return json.load(f)
            except:
                pass
        return {"last_scan": None, "models": {}}
    
    def _save_cache(self):
        """Save discovery cache."""
        with open(DISCOVERY_CACHE, 'w') as f:
            json.dump(self.cache, f, indent=2)
    
    def scan_installed(self) -> Dict[str, str]:
        """Scan for installed GGUF models."""
        installed = {}
        for f in self.models_dir.glob("*.gguf"):
            installed[f.stem.lower()] = str(f)
        return installed
    
    def get_status(self) -> List[ModelStatus]:
        """Get status of all tracked models."""
        installed = self.scan_installed()
        statuses = []
        
        for name, info in TRACKED_MODELS.items():
            # Check if installed (fuzzy match on filename)
            local_path = None
            is_installed = False
            
            for installed_name, path in installed.items():
                if name.replace("-", "").replace("_", "") in installed_name.replace("-", "").replace("_", ""):
                    is_installed = True
                    local_path = path
                    break
                # Also check the expected filename
                expected_stem = info["file"].replace(".gguf", "").lower()
                if expected_stem in installed_name:
                    is_installed = True
                    local_path = path
                    break
            
            statuses.append(ModelStatus(
                name=name,
                installed=is_installed,
                local_path=local_path,
                size_gb=info["size_gb"],
                category=info["category"],
                priority=info["priority"],
                last_checked=datetime.now().isoformat()
            ))
        
        return statuses
    
    def get_missing_models(self, priority: str = "high") -> List[str]:
        """Get list of missing models by priority."""
        statuses = self.get_status()
        
        priorities = ["high"]
        if priority in ["medium", "all"]:
            priorities.append("medium")
        if priority == "all":
            priorities.append("optional")
        
        missing = [
            s.name for s in statuses 
            if not s.installed and s.priority in priorities
        ]
        return missing
    
    def get_recommendations(self) -> Dict[str, Any]:
        """Get recommendations for improving model arsenal."""
        statuses = self.get_status()
        installed = {s.name: s for s in statuses if s.installed}
        missing = {s.name: s for s in statuses if not s.installed}
        
        recommendations = {
            "summary": {
                "installed": len(installed),
                "total_tracked": len(TRACKED_MODELS),
                "coverage": f"{len(installed)/len(TRACKED_MODELS)*100:.0f}%"
            },
            "by_category": {},
            "actions": []
        }
        
        # Check category coverage
        for category, required in MINIMUM_ARSENAL.items():
            cat_installed = [name for name in required if name in installed]
            cat_missing = [name for name in required if name in missing]
            
            recommendations["by_category"][category] = {
                "installed": cat_installed,
                "missing": cat_missing,
                "complete": len(cat_missing) == 0
            }
            
            if cat_missing:
                for name in cat_missing:
                    info = TRACKED_MODELS[name]
                    recommendations["actions"].append({
                        "action": "download",
                        "model": name,
                        "reason": f"Missing {category} model",
                        "size_gb": info["size_gb"],
                        "priority": info["priority"]
                    })
        
        return recommendations
    
    async def download_model(self, name: str, progress_callback=None) -> bool:
        """Download a tracked model."""
        if name not in TRACKED_MODELS:
            logger.error(f"Unknown model: {name}")
            return False
        
        info = TRACKED_MODELS[name]
        repo = info["repo"]
        filename = info["file"]
        
        logger.info(f"[Discovery] Downloading {name} from {repo}")
        
        # Use huggingface-cli
        cmd = [
            "huggingface-cli", "download",
            repo, filename,
            "--local-dir", str(self.models_dir)
        ]
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
        
        while True:
            line = process.stdout.readline()
            if not line and process.poll() is not None:
                break
            if line:
                if progress_callback:
                    progress_callback(line.strip())
                logger.info(f"[Download] {line.strip()}")
        
        success = process.returncode == 0
        
        if success:
            logger.info(f"[Discovery] Downloaded {name} successfully")
            self.cache["models"][name] = {
                "downloaded": datetime.now().isoformat(),
                "path": str(self.models_dir / filename)
            }
            self._save_cache()
        else:
            logger.error(f"[Discovery] Failed to download {name}")
        
        return success
    
    async def ensure_minimum_arsenal(self, progress_callback=None) -> Dict[str, bool]:
        """Ensure all minimum required models are installed."""
        results = {}
        
        for category, required in MINIMUM_ARSENAL.items():
            for name in required:
                statuses = self.get_status()
                status = next((s for s in statuses if s.name == name), None)
                
                if status and status.installed:
                    results[name] = True
                    continue
                
                # Download missing
                logger.info(f"[Discovery] Missing {category} model: {name}")
                success = await self.download_model(name, progress_callback)
                results[name] = success
        
        return results
    
    def print_status_report(self):
        """Print a formatted status report."""
        statuses = self.get_status()
        recs = self.get_recommendations()
        
        print("\n" + "=" * 60)
        print("📊 MODEL ARSENAL STATUS REPORT")
        print("=" * 60)
        
        print(f"\n📈 Summary: {recs['summary']['installed']}/{recs['summary']['total_tracked']} "
              f"tracked models installed ({recs['summary']['coverage']})")
        
        print("\n📦 By Category:")
        for cat, info in recs["by_category"].items():
            status = "✅" if info["complete"] else "⚠️"
            installed = ", ".join(info["installed"]) if info["installed"] else "none"
            print(f"  {status} {cat:12} - Installed: {installed}")
            if info["missing"]:
                print(f"     Missing: {', '.join(info['missing'])}")
        
        print("\n📋 Installed Models:")
        installed = sorted([s for s in statuses if s.installed], key=lambda x: x.size_gb, reverse=True)
        for s in installed:
            print(f"  ✓ {s.name:30} {s.size_gb:6.2f} GB  [{s.category}]")
        
        print("\n🔍 Available to Download:")
        missing = sorted([s for s in statuses if not s.installed], key=lambda x: (x.priority != "high", x.size_gb))
        for s in missing[:10]:  # Top 10
            priority_icon = "🔴" if s.priority == "high" else "🟡" if s.priority == "medium" else "⚪"
            print(f"  {priority_icon} {s.name:30} {s.size_gb:6.2f} GB  [{s.category}]")
        
        if recs["actions"]:
            print("\n⚡ Recommended Actions:")
            for action in recs["actions"][:5]:
                print(f"  → Download {action['model']} ({action['size_gb']}GB) - {action['reason']}")
        
        print("\n" + "=" * 60)


# ============================================================================
# CLI - Smart Model Discovery Interface
# ============================================================================
async def main():
    """CLI for intelligent model discovery."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="🔍 Intelligent Model Discovery - Your AI Model Advisor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python model_discovery.py --discover          # Find new models, build cases
  python model_discovery.py --pending           # See models awaiting your approval
  python model_discovery.py --approve "repo/model"  # Approve a recommendation
  python model_discovery.py --case "repo/model"     # See full case for a model
  python model_discovery.py --status            # Current arsenal status
        """
    )
    
    # Discovery actions
    parser.add_argument("--discover", action="store_true", 
                       help="🔍 Discover new models and build recommendation cases")
    parser.add_argument("--pending", action="store_true",
                       help="📋 Show models awaiting your approval")
    parser.add_argument("--report", action="store_true",
                       help="📊 Full discovery report with analysis")
    
    # Decision actions
    parser.add_argument("--approve", type=str, metavar="MODEL_ID",
                       help="✅ Approve a model for download")
    parser.add_argument("--reject", type=str, metavar="MODEL_ID",
                       help="❌ Reject a model recommendation")
    parser.add_argument("--defer", type=str, metavar="MODEL_ID",
                       help="⏳ Defer decision (ask me later)")
    parser.add_argument("--case", type=str, metavar="MODEL_ID",
                       help="📝 Show detailed case for a specific model")
    
    # Download approved
    parser.add_argument("--download-approved", action="store_true",
                       help="📥 Download all approved models")
    
    # Legacy options
    parser.add_argument("--status", action="store_true", help="Show status report")
    parser.add_argument("--download", type=str, help="Download specific tracked model")
    parser.add_argument("--ensure-minimum", action="store_true", 
                       help="Download all minimum required models")
    parser.add_argument("--list-missing", type=str, choices=["high", "medium", "all"],
                       help="List missing tracked models by priority")
    
    args = parser.parse_args()
    
    # Initialize services
    advisor = ModelAdvisor()
    service = ModelDiscoveryService()
    
    # ====== NEW INTELLIGENT FEATURES ======
    
    if args.discover:
        print("\n🔍 Discovering new models...")
        print("=" * 60)
        candidates = await advisor.discover_and_analyze()
        
        if candidates:
            print(f"\n✨ Found {len(candidates)} recommendations:\n")
            for c in candidates[:5]:
                print(advisor.format_recommendation_card(c))
                print()
            
            print("\n💡 Next steps:")
            print("  • Run --pending to see all awaiting approval")
            print("  • Run --case \"model_id\" to see full reasoning")
            print("  • Run --approve \"model_id\" to approve for download")
        else:
            print("\n✅ No new recommendations at this time.")
            print("Your model arsenal looks comprehensive!")
        return
    
    if args.pending:
        pending = advisor.get_pending_for_review()
        if pending:
            print(f"\n📋 {len(pending)} Models Awaiting Your Approval:\n")
            print("=" * 60)
            for i, r in enumerate(pending, 1):
                print(f"\n[{i}] {r.display_name}")
                print(f"    Score: {r.score:.0f}/100 | Size: {r.size_gb:.1f} GB | Downloads: {r.downloads:,}")
                print(f"    {r.case_summary}")
                print(f"    ID: {r.model_id}")
            
            print("\n" + "=" * 60)
            print("Actions:")
            print("  --approve \"model_id\"  : Approve for download")
            print("  --reject \"model_id\"   : Reject (won't show again)")
            print("  --case \"model_id\"     : See full reasoning")
        else:
            print("\n✅ No pending recommendations.")
            print("Run --discover to find new models.")
        return
    
    if args.case:
        for r in advisor.pending:
            if r.model_id == args.case or args.case in r.model_id:
                print("\n" + "=" * 60)
                print(advisor.format_recommendation_card(r, show_detailed=True))
                print("\n" + "=" * 60)
                print(f"\n📥 Download command:")
                print(f"   {advisor.get_download_command(r)}")
                return
        print(f"❌ Model not found: {args.case}")
        return
    
    if args.approve:
        r = advisor.approve(args.approve)
        if r:
            print(f"\n✅ Approved: {r.display_name}")
            print(f"\n📥 Download command:")
            cmd = advisor.get_download_command(r)
            print(f"   {cmd}")
            print(f"\nRun --download-approved to download all approved models")
        else:
            # Try partial match
            for rec in advisor.pending:
                if args.approve in rec.model_id:
                    r = advisor.approve(rec.model_id)
                    if r:
                        print(f"\n✅ Approved: {r.display_name}")
                        print(f"\n📥 Download command:")
                        print(f"   {advisor.get_download_command(r)}")
                        return
            print(f"❌ Model not found: {args.approve}")
        return
    
    if args.reject:
        advisor.reject(args.reject)
        print(f"❌ Rejected: {args.reject}")
        print("This model won't be recommended again.")
        return
    
    if args.defer:
        advisor.defer(args.defer)
        print(f"⏳ Deferred: {args.defer}")
        print("Will ask again later.")
        return
    
    if args.download_approved:
        approved = [r for r in advisor.pending if r.status == "approved"]
        if not approved:
            print("❌ No approved models to download.")
            print("Run --pending to see recommendations, then --approve to approve them.")
            return
        
        print(f"\n📥 Downloading {len(approved)} approved models...\n")
        for r in approved:
            print(f"Downloading: {r.display_name} ({r.size_gb:.1f} GB)")
            cmd = advisor.get_download_command(r)
            success = await service.download_model(r.model_id.split("/")[-1].lower().replace("-gguf", ""))
            if success:
                r.status = "completed"
                print(f"  ✅ Complete!")
            else:
                # Try direct HF download
                process = subprocess.Popen(cmd, shell=True)
                process.wait()
                if process.returncode == 0:
                    r.status = "completed"
                    print(f"  ✅ Complete!")
                else:
                    print(f"  ❌ Failed")
        advisor._save_pending()
        return
    
    if args.report:
        print(advisor.generate_report(detailed=True))
        return
    
    # ====== LEGACY FEATURES ======
    
    if args.status:
        service.print_status_report()
        # Also show pending recommendations
        pending = advisor.get_pending_for_review()
        if pending:
            print(f"\n💡 You have {len(pending)} model recommendations pending!")
            print("   Run --pending to review them.\n")
        return
    
    if args.download:
        await service.download_model(args.download)
        return
    
    if args.ensure_minimum:
        print("Ensuring minimum model arsenal...")
        results = await service.ensure_minimum_arsenal()
        for name, success in results.items():
            status = "✓" if success else "✗"
            print(f"  {status} {name}")
        return
    
    if args.list_missing:
        missing = service.get_missing_models(args.list_missing)
        print(f"Missing models ({args.list_missing} priority):")
        for name in missing:
            info = TRACKED_MODELS[name]
            print(f"  - {name} ({info['size_gb']}GB, {info['category']})")
        return
    
    # Default: show help with a quick status
    parser.print_help()
    
    print("\n" + "=" * 60)
    print("📊 Quick Status:")
    arsenal = advisor.analyze_arsenal()
    print(f"  Models: {arsenal.total_models} | Size: {arsenal.total_size_gb:.1f} GB")
    if arsenal.capability_gaps:
        print(f"  ⚠️ Capability gaps: {', '.join(arsenal.capability_gaps)}")
    
    pending = advisor.get_pending_for_review()
    if pending:
        print(f"\n  💡 {len(pending)} recommendations await your approval!")
        print(f"     Run: python model_discovery.py --pending")


if __name__ == "__main__":
    asyncio.run(main())
