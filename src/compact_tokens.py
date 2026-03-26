"""
Compact Tokens — Reduce conversation token count by 10-50x.

Pipeline (applied in order):
  1. Deduplicate     — Drop exact duplicate messages
  2. System Coalesce — Combine multiple system prompts into one
  3. Role Merge      — Merge consecutive same-role messages
  4. Whitespace Norm — Collapse multiple spaces/newlines
  5. Text Compress   — Remove filler words/phrases
  6. History Summarize— Collapse old turns into a context line
  7. Hard Truncate   — Fit target context window (tokens or chars)

Usage:
    from compact_tokens import compact_messages, compact_for_inference, CompactConfig

    compacted, stats = compact_messages(messages)
    compacted = compact_for_inference(messages, keep_last_n=4, target_tokens=4096)
"""

import hashlib
import logging
import re
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("compact_tokens")


# =========================================================================
# CONFIG
# =========================================================================


@dataclass
class CompactConfig:
    """Configuration for the compaction pipeline."""

    # How many recent messages to keep verbatim (never compress these)
    keep_last_n: int = 4

    # Summarize older messages into a single "[Context]" system message
    summarize_older: bool = True

    # Maximum chars for the summary of older messages (high so we don't truncate results used for summarise)
    summary_max_chars: int = 16_000

    # Merge consecutive messages from the same role
    merge_same_role: bool = True

    # Deduplicate exact repeated messages
    deduplicate: bool = True

    # Apply linguistic compression (remove filler, shorten)
    compress_text: bool = True

    # Normalize whitespace
    normalize_whitespace: bool = True

    # Max total chars after compaction (0 = no limit)
    max_total_chars: int = 0

    # Target context window (tokens) — hard truncate if needed
    target_ctx_tokens: int = 4096

    # Chars per token estimate
    chars_per_token: float = 4.0

    # Keep system messages intact (don't compress their content)
    protect_system: bool = True


# =========================================================================
# FILLER PATTERNS (compiled once at import)
# =========================================================================

_FILLER_PATTERNS = [
    # Politeness fluff
    (r"\bplease\b", ""),
    (r"\bkindly\b", ""),
    (r"\bcould you\b", ""),
    (r"\bwould you\b", ""),
    (r"\bcan you\b", ""),
    (r"\bI would like you to\b", ""),
    (r"\bI need you to\b", ""),
    (r"\bI want you to\b", ""),
    # Verbose connectors
    (r"\bin order to\b", "to"),
    (r"\bdue to the fact that\b", "because"),
    (r"\bat this point in time\b", "now"),
    (r"\bin the event that\b", "if"),
    (r"\bfor the purpose of\b", "to"),
    (r"\bin the process of\b", ""),
    (r"\bin terms of\b", "in"),
    (r"\bwith regard to\b", "re:"),
    (r"\bwith respect to\b", "re:"),
    (r"\bas a matter of fact\b", ""),
    (r"\bit is important to note that\b", "note:"),
    (r"\bit should be noted that\b", "note:"),
    (r"\bthe fact that\b", "that"),
    (r"\bin spite of the fact that\b", "although"),
    (r"\bregardless of the fact that\b", "although"),
    # ChatGPT-style preambles users often paste back
    (
        r"(?i)^(Sure[!,.]?\s*|Of course[!,.]?\s*|Certainly[!,.]?\s*|"
        r"Absolutely[!,.]?\s*|Great question[!,.]?\s*|"
        r"That'?s a great question[!,.]?\s*)",
        "",
    ),
    # Redundant starters
    (r"(?i)^Here (?:is|are) (?:the |a |an |my )?", ""),
]

_COMPILED_FILLERS = [(re.compile(p, re.IGNORECASE), r) for p, r in _FILLER_PATTERNS]
_MULTI_SPACE = re.compile(r"[ \t]+")
_MULTI_NEWLINE = re.compile(r"\n{3,}")

# Qwen3-style thinking blocks: do not expose in UI; keep for backend/debug only
_THINKING_BLOCK_RE = re.compile(r"<thinking?\s*>.*?</thinking?\s*>", re.DOTALL | re.IGNORECASE)
_THINKING_OPEN_RE = re.compile(r"<thinking?\s*>.*", re.DOTALL | re.IGNORECASE)


def strip_thinking_blocks(text: str, log_stripped: bool = True) -> str:
    """
    Remove <think>...</think> blocks from model output (e.g. Qwen3). Use for UI display;
    thinking content remains in backend logs only when log_stripped is True.
    """
    if not text or not isinstance(text, str):
        return text or ""
    out = _THINKING_BLOCK_RE.sub("", text)
    # Remove unclosed <think>... at the end
    out = _THINKING_OPEN_RE.sub("", out)
    out = out.strip()
    if log_stripped and len(out) != len(text.strip()):
        stripped = text.strip()[:500] if len(text) > 500 else text.strip()
        logger.debug(
            "Stripped thinking block from response (not shown in UI): %.200s...",
            stripped,
        )
    return out


# =========================================================================
# PIPELINE STAGES (pure functions, no side effects)
# =========================================================================


def _normalize_whitespace(text: str) -> str:
    """Collapse multiple spaces/newlines, strip edges."""
    text = _MULTI_SPACE.sub(" ", text)
    text = _MULTI_NEWLINE.sub("\n\n", text)
    return text.strip()


def _compress_text(text: str) -> str:
    """Apply linguistic compression — remove filler without losing meaning."""
    for pattern, replacement in _COMPILED_FILLERS:
        text = pattern.sub(replacement, text)
    text = _MULTI_SPACE.sub(" ", text)
    return text.strip()


def _deduplicate(messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """Remove exact duplicate messages (keep first occurrence)."""
    seen = set()
    result = []
    for msg in messages:
        key = f"{msg.get('role', '')}|{msg.get('content', '')}"
        h = hashlib.md5(key.encode()).hexdigest()
        if h not in seen:
            seen.add(h)
            result.append(msg)
    return result


def _merge_same_role(messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """Merge consecutive messages from the same role into one."""
    if not messages:
        return messages

    merged = [messages[0].copy()]
    for msg in messages[1:]:
        if msg.get("role") == merged[-1].get("role"):
            merged[-1]["content"] = merged[-1].get("content", "") + "\n" + msg.get("content", "")
        else:
            merged.append(msg.copy())
    return merged


def _coalesce_system(messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """Combine multiple system messages into a single one at the start."""
    system_parts = []
    non_system = []
    for msg in messages:
        if msg.get("role") == "system":
            content = msg.get("content", "").strip()
            if content:
                system_parts.append(content)
        else:
            non_system.append(msg)

    result = []
    if system_parts:
        result.append({"role": "system", "content": "\n".join(system_parts)})
    result.extend(non_system)
    return result


def _summarize_older(
    messages: List[Dict[str, str]],
    keep_last_n: int,
    max_chars: int,
) -> List[Dict[str, str]]:
    """Collapse older messages into a brief context summary.

    Keeps the last `keep_last_n` messages verbatim and replaces
    everything before them with a concise "[Prior conversation context]".
    """
    if len(messages) <= keep_last_n:
        return messages

    # Separate system messages (always preserved)
    system_msgs = [m for m in messages if m.get("role") == "system"]
    non_system = [m for m in messages if m.get("role") != "system"]

    if len(non_system) <= keep_last_n:
        return messages

    older = non_system[:-keep_last_n]
    recent = non_system[-keep_last_n:]

    # Build summary of older messages — use full content (no per-message truncation) so summarise has accurate input
    summary_parts = []
    for msg in older:
        role = msg.get("role", "?")[0].upper()
        content = (msg.get("content", "") or "").strip()
        summary_parts.append(f"{role}: {content}")

    summary_text = "\n\n".join(summary_parts)
    if len(summary_text) > max_chars:
        summary_text = summary_text[: max_chars - 3] + "..."

    result = list(system_msgs)
    result.append({"role": "system", "content": f"[Prior conversation context: {summary_text}]"})
    result.extend(recent)
    return result


def _hard_truncate(
    messages: List[Dict[str, str]],
    max_chars: int,
) -> List[Dict[str, str]]:
    """Hard-truncate to fit within max_chars total content.

    Preserves system messages and the last non-system message.
    Trims from the oldest non-system messages first.
    """

    def _total_chars(msgs):
        return sum(len(m.get("content", "")) for m in msgs)

    if _total_chars(messages) <= max_chars:
        return messages

    system = [m for m in messages if m.get("role") == "system"]
    non_system = [m for m in messages if m.get("role") != "system"]

    if not non_system:
        return messages

    last_msg = non_system[-1]
    middle = non_system[:-1]

    system_chars = _total_chars(system)
    last_chars = len(last_msg.get("content", ""))
    budget = max_chars - system_chars - last_chars

    if budget <= 0:
        # Can't even fit system + last message — truncate last message
        truncated = last_msg.get("content", "")[: max_chars - system_chars]
        return system + [{"role": last_msg["role"], "content": truncated}]

    # Keep as many middle messages as fit (most recent first)
    kept_middle = []
    used = 0
    for msg in reversed(middle):
        msg_chars = len(msg.get("content", ""))
        if used + msg_chars <= budget:
            kept_middle.insert(0, msg)
            used += msg_chars
        else:
            break

    return system + kept_middle + [last_msg]


# =========================================================================
# MAIN PIPELINE
# =========================================================================


def compact_messages(
    messages: List[Dict[str, str]],
    config: Optional[CompactConfig] = None,
) -> Tuple[List[Dict[str, str]], Dict[str, Any]]:
    """Apply the full compaction pipeline to a conversation.

    Returns (compacted_messages, stats_dict).
    """
    if config is None:
        config = CompactConfig()

    start = time.time()
    original_chars = sum(len(m.get("content", "")) for m in messages)
    original_count = len(messages)
    stages_applied = []
    result = [m.copy() for m in messages]

    # Stage 1: Deduplicate
    if config.deduplicate:
        before = len(result)
        result = _deduplicate(result)
        if len(result) < before:
            stages_applied.append(f"dedup: {before} -> {len(result)} msgs")

    # Stage 2: Coalesce system messages
    system_count = sum(1 for m in result if m.get("role") == "system")
    if system_count > 1:
        result = _coalesce_system(result)
        stages_applied.append(f"system_coalesce: {system_count} -> 1")

    # Stage 3: Merge consecutive same-role
    if config.merge_same_role:
        before = len(result)
        result = _merge_same_role(result)
        if len(result) < before:
            stages_applied.append(f"merge_roles: {before} -> {len(result)} msgs")

    # Stage 4: Normalize whitespace
    if config.normalize_whitespace:
        for msg in result:
            if msg.get("role") != "system" or not config.protect_system:
                msg["content"] = _normalize_whitespace(msg.get("content", ""))

    # Stage 5: Compress text (remove filler)
    if config.compress_text:
        chars_before = sum(len(m.get("content", "")) for m in result)
        for msg in result:
            if msg.get("role") != "system" or not config.protect_system:
                msg["content"] = _compress_text(msg.get("content", ""))
        chars_after = sum(len(m.get("content", "")) for m in result)
        saved = chars_before - chars_after
        if saved > 0:
            stages_applied.append(f"compress: saved {saved} chars")

    # Stage 6: Summarize older messages
    if config.summarize_older and len(result) > config.keep_last_n:
        before_count = len(result)
        result = _summarize_older(
            result,
            keep_last_n=config.keep_last_n,
            max_chars=config.summary_max_chars,
        )
        stages_applied.append(f"summarize: {before_count} -> {len(result)} msgs (kept last {config.keep_last_n})")

    # Stage 7: Hard truncate to context window (tokens -> chars directly)
    if config.target_ctx_tokens > 0:
        max_chars = int(config.target_ctx_tokens * config.chars_per_token)
        chars_before = sum(len(m.get("content", "")) for m in result)
        result = _hard_truncate(result, max_chars=max_chars)
        chars_after = sum(len(m.get("content", "")) for m in result)
        if chars_after < chars_before:
            stages_applied.append(
                f"truncate: {chars_before} -> {chars_after} chars (fit {config.target_ctx_tokens} tokens)"
            )

    # Stage 8: Max total chars limit (if set)
    if config.max_total_chars > 0:
        chars_before = sum(len(m.get("content", "")) for m in result)
        result = _hard_truncate(result, max_chars=config.max_total_chars)
        chars_after = sum(len(m.get("content", "")) for m in result)
        if chars_after < chars_before:
            stages_applied.append(f"max_chars: {chars_before} -> {chars_after} chars")

    # Compute stats
    final_chars = sum(len(m.get("content", "")) for m in result)
    elapsed_ms = (time.time() - start) * 1000
    est_original = max(1, int(original_chars / config.chars_per_token))
    est_final = max(1, int(final_chars / config.chars_per_token))
    ratio = est_final / est_original if est_original > 0 else 1.0
    reduction = 1.0 - ratio

    stats = {
        "original_messages": original_count,
        "compacted_messages": len(result),
        "original_chars": original_chars,
        "compacted_chars": final_chars,
        "original_tokens_est": est_original,
        "compacted_tokens_est": est_final,
        "reduction_ratio": round(reduction, 3),
        "compression_factor": f"{1 / ratio:.1f}x" if ratio > 0 else "inf",
        "stages_applied": stages_applied,
        "elapsed_ms": round(elapsed_ms, 2),
    }

    if stages_applied:
        logger.info(
            f"[compact] {original_count} msgs -> {len(result)} msgs, "
            f"{est_original} -> {est_final} tokens "
            f"({stats['compression_factor']} reduction) in {elapsed_ms:.1f}ms"
        )

    return result, stats


# =========================================================================
# CONVENIENCE
# =========================================================================


def compact_for_inference(
    messages: List[Dict[str, str]],
    *,
    keep_last_n: int = 4,
    target_tokens: int = 4096,
) -> List[Dict[str, str]]:
    """Quick compact for use inside inference handlers. Returns messages only."""
    cfg = CompactConfig(
        keep_last_n=keep_last_n,
        target_ctx_tokens=target_tokens,
    )
    compacted, _ = compact_messages(messages, cfg)
    return compacted
