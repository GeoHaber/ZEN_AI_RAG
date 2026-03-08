"""
ModelCard and ModelRegistry - GGUF Model discovery, categorization, and metadata

Discovers GGUF models, extracts metadata, categorizes by performance, detects
duplicates, and generates rich UI cards.

Thread-safe with RLock for concurrent access.
"""

import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from threading import RLock
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class ModelCategory(Enum):
    """Model size/performance categories"""

    FAST = "fast"  # <2B params, <1GB
    BALANCED = "balanced"  # 2-13B params, 1-8GB
    LARGE = "large"  # >13B params, >8GB
    SPECIALIZED = "specialized"


class QuantizationType(Enum):
    """GGUF quantization types"""

    Q2_K = "Q2_K"
    Q3_K = "Q3_K"
    Q4_K = "Q4_K"
    Q4_1 = "Q4_1"
    Q5_K = "Q5_K"
    Q5_1 = "Q5_1"
    Q6_K = "Q6_K"
    Q8_0 = "Q8_0"
    F16 = "F16"
    F32 = "F32"


@dataclass
class ModelCapabilities:
    """Model capabilities/tags"""

    chat: bool = False
    coding: bool = False
    reasoning: bool = False
    math: bool = False
    multilingual: bool = False
    vision: bool = False

    def to_list(self) -> List[str]:
        """Convert to list of capability names"""
        caps = []
        if self.chat:
            caps.append("Chat")
        if self.coding:
            caps.append("Coding")
        if self.reasoning:
            caps.append("Reasoning")
        if self.math:
            caps.append("Math")
        if self.multilingual:
            caps.append("Multilingual")
        if self.vision:
            caps.append("Vision")
        return caps


@dataclass
class ModelCard:
    """Complete model metadata for display"""

    id: str  # Unique identifier
    name: str  # Display name
    filename: str  # Actual filename
    path: Path  # Full path to file
    size: str  # Formatted size (e.g. "~4GB")
    size_bytes: int  # Actual size in bytes
    base_model: str  # Base model name (e.g. "mistral-7b")
    quantization: Optional[str]  # Quantization type
    category: ModelCategory  # Performance category
    context: int  # Context window size
    estimated_speed: int  # Estimated tokens/sec
    recommended_ram: int  # Recommended RAM in GB
    description: str  # Short description
    capabilities: ModelCapabilities  # What it can do
    source: str  # Source repo (e.g. "mistralai/Mistral-7B-Instruct-v0.3")
    url: str  # Download/info URL
    version: Optional[str] = None  # Model version
    release_date: Optional[str] = None  # Release date
    last_updated: Optional[str] = None  # Last update date

    def to_card_dict(self) -> dict:
        """Convert to UI card dict"""
        return {
            "id": self.id,
            "name": self.name,
            "filename": self.filename,
            "size": self.size,
            "base_model": self.base_model,
            "quantization": self.quantization,
            "category": self.category.value,
            "context": self.context,
            "estimated_speed": self.estimated_speed,
            "recommended_ram": self.recommended_ram,
            "description": self.description,
            "capabilities": self.capabilities.to_list(),
            "source": self.source,
            "url": self.url,
            "version": self.version,
            "path": str(self.path),
        }


class ModelRegistry:
    """Discover, categorize, and manage GGUF models"""

    # Hardcoded metadata for known models
    MODEL_METADATA = {
        "mistral-7b": {
            "description": "Excellent reasoning & analysis, great all-rounder",
            "context": 8192,
            "estimated_speed": 10,
            "recommended_ram": 8,
            "source": "mistralai/Mistral-7B-Instruct-v0.3",
            "url": "https://huggingface.co/mistralai/Mistral-7B-Instruct-v0.3",
            "capabilities": {"chat": True, "coding": True, "reasoning": True},
        },
        "qwen2.5-14b": {
            "description": "Advanced multilingual, excellent coding",
            "context": 32768,
            "estimated_speed": 6,
            "recommended_ram": 16,
            "source": "Qwen/Qwen2.5-14B-Instruct",
            "url": "https://huggingface.co/Qwen/Qwen2.5-14B-Instruct",
            "capabilities": {"chat": True, "coding": True, "reasoning": True, "multilingual": True},
        },
        "deepseek-coder": {
            "description": "Specialized for code generation and analysis",
            "context": 4096,
            "estimated_speed": 12,
            "recommended_ram": 8,
            "source": "deepseek-ai/deepseek-coder-6.7b-instruct",
            "url": "https://huggingface.co/deepseek-ai/deepseek-coder-6.7b-instruct",
            "capabilities": {"chat": True, "coding": True, "math": True},
        },
        "phi": {
            "description": "Fast lightweight model, good for quick tasks",
            "context": 4096,
            "estimated_speed": 25,
            "recommended_ram": 4,
            "source": "microsoft/phi-2",
            "url": "https://huggingface.co/microsoft/phi-2",
            "capabilities": {"chat": True, "coding": True},
        },
        "llama": {
            "description": "Meta's foundational model, reliable baseline",
            "context": 4096,
            "estimated_speed": 10,
            "recommended_ram": 8,
            "source": "meta-llama/Llama-2-7b-hf",
            "url": "https://huggingface.co/meta-llama/Llama-2-7b-hf",
            "capabilities": {"chat": True},
        },
        "neural-chat": {
            "description": "Optimized for conversation and instruction following",
            "context": 4096,
            "estimated_speed": 12,
            "recommended_ram": 8,
            "source": "Intel/neural-chat-7b-v3-3",
            "url": "https://huggingface.co/Intel/neural-chat-7b-v3-3",
            "capabilities": {"chat": True},
        },
        "tinyllama": {
            "description": "Ultra-lightweight, good for basic tasks",
            "context": 2048,
            "estimated_speed": 30,
            "recommended_ram": 2,
            "source": "TinyLlama/TinyLlama-1.1B-Chat-v1.0",
            "url": "https://huggingface.co/TinyLlama/TinyLlama-1.1B-Chat-v1.0",
            "capabilities": {"chat": True},
        },
        "neural-7b": {
            "description": "Balanced performance and efficiency",
            "context": 4096,
            "estimated_speed": 11,
            "recommended_ram": 8,
            "source": "intel/neural-chat-7b-v3",
            "url": "https://huggingface.co/intel/neural-chat-7b-v3",
            "capabilities": {"chat": True, "coding": True},
        },
        "openchat": {
            "description": "Fast and efficient chat model",
            "context": 8192,
            "estimated_speed": 14,
            "recommended_ram": 8,
            "source": "openchat/openchat-3.5-1210",
            "url": "https://huggingface.co/openchat/openchat-3.5-1210",
            "capabilities": {"chat": True, "coding": True},
        },
        "zephyr": {
            "description": "Fast and helpful instruction follower",
            "context": 4096,
            "estimated_speed": 16,
            "recommended_ram": 8,
            "source": "HuggingFaceH4/zephyr-7b-beta",
            "url": "https://huggingface.co/HuggingFaceH4/zephyr-7b-beta",
            "capabilities": {"chat": True},
        },
        "nous-hermes": {
            "description": "Creative and reasoning focused",
            "context": 4096,
            "estimated_speed": 10,
            "recommended_ram": 8,
            "source": "NousResearch/Nous-Hermes-2-Mixtral-8x7B",
            "url": "https://huggingface.co/NousResearch/Nous-Hermes-2-Mixtral-8x7B",
            "capabilities": {"chat": True, "reasoning": True},
        },
    }

    def __init__(self, model_dir: Optional[Path] = None):
        """
        Initialize registry

        Args:
            model_dir: Directory to scan for models (default: C:\\AI\\Models)
        """
        self._lock = RLock()
        self.model_dir = model_dir or Path("C:\\AI\\Models")
        self.models: List[ModelCard] = []
        self._model_groups: Dict[str, List[ModelCard]] = {}

    def discover(self) -> List[ModelCard]:
        """
        Discover all GGUF models in model directory

        Returns:
            List of ModelCard objects
        """
        with self._lock:
            self.models = []
            self._model_groups = {}

            if not self.model_dir.exists():
                logger.warning(f"Model directory not found: {self.model_dir}")
                return self.models

            # Find all .gguf files
            gguf_files = list(self.model_dir.glob("*.gguf"))
            logger.info(f"Discovering models in {self.model_dir}")
            logger.info(f"Found {len(gguf_files)} GGUF files")

            for file_path in gguf_files:
                try:
                    card = self._create_card(file_path)
                    self.models.append(card)
                except Exception as e:
                    logger.warning(f"Could not create card for {file_path}: {e}")

            # Group by base model
            self._group_by_base_model()

            logger.info(f"Created {len(self.models)} model cards")
            logger.info(f"Organized into {len(self._model_groups)} base model groups")

            return self.models

    def _create_card(self, file_path: Path) -> ModelCard:
        """
        Create ModelCard from GGUF file

        Args:
            file_path: Path to .gguf file

        Returns:
            ModelCard with metadata
        """
        filename = file_path.name
        base_model = self._extract_base_model(filename)
        quantization = self._extract_quantization(filename)
        size_bytes = file_path.stat().st_size
        size_str = self._format_size(size_bytes)

        # Get metadata or use defaults
        metadata = self.MODEL_METADATA.get(base_model, {})

        # Determine category
        category = self._determine_category(size_bytes, base_model)

        # Build capabilities
        caps_dict = metadata.get("capabilities", {})
        caps = ModelCapabilities(
            chat=caps_dict.get("chat", False),
            coding=caps_dict.get("coding", False),
            reasoning=caps_dict.get("reasoning", False),
            math=caps_dict.get("math", False),
            multilingual=caps_dict.get("multilingual", False),
            vision=caps_dict.get("vision", False),
        )

        return ModelCard(
            id=base_model,
            name=filename.replace(".gguf", "").replace(".", " "),
            filename=filename,
            path=file_path,
            size=size_str,
            size_bytes=size_bytes,
            base_model=base_model,
            quantization=quantization,
            category=category,
            context=metadata.get("context", 4096),
            estimated_speed=metadata.get("estimated_speed", 10),
            recommended_ram=metadata.get("recommended_ram", 8),
            description=metadata.get("description", f"{base_model} model"),
            capabilities=caps,
            source=metadata.get("source", base_model),
            url=metadata.get("url", f"https://huggingface.co/{base_model}"),
        )

    def _extract_base_model(self, filename: str) -> str:
        """
        Extract base model name from filename

        Args:
            filename: GGUF filename

        Returns:
            Normalized base model name
        """
        # Remove .gguf extension
        name = filename.replace(".gguf", "")

        # Remove quantization markers
        parts = name.split(".")
        base = parts[0] if parts else name

        # Normalize to lowercase
        base = base.lower()

        # Handle common patterns
        replacements = {
            "mistral": "mistral",
            "llama": "llama",
            "qwen": "qwen2.5",
            "deepseek": "deepseek-coder",
            "phi": "phi",
            "tinyllama": "tinyllama",
            "openchat": "openchat",
            "zephyr": "zephyr",
            "neural": "neural-chat",
            "nous": "nous-hermes",
        }

        for key, val in replacements.items():
            if key in base:
                return val

        return base

    def _extract_quantization(self, filename: str) -> Optional[str]:
        """
        Extract quantization type from filename

        Args:
            filename: GGUF filename

        Returns:
            Quantization type or None
        """
        quant_types = ["Q2_K", "Q3_K", "Q4_K", "Q4_1", "Q5_K", "Q5_1", "Q6_K", "Q8_0", "F16", "F32"]

        filename_upper = filename.upper()
        for quant in quant_types:
            if quant in filename_upper:
                return quant

        return None

    def _determine_category(self, size_bytes: int, base_model: str) -> ModelCategory:
        """
        Determine category by model size or name hints

        Args:
            size_bytes: File size in bytes
            base_model: Base model name

        Returns:
            ModelCategory
        """
        size_gb = size_bytes / (1024**3)

        # Name-based hints
        if any(x in base_model.lower() for x in ["tiny", "small", "mini"]):
            return ModelCategory.FAST

        if "large" in base_model.lower() or "xl" in base_model.lower():
            return ModelCategory.LARGE

        # Size-based
        if size_gb < 1.5:
            return ModelCategory.FAST
        elif size_gb > 10:
            return ModelCategory.LARGE
        else:
            return ModelCategory.BALANCED

    def _format_size(self, size_bytes: int) -> str:
        """Format bytes to human-readable size"""
        for unit in ["B", "KB", "MB", "GB"]:
            if size_bytes < 1024:
                return f"~{size_bytes:.1f}{unit}"
            size_bytes /= 1024
        return f"~{size_bytes:.1f}TB"

    def _group_by_base_model(self):
        """Group models by base model name"""
        self._model_groups = {}
        for model in self.models:
            base = model.base_model
            if base not in self._model_groups:
                self._model_groups[base] = []
            self._model_groups[base].append(model)

    def get_duplicates(self) -> Dict[str, List[ModelCard]]:
        """
        Get models with same base but different quantizations

        Returns:
            Dict of base_model: [variants...]
        """
        with self._lock:
            duplicates = {}
            for base, models in self._model_groups.items():
                if len(models) > 1:
                    duplicates[base] = models
            return duplicates

    def get_cards_by_category(self, category: ModelCategory) -> List[ModelCard]:
        """Get models in specific category"""
        with self._lock:
            return [m for m in self.models if m.category == category]

    def get_recommendations(self, use_case: str = "balanced") -> List[ModelCard]:
        """
        Get model recommendations for use case

        Args:
            use_case: 'fast', 'balanced', 'quality', 'coding', 'reasoning'

        Returns:
            Recommended models
        """
        with self._lock:
            if use_case == "fast":
                return self.get_cards_by_category(ModelCategory.FAST)

            elif use_case == "balanced":
                return self.get_cards_by_category(ModelCategory.BALANCED)

            elif use_case == "quality":
                return sorted(self.get_cards_by_category(ModelCategory.LARGE), key=lambda m: m.context, reverse=True)

            elif use_case == "coding":
                return sorted(
                    [m for m in self.models if m.capabilities.coding], key=lambda m: m.estimated_speed, reverse=True
                )

            elif use_case == "reasoning":
                return sorted(
                    [m for m in self.models if m.capabilities.reasoning], key=lambda m: m.context, reverse=True
                )

            return self.models

    def get_all_cards(self) -> List[dict]:
        """Get all models as UI-ready card dicts"""
        with self._lock:
            return [m.to_card_dict() for m in self.models]
