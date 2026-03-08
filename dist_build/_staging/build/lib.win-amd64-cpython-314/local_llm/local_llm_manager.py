"""
LocalLLMManager - Orchestration layer for local LLM infrastructure

Combines LlamaCppManager and ModelRegistry to provide unified interface
for managing local llama.cpp and GGUF models.

Main entry point for applications.
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from threading import RLock
from typing import Dict, List, Optional

# Support both relative and absolute imports
try:
    from .llama_cpp_manager import LlamaCppManager, LlamaCppStatus
    from .model_card import ModelRegistry, ModelCard, ModelCategory
except ImportError:
    from llama_cpp_manager import LlamaCppManager
    from model_card import ModelRegistry, ModelCard, ModelCategory

logger = logging.getLogger(__name__)


@dataclass
class LocalLLMStatus:
    """Complete local LLM infrastructure status"""

    llama_cpp_ready: bool
    llama_cpp_status: Dict
    models_discovered: int
    models: List[ModelCard] = field(default_factory=list)
    duplicate_groups: Optional[Dict[str, List[ModelCard]]] = None

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict"""
        return {
            "llama_cpp_ready": self.llama_cpp_ready,
            "llama_cpp_status": self.llama_cpp_status,
            "models_discovered": self.models_discovered,
            "models": [m.to_card_dict() for m in self.models],
            "duplicate_groups": {k: [m.to_card_dict() for m in v] for k, v in (self.duplicate_groups or {}).items()},
        }


class LocalLLMManager:
    """Main orchestrator for local LLM infrastructure"""

    def __init__(self, model_dir: Optional[Path] = None):
        """
        Initialize manager

        Args:
            model_dir: Directory containing GGUF models (default: C:\\AI\\Models)
        """
        self._lock = RLock()
        self.llama_manager = LlamaCppManager()
        self.registry = ModelRegistry(model_dir or Path("C:\\AI\\Models"))
        self._status = None
        self._selected_duplicates: Dict[str, ModelCard] = {}

    def initialize(self, check_updates: bool = False) -> LocalLLMStatus:
        """
        Full initialization: find llama.cpp, discover models, handle duplicates

        Args:
            check_updates: Whether to check for model updates (Phase 2)

        Returns:
            LocalLLMStatus with complete system status
        """
        with self._lock:
            logger.info("Initializing LocalLLMManager...")
            logger.info("Searching for llama-server executable...")

            # Check llama.cpp
            llama_status = self.llama_manager.get_status()
            llama_ready = llama_status.installed

            if llama_ready:
                logger.info(f"Found llama.cpp version {llama_status.version}")
                if llama_status.needs_update:
                    logger.warning(f"Update available: {llama_status.latest_version}")
            else:
                logger.warning("llama.cpp not found - models won't work without it")

            # Discover models
            logger.info(f"Discovering models in {self.registry.model_dir}")
            models = self.registry.discover()
            logger.info(f"Found {len(models)} models in {len(self.registry._model_groups)} groups")

            # Detect duplicates
            duplicates = self.registry.get_duplicates()
            if duplicates:
                for base_name, variants in duplicates.items():
                    logger.warning(f"Found {len(variants)} variants of {base_name} - choose which to keep")

            # Build status
            self._status = LocalLLMStatus(
                llama_cpp_ready=llama_ready,
                llama_cpp_status=llama_status.to_dict(),
                models_discovered=len(models),
                models=models,
                duplicate_groups=duplicates if duplicates else None,
            )

            return self._status

    def get_status(self) -> LocalLLMStatus:
        """
        Get current status (cached or fresh)

        Returns:
            LocalLLMStatus
        """
        if self._status is None:
            return self.initialize()
        return self._status

    def handle_duplicates(self, duplicate_group: List[ModelCard]) -> ModelCard:
        """
        Handle duplicate model variants (user chooses which to keep)

        Args:
            duplicate_group: List of model variants

        Returns:
            Selected ModelCard
        """
        if not duplicate_group:
            return None

        print("\n" + "=" * 60)
        print("Duplicate Models Found")
        print("=" * 60)

        base_name = duplicate_group[0].base_model
        print(f"\nBase Model: {base_name}")
        print(f"Found {len(duplicate_group)} variants:\n")

        for i, model in enumerate(duplicate_group, 1):
            quant_info = f" [{model.quantization}]" if model.quantization else ""
            print(f"  {i}. {model.filename}{quant_info}")
            print(f"     Size: {model.size}")
            print(f"     Quantization: {model.quantization or 'Original'}")
            print()

        # Prompt user
        while True:
            try:
                choice = input("Which variant to keep? (1-{0}): ".format(len(duplicate_group))).strip()
                choice_idx = int(choice) - 1

                if 0 <= choice_idx < len(duplicate_group):
                    selected = duplicate_group[choice_idx]
                    self._selected_duplicates[base_name] = selected
                    print(f"✓ Selected: {selected.filename}\n")
                    return selected
                else:
                    print(f"Invalid choice. Enter 1-{len(duplicate_group)}")
            except ValueError:
                print("Invalid input. Enter a number.")

    def check_model_updates(self) -> Dict:
        """
        Check for model updates (Phase 2 - HuggingFace integration)

        Returns:
            Dict of updates available
        """
        # TODO: Integrate with HuggingFace API to check for updates
        logger.info("Model update checking not yet implemented (Phase 2)")
        return {}

    def get_model_by_category(self, category: ModelCategory) -> List[ModelCard]:
        """Get models by performance category"""
        return self.registry.get_cards_by_category(category)

    def get_recommendations(self, use_case: str) -> List[ModelCard]:
        """
        Get model recommendations for use case

        Args:
            use_case: 'fast', 'balanced', 'quality', 'coding', 'reasoning'

        Returns:
            List of recommended models
        """
        return self.registry.get_recommendations(use_case)

    def get_all_cards(self) -> List[dict]:
        """Get all models as UI-ready cards"""
        return self.registry.get_all_cards()

    def print_summary(self):
        """Print human-readable status summary"""
        status = self.get_status()

        print("\n" + "=" * 70)
        print("LOCAL LLM MANAGER - STATUS SUMMARY")
        print("=" * 70)

        # llama.cpp status
        print("\n[llama.cpp Server]")
        llama = status.llama_cpp_status
        if llama["installed"]:
            print(f"  ✓ Installed: {llama['version']}")
            if llama["needs_update"]:
                print(f"  ⚠ Update available: {llama['latest_version']}")
            if llama["running"]:
                print(f"  ✓ Running (PID: {llama['pid']})")
            else:
                print("  ✗ Not running")
        else:
            print("  ✗ Not installed")
            print(f"  Download from: {self.llama_manager.get_download_url()}")

        # Models status
        print(f"\n[Models]")
        print(f"  Total discovered: {status.models_discovered}")
        print(f"  Groups: {len(self.registry._model_groups)}")

        # Category breakdown
        by_category = {}
        for model in status.models:
            cat = model.category.value
            by_category[cat] = by_category.get(cat, 0) + 1

        for cat, count in sorted(by_category.items()):
            print(f"    - {cat.capitalize()}: {count}")

        # Duplicates
        if status.duplicate_groups:
            print(f"\n[Duplicates]")
            for base_name, variants in status.duplicate_groups.items():
                print(f"  • {base_name}: {len(variants)} variants")
                for v in variants:
                    marker = "✓" if v in self._selected_duplicates.values() else " "
                    print(f"    {marker} {v.filename}")

        # Recommendations
        print(f"\n[Model Recommendations]")
        fast = self.get_recommendations("fast")
        print(f"  Fast: {len(fast)} models")
        if fast:
            print(f"    • {fast[0].name}")

        coding = self.get_recommendations("coding")
        print(f"  Coding: {len(coding)} models")
        if coding:
            print(f"    • {coding[0].name}")

        reasoning = self.get_recommendations("reasoning")
        print(f"  Reasoning: {len(reasoning)} models")
        if reasoning:
            print(f"    • {reasoning[0].name}")

        print("\n" + "=" * 70 + "\n")


if __name__ == "__main__":
    # Quick test
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    manager = LocalLLMManager()
    status = manager.initialize()

    print(f"\nllama.cpp ready: {status.llama_cpp_ready}")
    print(f"Models found: {status.models_discovered}")

    if status.duplicate_groups:
        print(f"Duplicates: {list(status.duplicate_groups.keys())}")

    print("\nRecommendations for 'coding':")
    coding = manager.get_recommendations("coding")
    for m in coding[:3]:
        print(f"  • {m.name}")

    manager.print_summary()
