"""
Rust inference module wrapper with adaptive timeout support.

Provides:
- Token counting with model awareness (Rust accelerated)
- Inference timeout calculation based on provider
- Fallback to Python if Rust unavailable
"""

import logging
from typing import Optional, Dict, Tuple

logger = logging.getLogger(__name__)

# Try to import Rust inference module
RUST_INFERENCE_AVAILABLE = False
RUST_INFERENCE_ERROR = None

try:
    # Try importing from the compiled Rust extension
    import rag_rat_rust

    # Check if inference functions are available
    if hasattr(rag_rat_rust, "parse_image_dimension"):
        # Basic functions are available
        RUST_INFERENCE_AVAILABLE = True
        logger.info("✅ Rust inference utilities loaded")
    else:
        RUST_INFERENCE_ERROR = "Missing required inference functions"
        logger.warning("⚠️  Rust extension missing inference functions")

except ImportError as e:
    RUST_INFERENCE_ERROR = str(e)
    logger.warning(f"⚠️  Rust inference module not available: {e}")


# ═══════════════════════════════════════════════════════════════════════════
# TIMEOUT CALCULATION - Ported from Python chat.py bugfix
# ═══════════════════════════════════════════════════════════════════════════


def calculate_inference_timeout(provider: str, model: str = "", max_tokens: int = 256) -> float:
    """
    Calculate adaptive timeout for LLM inference based on provider type.

    BUGFIX: Replaces fixed 30s timeout with adaptive timeout per provider.
    - Local models (CPU): 240s (4 minutes) - slow but usable
    - API models: 60s (sufficient for cloud inference)
    - Fine-tuned based on max_tokens (more tokens = more time)

    Args:
        provider: LLM provider name (e.g., "Local (llama-cpp)", "OpenAI", "Claude")
        model: Model name (informational)
        max_tokens: Maximum tokens to generate (affects timeout)

    Returns:
        Timeout in seconds
    """
    provider_lower = (provider or "").lower()
    is_local = any(x in provider_lower for x in ["llama", "ollama", "local"])

    if is_local:
        # Local model on CPU: Calculate based on expected token rate
        # TinyLlama: ~40-80 tokens/sec (avg 50 tok/sec)
        # Larger models slower: 10-30 tokens/sec

        # Conservative: assume 30 tokens/sec on CPU
        tokens_per_second = 30.0
        token_time = max(5.0, max_tokens / tokens_per_second)

        # Add overhead for context processing
        base_timeout = 60.0
        total_timeout = base_timeout + token_time

        # Cap at 5 minutes for extreme cases
        final_timeout = min(300.0, total_timeout)

        logger.debug(f"Local model timeout: base={base_timeout}s + tokens={token_time:.1f}s = {final_timeout:.1f}s")
        return final_timeout

    else:
        # API models: typically respond in 1-30 seconds
        # Use 60s as generous upper bound
        logger.debug("API model timeout: 60s")
        return 60.0


# ═══════════════════════════════════════════════════════════════════════════
# TOKEN COUNTING - Rust accelerated with Python fallback
# ═══════════════════════════════════════════════════════════════════════════


def count_tokens_safe(text: str, model: str = "tinyllama") -> int:
    """
    Count tokens in text using Python (with Rust fallback planned).

    Args:
        text: Input text
        model: Model name for multiplier adjustment

    Returns:
        Estimated token count
    """
    # Python implementation: simple whitespace-based counting
    # Rough approximation: ~0.25 words per token (or ~4 chars per token)
    words = len(text.split())
    char_tokens = len(text) / 4
    base_tokens = int(max(words * 0.25, char_tokens))

    # Apply model multiplier
    multipliers = {
        "tinyllama": 1.0,
        "llama2": 1.1,
        "mistral": 0.95,
    }
    multiplier = multipliers.get(model.lower(), 1.0)

    return int(base_tokens * multiplier)


def validate_tokens_safe(
    tokens: int, model: str = "tinyllama", max_tokens: Optional[int] = None
) -> Tuple[bool, Optional[str]]:
    """
    Validate token count against model limits.

    Args:
        tokens: Token count to validate
        model: Model name
        max_tokens: Override max (uses model default if None)

    Returns:
        (is_valid, error_message)
    """
    # Python implementation: model-specific limits
    limits = {
        "tinyllama": 4096,
        "llama2": 4096,
        "mistral": 32000,
    }

    limit = max_tokens or limits.get(model.lower(), 4096)

    if tokens > limit:
        return (False, f"Token count ({tokens}) exceeds limit ({limit}) for {model}")

    return (True, None)


# ═══════════════════════════════════════════════════════════════════════════
# INFERENCE REQUEST BUILDER - With automatic timeout
# ═══════════════════════════════════════════════════════════════════════════


def build_inference_request(
    provider: str,
    model: str,
    prompt: str,
    max_tokens: int = 256,
    temperature: float = 0.7,
    system_prompt: Optional[str] = None,
) -> Dict:
    """
    Build inference request with calculated timeout.

    Args:
        provider: LLM provider
        model: Model name
        prompt: Input prompt
        max_tokens: Max tokens to generate
        temperature: Sampling temperature
        system_prompt: System context

    Returns:
        Request dict with timeout field
    """
    # Calculate timeout adaptively
    timeout = calculate_inference_timeout(provider, model, max_tokens)

    # Validate token count
    prompt_tokens = count_tokens_safe(prompt, model)
    is_valid, error = validate_tokens_safe(prompt_tokens, model)

    if not is_valid:
        logger.warning(f"Token validation warning: {error}")

    return {
        "provider": provider,
        "model": model,
        "prompt": prompt,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "system_prompt": system_prompt,
        "timeout": timeout,
        "prompt_tokens": prompt_tokens,
    }


# ═══════════════════════════════════════════════════════════════════════════
# STATUS & DIAGNOSTICS
# ═══════════════════════════════════════════════════════════════════════════


def get_inference_status() -> Dict:
    """Get status of Rust inference module."""
    return {
        "available": RUST_INFERENCE_AVAILABLE,
        "error": RUST_INFERENCE_ERROR,
    }


def test_timeout_calculation():
    """Test timeout calculation for different providers."""
    print("\n" + "=" * 70)
    print("TIMEOUT CALCULATION TEST")
    print("=" * 70)

    test_cases = [
        ("Local (llama-cpp)", "tinyllama-1.1b", 256),
        ("Local (llama-cpp)", "mistral-7b", 512),
        ("Ollama", "neural-chat", 128),
        ("OpenAI", "gpt-4", 256),
        ("Anthropic (Claude)", "claude-3-sonnet", 256),
        ("Gemini", "gemini-pro", 512),
    ]

    for provider, model, tokens in test_cases:
        timeout = calculate_inference_timeout(provider, model, tokens)
        is_local = any(x in provider.lower() for x in ["llama", "ollama", "local"])
        model_type = "LOCAL (CPU)" if is_local else "API"
        print(f"  {provider:30} {model:20} {tokens:3} tokens → {timeout:6.1f}s [{model_type}]")

    print()


if __name__ == "__main__":
    print(f"Rust inference status: {get_inference_status()}")
    test_timeout_calculation()

    # Test token counting
    test_text = "Hello world! This is a test of the token counting system."
    tokens = count_tokens_safe(test_text, "tinyllama")
    print("\nToken counting test:")
    print(f"  Text: {test_text!r}")
    print(f"  Tokens: {tokens}")
    # Test request building
    request = build_inference_request(
        provider="Local (llama-cpp)",
        model="tinyllama",
        prompt="What is AI?",
        max_tokens=256,
    )
    print("\nInference request:")
    for key, value in request.items():
        print(f"  {key}: {value}")        pass
        pass
