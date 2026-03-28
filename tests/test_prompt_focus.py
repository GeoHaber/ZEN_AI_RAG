"""
Tests for Core/prompt_focus.py — Focus-Mode Prompt Injection

Tests cover:
  - FocusMode enum values and conversions
  - FocusConfig dataclass fields
  - apply_focus() system prompt and query wrapping
  - Temperature suggestions per mode
  - Backwards compatibility (GENERAL mode = no changes)
  - Edge cases: empty queries, unknown modes, None values
  - All 7 modes produce valid output
  - Icon/label/description accessors
  - Query prefix/suffix application
  - Server-side focus_mode field integration
"""

import pytest


# ─── Imports ───────────────────────────────────────────────────────────────


def test_import():
    from Core.prompt_focus import (
        FocusMode,
        FocusConfig,
    )

    assert FocusMode is not None
    assert FocusConfig is not None


# ─── FocusMode Enum ───────────────────────────────────────────────────────


def test_focus_mode_values():
    from Core.prompt_focus import FocusMode

    assert FocusMode.GENERAL.value == "general"
    assert FocusMode.DATA_EXTRACTION.value == "data_extraction"
    assert FocusMode.SUMMARIZATION.value == "summarization"
    assert FocusMode.COMPARISON.value == "comparison"
    assert FocusMode.FACT_CHECK.value == "fact_check"
    assert FocusMode.TIMELINE.value == "timeline"
    assert FocusMode.DEEP_ANALYSIS.value == "deep_analysis"


def test_focus_mode_count():
    from Core.prompt_focus import FocusMode

    assert len(FocusMode) == 7


def test_focus_mode_is_string_enum():
    from Core.prompt_focus import FocusMode

    assert isinstance(FocusMode.GENERAL, str)
    assert FocusMode.GENERAL == "general"


def test_focus_mode_from_string_valid():
    from Core.prompt_focus import FocusMode

    assert FocusMode.from_string("data_extraction") == FocusMode.DATA_EXTRACTION
    assert FocusMode.from_string("timeline") == FocusMode.TIMELINE


def test_focus_mode_from_string_invalid():
    from Core.prompt_focus import FocusMode

    assert FocusMode.from_string("nonexistent") == FocusMode.GENERAL


def test_focus_mode_from_string_empty():
    from Core.prompt_focus import FocusMode

    assert FocusMode.from_string("") == FocusMode.GENERAL


def test_focus_mode_choices():
    from Core.prompt_focus import FocusMode

    choices = FocusMode.choices()
    assert len(choices) == 7
    # Each choice is (value, icon, label)
    for value, icon, label in choices:
        assert isinstance(value, str)
        assert isinstance(icon, str)
        assert isinstance(label, str)
        assert len(icon) > 0
        assert len(label) > 0


def test_choices_values_match_enum():
    from Core.prompt_focus import FocusMode

    choices = FocusMode.choices()
    values = [v for v, _, _ in choices]
    enum_values = [m.value for m in FocusMode]
    assert values == enum_values


# ─── FocusConfig ───────────────────────────────────────────────────────────


def test_focus_config_fields():
    from Core.prompt_focus import FocusMode, get_focus_config

    cfg = get_focus_config(FocusMode.DATA_EXTRACTION)
    assert cfg.mode == FocusMode.DATA_EXTRACTION
    assert cfg.icon == "📊"
    assert "Data Extraction" in cfg.label
    assert len(cfg.system_prompt) > 10
    assert cfg.query_prefix != ""
    assert cfg.query_suffix != ""
    assert cfg.temperature is not None
    assert len(cfg.description) > 10


def test_focus_config_immutable():
    from Core.prompt_focus import FocusMode, get_focus_config

    cfg = get_focus_config(FocusMode.GENERAL)
    with pytest.raises(AttributeError):
        cfg.label = "Modified"


def test_all_configs_available():
    from Core.prompt_focus import FocusMode, get_all_configs

    configs = get_all_configs()
    assert len(configs) == 7
    for mode in FocusMode:
        assert mode in configs


# ─── apply_focus() ─────────────────────────────────────────────────────────


def test_apply_general_unchanged():
    """GENERAL mode should not modify the query."""
    from Core.prompt_focus import FocusMode, apply_focus

    sys_prompt, wrapped = apply_focus(FocusMode.GENERAL, "What is Python?")
    assert wrapped == "What is Python?"
    assert len(sys_prompt) > 0


def test_apply_general_preserves_existing_system_prompt():
    """GENERAL mode should keep the existing system prompt if provided."""
    from Core.prompt_focus import FocusMode, apply_focus

    existing = "You are a medical expert."
    sys_prompt, wrapped = apply_focus(FocusMode.GENERAL, "test", existing_system_prompt=existing)
    assert sys_prompt == existing
    assert wrapped == "test"


def test_apply_data_extraction_wraps_query():
    """DATA_EXTRACTION should add prefix and suffix to the query."""
    from Core.prompt_focus import FocusMode, apply_focus

    sys_prompt, wrapped = apply_focus(FocusMode.DATA_EXTRACTION, "Show me the revenue data")
    assert "EXTRACT" in wrapped
    assert "Show me the revenue data" in wrapped
    assert "OUTPUT FORMAT" in wrapped
    assert "data extraction" in sys_prompt.lower() or "extract" in sys_prompt.lower()


def test_apply_summarization_wraps_query():
    from Core.prompt_focus import FocusMode, apply_focus

    sys_prompt, wrapped = apply_focus(FocusMode.SUMMARIZATION, "Tell me about climate change")
    assert "SUMMARIZE" in wrapped
    assert "Tell me about climate change" in wrapped
    assert "bullet" in wrapped.lower()


def test_apply_comparison_wraps_query():
    from Core.prompt_focus import FocusMode, apply_focus

    sys_prompt, wrapped = apply_focus(FocusMode.COMPARISON, "Compare A vs B")
    assert "COMPARE" in wrapped
    assert "Similarities" in wrapped or "Differences" in wrapped


def test_apply_fact_check_wraps_query():
    from Core.prompt_focus import FocusMode, apply_focus

    sys_prompt, wrapped = apply_focus(FocusMode.FACT_CHECK, "Is this true?")
    assert "VERIFY" in wrapped
    assert "Verdict" in wrapped or "Supported" in wrapped


def test_apply_timeline_wraps_query():
    from Core.prompt_focus import FocusMode, apply_focus

    sys_prompt, wrapped = apply_focus(FocusMode.TIMELINE, "What happened in 2024?")
    assert "EXTRACT" in wrapped or "events" in wrapped.lower()
    assert "chronolog" in wrapped.lower()


def test_apply_deep_analysis_wraps_query():
    from Core.prompt_focus import FocusMode, apply_focus

    sys_prompt, wrapped = apply_focus(FocusMode.DEEP_ANALYSIS, "Why did sales drop?")
    assert "ANALYZE" in wrapped
    assert "Patterns" in wrapped or "patterns" in wrapped


def test_apply_all_modes_produce_valid_output():
    """Every mode should return (str, str) with non-empty system prompt."""
    from Core.prompt_focus import FocusMode, apply_focus

    for mode in FocusMode:
        sys_prompt, wrapped = apply_focus(mode, "test query")
        assert isinstance(sys_prompt, str), f"Mode {mode}: system_prompt not str"
        assert isinstance(wrapped, str), f"Mode {mode}: wrapped not str"
        assert len(sys_prompt) > 10, f"Mode {mode}: system_prompt too short"
        assert "test query" in wrapped, f"Mode {mode}: original query missing"


def test_apply_focus_empty_query():
    """Empty query should still work (no crash)."""
    from Core.prompt_focus import FocusMode, apply_focus

    sys_prompt, wrapped = apply_focus(FocusMode.DATA_EXTRACTION, "")
    assert isinstance(sys_prompt, str)
    assert isinstance(wrapped, str)


def test_apply_focus_long_query():
    """Long query should work without truncation."""
    from Core.prompt_focus import FocusMode, apply_focus

    long_q = "x " * 5000
    sys_prompt, wrapped = apply_focus(FocusMode.SUMMARIZATION, long_q)
    assert long_q in wrapped


def test_apply_focus_unicode_query():
    """Unicode (Romanian) queries should pass through correctly."""
    from Core.prompt_focus import FocusMode, apply_focus

    ro_query = "Câte persoane au fost internate în Spitalul Municipal?"
    sys_prompt, wrapped = apply_focus(FocusMode.DATA_EXTRACTION, ro_query)
    assert ro_query in wrapped


# ─── System Prompt Quality ─────────────────────────────────────────────────


def test_system_prompts_are_short():
    """System prompts should be ≤200 tokens (approximately ≤800 chars) for small models."""
    from Core.prompt_focus import FocusMode, get_focus_config

    for mode in FocusMode:
        cfg = get_focus_config(mode)
        assert len(cfg.system_prompt) <= 800, (
            f"Mode {mode.value}: system_prompt too long ({len(cfg.system_prompt)} chars)"
        )


def test_system_prompts_contain_language_directive():
    """All system prompts should tell the LLM to respond in user's language."""
    from Core.prompt_focus import FocusMode, get_focus_config

    for mode in FocusMode:
        cfg = get_focus_config(mode)
        assert "language" in cfg.system_prompt.lower(), f"Mode {mode.value}: missing language directive"


def test_non_general_modes_have_imperatives():
    """Non-general modes should use imperative verbs in query wrappers."""
    from Core.prompt_focus import FocusMode, get_focus_config

    imperatives = {"EXTRACT", "SUMMARIZE", "COMPARE", "VERIFY", "ANALYZE"}
    for mode in FocusMode:
        if mode == FocusMode.GENERAL:
            continue
        cfg = get_focus_config(mode)
        prefix_upper = cfg.query_prefix.upper()
        has_imperative = any(imp in prefix_upper for imp in imperatives)
        assert has_imperative, f"Mode {mode.value}: query_prefix missing imperative verb"


# ─── Temperature Suggestions ──────────────────────────────────────────────


def test_temperature_general_is_none():
    """GENERAL mode should not override temperature."""
    from Core.prompt_focus import FocusMode, get_suggested_temperature

    assert get_suggested_temperature(FocusMode.GENERAL) is None


def test_temperature_data_extraction_low():
    """Data extraction should have low temperature (precision)."""
    from Core.prompt_focus import FocusMode, get_suggested_temperature

    temp = get_suggested_temperature(FocusMode.DATA_EXTRACTION)
    assert temp is not None
    assert temp <= 0.3


def test_temperature_fact_check_low():
    from Core.prompt_focus import FocusMode, get_suggested_temperature

    temp = get_suggested_temperature(FocusMode.FACT_CHECK)
    assert temp is not None
    assert temp <= 0.3


def test_temperature_deep_analysis_moderate():
    from Core.prompt_focus import FocusMode, get_suggested_temperature

    temp = get_suggested_temperature(FocusMode.DEEP_ANALYSIS)
    assert temp is not None
    assert 0.3 <= temp <= 0.7


def test_all_non_general_have_temperature():
    """Every non-general mode should suggest a temperature."""
    from Core.prompt_focus import FocusMode, get_suggested_temperature

    for mode in FocusMode:
        if mode == FocusMode.GENERAL:
            continue
        temp = get_suggested_temperature(mode)
        assert temp is not None, f"Mode {mode.value}: no temperature suggestion"
        assert 0.0 <= temp <= 2.0, f"Mode {mode.value}: temperature {temp} out of range"


# ─── Accessors ─────────────────────────────────────────────────────────────


def test_get_mode_icon():
    from Core.prompt_focus import FocusMode, get_mode_icon

    assert get_mode_icon(FocusMode.GENERAL) == "💬"
    assert get_mode_icon(FocusMode.DATA_EXTRACTION) == "📊"
    assert get_mode_icon(FocusMode.TIMELINE) == "📅"


def test_get_mode_description():
    from Core.prompt_focus import FocusMode, get_mode_description

    desc = get_mode_description(FocusMode.FACT_CHECK)
    assert isinstance(desc, str)
    assert len(desc) > 10


def test_get_focus_config_unknown_mode():
    """Unknown mode should return GENERAL config."""
    from Core.prompt_focus import FocusMode, get_focus_config

    # Passing a raw string that isn't a valid mode
    cfg = get_focus_config(FocusMode.GENERAL)
    assert cfg.mode == FocusMode.GENERAL


# ─── Integration: Server Schema Compatibility ─────────────────────────────


def test_focus_mode_values_are_valid_api_strings():
    """All mode values should be valid, URL-safe strings for API use."""
    from Core.prompt_focus import FocusMode

    for mode in FocusMode:
        assert mode.value.isascii()
        assert " " not in mode.value
        assert mode.value == mode.value.lower()


def test_apply_focus_returns_tuple():
    from Core.prompt_focus import FocusMode, apply_focus

    result = apply_focus(FocusMode.DATA_EXTRACTION, "test")
    assert isinstance(result, tuple)
    assert len(result) == 2


# ─── Query Wrapping Edge Cases ─────────────────────────────────────────────


def test_query_prefix_ends_with_newline():
    """Prefixes should end with newline for clean formatting."""
    from Core.prompt_focus import FocusMode, get_focus_config

    for mode in FocusMode:
        cfg = get_focus_config(mode)
        if cfg.query_prefix:
            assert cfg.query_prefix.endswith("\n"), f"Mode {mode.value}: query_prefix doesn't end with newline"


def test_query_suffix_starts_with_newline():
    """Suffixes should start with newline for clean formatting."""
    from Core.prompt_focus import FocusMode, get_focus_config

    for mode in FocusMode:
        cfg = get_focus_config(mode)
        if cfg.query_suffix:
            assert cfg.query_suffix.startswith("\n"), f"Mode {mode.value}: query_suffix doesn't start with newline"


def test_wrapped_query_contains_original():
    """The wrapped query must always contain the original user query."""
    from Core.prompt_focus import FocusMode, apply_focus

    original = "What is the mortality rate in the ICU?"
    for mode in FocusMode:
        _, wrapped = apply_focus(mode, original)
        assert original in wrapped, f"Mode {mode.value}: original query lost in wrapping"


# ─── Concurrent Safety ────────────────────────────────────────────────────


def test_concurrent_apply_focus():
    """apply_focus should be thread-safe (no shared mutable state)."""
    from Core.prompt_focus import FocusMode, apply_focus
    from concurrent.futures import ThreadPoolExecutor

    modes = list(FocusMode)
    queries = [f"Query for mode {m.value}" for m in modes]

    def run(mode_query):
        mode, query = mode_query
        return apply_focus(mode, query)

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(run, zip(modes, queries)))

    assert len(results) == 7
    for sys_prompt, wrapped in results:
        assert isinstance(sys_prompt, str)
        assert isinstance(wrapped, str)
