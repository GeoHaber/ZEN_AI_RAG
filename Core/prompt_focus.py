"""
Core/prompt_focus.py — Focus-Mode Prompt Injection for Small LLMs

Constrains and focuses the LLM (especially ≤13B models via llama.cpp)
toward specific data-understanding tasks by injecting:

  1. **System prompt** (BEFORE the user query) — sets persona + output rules
  2. **Query wrapper** (AROUND the user query) — tells the LLM *how* to
     process the retrieved RAG context for this specific task

Design principles for small-model effectiveness:
  - System prompts ≤ 200 tokens (longer → coherence loss)
  - Imperative verbs: "Extract", "List", "Compare" (not soft requests)
  - Explicit format constraints: "Output as: ..."
  - Negative constraints: "Do NOT ..." (prevents rambling)
  - Language-aware: responds in user's language

Usage:
    from Core.prompt_focus import FocusMode, get_focus_config, apply_focus

    # Get all available modes for UI dropdown
    modes = FocusMode.choices()

    # Apply focus to a user query before sending to LLM
    system_prompt, wrapped_query = apply_focus(
        FocusMode.DATA_EXTRACTION, user_query, language="en"
    )

    # Use a template from the example library
    from Core.prompt_focus import PromptTemplateLibrary
    lib = PromptTemplateLibrary()
    templates = lib.list_templates()            # all built-in + custom
    tpl = lib.get_template("medical_symptoms")  # grab a specific one
    system, query = lib.apply_template("medical_symptoms", user_query)

    # Create your own custom prompt
    lib.save_custom(
        name="my_legal_prompt",
        system_prompt="You are a legal analyst. ...",
        query_prefix="ANALYZE the legal implications of: ",
        query_suffix="\\nList each legal risk with severity.",
        temperature=0.2,
        icon="⚖️",
        description="Legal risk analysis from documents",
        category="Legal",
    )
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ─── Focus Modes ───────────────────────────────────────────────────────────


class FocusMode(str, Enum):
    """Available LLM focus modes for data understanding tasks."""

    GENERAL = "general"
    DATA_EXTRACTION = "data_extraction"
    SUMMARIZATION = "summarization"
    COMPARISON = "comparison"
    FACT_CHECK = "fact_check"
    TIMELINE = "timeline"
    DEEP_ANALYSIS = "deep_analysis"

    @classmethod
    def choices(cls) -> List[Tuple[str, str, str]]:
        """Return (value, icon, label) tuples for UI dropdowns."""
        return [
            (cls.GENERAL.value, "💬", "General Assistant"),
            (cls.DATA_EXTRACTION.value, "📊", "Data Extraction"),
            (cls.SUMMARIZATION.value, "📝", "Summarization"),
            (cls.COMPARISON.value, "⚖️", "Comparison"),
            (cls.FACT_CHECK.value, "✅", "Fact Checking"),
            (cls.TIMELINE.value, "📅", "Timeline Builder"),
            (cls.DEEP_ANALYSIS.value, "🔬", "Deep Analysis"),
        ]

    @classmethod
    def from_string(cls, value: str) -> "FocusMode":
        """Safe conversion from string, defaults to GENERAL."""
        try:
            return cls(value)
        except ValueError:
            return cls.GENERAL


# ─── Prompt Configuration ──────────────────────────────────────────────────


@dataclass(frozen=True)
class FocusConfig:
    """Immutable configuration for a single focus mode.

    Attributes:
        mode:           The FocusMode enum value
        icon:           Emoji icon for UI display
        label:          Human-readable label
        system_prompt:  Injected as the system message (persona + rules)
        query_prefix:   Prepended to the user query (task directive)
        query_suffix:   Appended after the user query (output format)
        temperature:    Suggested temperature override (None = use default)
        description:    Short help text for the UI tooltip
    """

    mode: FocusMode
    icon: str
    label: str
    system_prompt: str
    query_prefix: str = ""
    query_suffix: str = ""
    temperature: Optional[float] = None
    description: str = ""


# ─── The Prompt Library ────────────────────────────────────────────────────
# Each prompt is carefully tuned for ≤13B parameter models:
#   • Short system prompts (≤150 tokens) to stay in working memory
#   • Imperative verbs for clear instruction following
#   • Format constraints to force structured output
#   • Negative constraints to prevent common failure modes

_FOCUS_CONFIGS: Dict[FocusMode, FocusConfig] = {
    FocusMode.GENERAL: FocusConfig(
        mode=FocusMode.GENERAL,
        icon="💬",
        label="General Assistant",
        system_prompt=(
            "You are a helpful assistant. Answer questions clearly and concisely "
            "using the provided context. Cite sources. Respond in the user's language."
        ),
        description="Default mode — balanced, clear answers with source citations.",
    ),
    FocusMode.DATA_EXTRACTION: FocusConfig(
        mode=FocusMode.DATA_EXTRACTION,
        icon="📊",
        label="Data Extraction",
        system_prompt=(
            "You are a precise data extraction engine. Your ONLY job is to extract "
            "structured facts from documents. Output ONLY data — no commentary, "
            "no opinions, no filler. Use tables or bullet lists. "
            "If a value is missing, write 'N/A'. Respond in the user's language."
        ),
        query_prefix="EXTRACT all facts, numbers, dates, names, and entities from the context below.\n\n",
        query_suffix=(
            "\n\nOUTPUT FORMAT: Structured list or markdown table. "
            "Each item must cite its source. Do NOT add interpretation."
        ),
        temperature=0.1,  # Low creativity = precise extraction
        description="Extract structured data: facts, numbers, dates, names. Outputs tables/lists.",
    ),
    FocusMode.SUMMARIZATION: FocusConfig(
        mode=FocusMode.SUMMARIZATION,
        icon="📝",
        label="Summarization",
        system_prompt=(
            "You are a concise summarizer. Compress information into the fewest "
            "possible words without losing meaning. No filler, no repetition. "
            "Use bullet points. Every bullet must add NEW information. "
            "Respond in the user's language."
        ),
        query_prefix="SUMMARIZE the key information relevant to this question:\n\n",
        query_suffix=(
            "\n\nOUTPUT: Maximum 7 bullet points. Start each with the most important word. "
            "Do NOT repeat any fact. Cite source numbers."
        ),
        temperature=0.3,
        description="Compress documents into ≤7 key bullet points. No filler.",
    ),
    FocusMode.COMPARISON: FocusConfig(
        mode=FocusMode.COMPARISON,
        icon="⚖️",
        label="Comparison",
        system_prompt=(
            "You are an analytical comparator. Your job is to find similarities "
            "and differences between entities, claims, or data points in the documents. "
            "Always use a structured comparison format. Be objective — no opinions. "
            "Respond in the user's language."
        ),
        query_prefix="COMPARE the entities or claims related to this question:\n\n",
        query_suffix=(
            "\n\nOUTPUT FORMAT:\n"
            "• **Similarities:** (bullet list)\n"
            "• **Differences:** (bullet list or comparison table)\n"
            "• **Key Insight:** (one sentence)\n"
            "Cite sources for each point."
        ),
        temperature=0.3,
        description="Compare/contrast entities, claims, or data points. Outputs structured differences.",
    ),
    FocusMode.FACT_CHECK: FocusConfig(
        mode=FocusMode.FACT_CHECK,
        icon="✅",
        label="Fact Checking",
        system_prompt=(
            "You are a rigorous fact-checker. For each claim in the query, determine "
            "if the documents SUPPORT, CONTRADICT, or are INSUFFICIENT to verify it. "
            "Quote the exact evidence. Flag any contradictions between sources. "
            "Respond in the user's language."
        ),
        query_prefix="VERIFY the following against the provided documents:\n\n",
        query_suffix=(
            "\n\nOUTPUT FORMAT for each claim:\n"
            "• Claim: [statement]\n"
            "• Verdict: ✅ Supported / ❌ Contradicted / ⚠️ Insufficient evidence\n"
            "• Evidence: [exact quote from source]\n"
            "• Source: [source number]\n"
            "Flag any contradictions between different sources."
        ),
        temperature=0.1,  # Precision is critical
        description="Verify claims against documents. Outputs verdicts with evidence.",
    ),
    FocusMode.TIMELINE: FocusConfig(
        mode=FocusMode.TIMELINE,
        icon="📅",
        label="Timeline Builder",
        system_prompt=(
            "You are a chronological analyst. Extract events with dates/times "
            "from documents and arrange them in order. If exact dates are missing, "
            "use relative ordering (before/after). Focus on temporal relationships. "
            "Respond in the user's language."
        ),
        query_prefix="EXTRACT all events and dates related to:\n\n",
        query_suffix=(
            "\n\nOUTPUT FORMAT:\n"
            "📅 [Date/Period] — [Event description] (Source [N])\n"
            "List chronologically, oldest first. "
            "If dates are uncertain, mark with '~' (approximate)."
        ),
        temperature=0.2,
        description="Build chronological timelines from document events. Oldest-first ordering.",
    ),
    FocusMode.DEEP_ANALYSIS: FocusConfig(
        mode=FocusMode.DEEP_ANALYSIS,
        icon="🔬",
        label="Deep Analysis",
        system_prompt=(
            "You are an analytical reasoning engine. Go beyond surface facts — "
            "identify patterns, correlations, causal relationships, and implications. "
            "Distinguish between what the data SHOWS vs what it SUGGESTS. "
            "Be precise about confidence levels. Respond in the user's language."
        ),
        query_prefix="ANALYZE the following in depth using the provided documents:\n\n",
        query_suffix=(
            "\n\nOUTPUT STRUCTURE:\n"
            "1. **Key Findings:** (what the data directly shows)\n"
            "2. **Patterns:** (recurring themes, correlations)\n"
            "3. **Implications:** (what this suggests, with confidence level)\n"
            "4. **Gaps:** (what data is missing for a complete analysis)\n"
            "Cite sources throughout."
        ),
        temperature=0.5,  # Allow some creative reasoning
        description="Deep causal analysis: patterns, correlations, implications, gaps.",
    ),
}


# ─── Public API ────────────────────────────────────────────────────────────


def get_focus_config(mode: FocusMode) -> FocusConfig:
    """Get the configuration for a focus mode."""
    return _FOCUS_CONFIGS.get(mode, _FOCUS_CONFIGS[FocusMode.GENERAL])


def get_all_configs() -> Dict[FocusMode, FocusConfig]:
    """Get all focus mode configurations (for UI listing)."""
    return dict(_FOCUS_CONFIGS)


def apply_focus(
    mode: FocusMode,
    user_query: str,
    existing_system_prompt: Optional[str] = None,
) -> Tuple[str, str]:
    """Apply focus mode to a query.

    Returns:
        (system_prompt, wrapped_query) — ready to send to the LLM.

    The system_prompt REPLACES the default one (not appends) because small
    models get confused by contradictory instructions. The wrapped_query
    is the user query with task-specific prefix/suffix.

    If mode is GENERAL, returns the existing_system_prompt unchanged
    and the query unmodified (backwards compatible).
    """
    config = get_focus_config(mode)

    # ── System prompt ──
    if mode == FocusMode.GENERAL and existing_system_prompt:
        system_prompt = existing_system_prompt
    else:
        system_prompt = config.system_prompt

    # ── Wrapped query ──
    if config.query_prefix or config.query_suffix:
        wrapped_query = f"{config.query_prefix}{user_query}{config.query_suffix}"
    else:
        wrapped_query = user_query

    if mode != FocusMode.GENERAL:
        logger.info(
            f"[PromptFocus] Mode={mode.value}, "
            f"system={len(system_prompt)} chars, "
            f"query={len(user_query)}→{len(wrapped_query)} chars"
        )

    return system_prompt, wrapped_query


def get_suggested_temperature(mode: FocusMode) -> Optional[float]:
    """Get the suggested temperature for a mode, or None for default."""
    config = get_focus_config(mode)
    return config.temperature


def get_mode_description(mode: FocusMode) -> str:
    """Get the help text for a mode."""
    config = get_focus_config(mode)
    return config.description


def get_mode_icon(mode: FocusMode) -> str:
    """Get the icon for a mode."""
    config = get_focus_config(mode)
    return config.icon


# ═══════════════════════════════════════════════════════════════════════════
# Prompt Template Library  — ready-to-use examples + user customs
# ═══════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class PromptTemplate:
    """A reusable prompt template (built-in or user-created).

    Each template follows the Small-LLM Design Rules:
      ✓ System prompt ≤ 200 tokens
      ✓ Imperative verbs ("Extract", "List", "Compare")
      ✓ Format constraints ("Output as: ...")
      ✓ Negative constraints ("Do NOT ...")
    """

    name: str  # unique slug  e.g. "medical_symptoms"
    label: str  # display name e.g. "Medical Symptoms"
    icon: str  # emoji
    category: str  # grouping: "Medical", "Legal", "Business", etc.
    system_prompt: str
    query_prefix: str = ""
    query_suffix: str = ""
    temperature: float = 0.3
    description: str = ""
    is_builtin: bool = True  # False for user-created
    example_query: str = ""  # sample question for the UI "Try this" button

    def to_dict(self) -> Dict[str, Any]:
        """Serialize for JSON persistence."""
        return {
            "name": self.name,
            "label": self.label,
            "icon": self.icon,
            "category": self.category,
            "system_prompt": self.system_prompt,
            "query_prefix": self.query_prefix,
            "query_suffix": self.query_suffix,
            "temperature": self.temperature,
            "description": self.description,
            "is_builtin": self.is_builtin,
            "example_query": self.example_query,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "PromptTemplate":
        """Deserialize from JSON."""
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# ─── Built-in Example Templates ───────────────────────────────────────────
# Each one demonstrates the 4 design rules for small LLMs.
# Users can browse these, use them as-is, or clone + edit.

_BUILTIN_TEMPLATES: Dict[str, PromptTemplate] = {}


def _register(tpl: PromptTemplate) -> PromptTemplate:
    _BUILTIN_TEMPLATES[tpl.name] = tpl
    return tpl


# ── Medical ────────────────────────────────────────────────────────────────

_register(
    PromptTemplate(
        name="medical_symptoms",
        label="Symptom Extractor",
        icon="🩺",
        category="Medical",
        system_prompt=(
            "You are a medical data extractor. Extract symptoms, diagnoses, "
            "medications, dosages, and lab values from clinical documents. "
            "Output as structured lists. Do NOT provide medical advice. "
            "Respond in the user's language."
        ),
        query_prefix="EXTRACT all clinical data related to:\n\n",
        query_suffix=(
            "\n\nOUTPUT FORMAT:\n"
            "• Symptoms: [list]\n• Diagnoses: [list]\n"
            "• Medications: [drug — dose — frequency]\n"
            "• Lab Values: [test — value — reference range]\n"
            "Mark uncertain items with '?'. Cite source numbers."
        ),
        temperature=0.1,
        description="Extract symptoms, meds, diagnoses, lab values from clinical docs.",
        example_query="What symptoms and medications are mentioned for the patient?",
    )
)

_register(
    PromptTemplate(
        name="medical_contraindications",
        label="Contraindication Checker",
        icon="⚠️",
        category="Medical",
        system_prompt=(
            "You are a pharmacovigilance analyst. Cross-reference medications, "
            "conditions, and allergies in the documents to identify potential "
            "contraindications and interactions. Be precise — cite evidence. "
            "Do NOT guess. Respond in the user's language."
        ),
        query_prefix="CHECK for contraindications and drug interactions:\n\n",
        query_suffix=(
            "\n\nOUTPUT:\n"
            "• ⚠️ [Drug A] + [Drug B/Condition]: [Risk] (Source [N])\n"
            "• ✅ No issues found for: [list]\n"
            "If insufficient data, state 'Insufficient evidence'."
        ),
        temperature=0.1,
        description="Find drug interactions and contraindications across documents.",
        example_query="Are there any drug interactions for this patient's medications?",
    )
)

# ── Legal / Compliance ─────────────────────────────────────────────────────

_register(
    PromptTemplate(
        name="legal_risk",
        label="Legal Risk Scanner",
        icon="⚖️",
        category="Legal",
        system_prompt=(
            "You are a legal risk analyst. Identify legal obligations, risks, "
            "deadlines, and liability clauses in documents. Focus on actionable "
            "items. Do NOT provide legal advice — flag items for human review. "
            "Respond in the user's language."
        ),
        query_prefix="IDENTIFY all legal risks and obligations related to:\n\n",
        query_suffix=(
            "\n\nOUTPUT:\n"
            "• 🔴 High Risk: [description] (Source [N])\n"
            "• 🟡 Medium Risk: [description]\n"
            "• 📅 Deadline: [date — action required]\n"
            "• 📋 Obligation: [what — who — when]\n"
            "Flag ambiguous clauses for human review."
        ),
        temperature=0.2,
        description="Scan documents for legal risks, deadlines, obligations.",
        example_query="What are the key legal risks and deadlines in this contract?",
    )
)

_register(
    PromptTemplate(
        name="compliance_audit",
        label="Compliance Auditor",
        icon="📋",
        category="Legal",
        system_prompt=(
            "You are a compliance auditor. Check documents against regulations "
            "and policies. For each requirement, determine: Compliant, "
            "Non-Compliant, or Partially Compliant. Cite the specific clause. "
            "Do NOT assume compliance — evidence required. Respond in the user's language."
        ),
        query_prefix="AUDIT compliance for:\n\n",
        query_suffix=(
            "\n\nOUTPUT:\n"
            "• ✅ Compliant: [requirement] — Evidence: [quote]\n"
            "• ❌ Non-Compliant: [requirement] — Gap: [what's missing]\n"
            "• ⚠️ Partial: [requirement] — Missing: [specifics]\n"
            "Summary: X/Y requirements met."
        ),
        temperature=0.1,
        description="Audit documents for regulatory compliance with verdicts.",
        example_query="Does this policy comply with GDPR data handling requirements?",
    )
)

# ── Business / Finance ─────────────────────────────────────────────────────

_register(
    PromptTemplate(
        name="financial_numbers",
        label="Financial Data Miner",
        icon="💰",
        category="Business",
        system_prompt=(
            "You are a financial data miner. Extract all monetary values, "
            "percentages, growth rates, revenue figures, and financial metrics. "
            "Output as tables when possible. Do NOT round numbers — exact values only. "
            "Respond in the user's language."
        ),
        query_prefix="EXTRACT all financial data related to:\n\n",
        query_suffix=(
            "\n\nOUTPUT FORMAT: Markdown table with columns:\n"
            "| Metric | Value | Period | Source |\n"
            "If trends exist, note direction (↑/↓/→). "
            "Do NOT calculate projections."
        ),
        temperature=0.1,
        description="Mine financial metrics: revenue, growth, percentages from reports.",
        example_query="What are the revenue figures and growth rates mentioned?",
    )
)

_register(
    PromptTemplate(
        name="meeting_actions",
        label="Meeting Action Items",
        icon="📌",
        category="Business",
        system_prompt=(
            "You are a meeting analyst. Extract action items, decisions, "
            "deadlines, and responsible parties from meeting notes. "
            "Be specific — WHO does WHAT by WHEN. Skip pleasantries. "
            "Respond in the user's language."
        ),
        query_prefix="EXTRACT all action items and decisions from:\n\n",
        query_suffix=(
            "\n\nOUTPUT:\n"
            "**Decisions Made:**\n• [decision] (decided by [who])\n\n"
            "**Action Items:**\n"
            "• [ ] [task] — Owner: [name] — Due: [date]\n\n"
            "**Open Questions:**\n• [question] — Assigned to: [name]"
        ),
        temperature=0.2,
        description="Pull action items, decisions, and deadlines from meeting notes.",
        example_query="What action items and deadlines came out of this meeting?",
    )
)

# ── Technical / Engineering ────────────────────────────────────────────────

_register(
    PromptTemplate(
        name="code_review",
        label="Code Review Analyst",
        icon="🔍",
        category="Technical",
        system_prompt=(
            "You are a code review analyst. Identify bugs, security issues, "
            "performance problems, and code smells in the provided code. "
            "Rate severity: Critical, Warning, Info. Suggest fixes briefly. "
            "Do NOT rewrite entire functions. Respond in the user's language."
        ),
        query_prefix="REVIEW the following code for issues:\n\n",
        query_suffix=(
            "\n\nOUTPUT for each issue:\n"
            "• [🔴/🟡/🔵] Line ~N: [Issue type] — [Description]\n"
            "  Fix: [one-line suggestion]\n\n"
            "Summary: X critical, Y warnings, Z info."
        ),
        temperature=0.2,
        description="Find bugs, security issues, and code smells with severity ratings.",
        example_query="Review this code for bugs and security vulnerabilities.",
    )
)

_register(
    PromptTemplate(
        name="api_documentation",
        label="API Doc Generator",
        icon="📖",
        category="Technical",
        system_prompt=(
            "You are an API documentation writer. Generate clear, structured "
            "API documentation from code or specs. Include endpoints, parameters, "
            "response formats, and examples. Be concise. "
            "Do NOT add unverified information. Respond in the user's language."
        ),
        query_prefix="DOCUMENT the API described in:\n\n",
        query_suffix=(
            "\n\nOUTPUT FORMAT per endpoint:\n"
            "### [METHOD] /path\n"
            "**Description:** ...\n"
            "**Parameters:** | Name | Type | Required | Description |\n"
            "**Response:** ```json { ... } ```\n"
            "**Example:** curl command"
        ),
        temperature=0.2,
        description="Generate structured API documentation from code or specs.",
        example_query="Document the endpoints described in this specification.",
    )
)

# ── Research / Academic ────────────────────────────────────────────────────

_register(
    PromptTemplate(
        name="literature_review",
        label="Literature Reviewer",
        icon="📚",
        category="Research",
        system_prompt=(
            "You are a research literature analyst. Identify key findings, "
            "methodologies, sample sizes, and conclusions from academic papers. "
            "Note limitations and conflicting results between studies. "
            "Do NOT overstate findings. Respond in the user's language."
        ),
        query_prefix="REVIEW the research literature on:\n\n",
        query_suffix=(
            "\n\nOUTPUT:\n"
            "• **Key Findings:** [finding] (Study: [author/source], N=[size])\n"
            "• **Methods Used:** [list]\n"
            "• **Conflicts:** [study A says X, study B says Y]\n"
            "• **Limitations:** [what's missing]\n"
            "• **Consensus:** [what most evidence supports]"
        ),
        temperature=0.3,
        description="Analyze research papers: findings, methods, conflicts, consensus.",
        example_query="What do the studies say about the effectiveness of this treatment?",
    )
)

_register(
    PromptTemplate(
        name="statistical_digest",
        label="Statistics Extractor",
        icon="📈",
        category="Research",
        system_prompt=(
            "You are a statistics extractor. Pull all statistical values: "
            "p-values, confidence intervals, effect sizes, sample sizes, "
            "correlations, and significance levels. Present in tables. "
            "Do NOT interpret — just extract. Respond in the user's language."
        ),
        query_prefix="EXTRACT all statistical values from:\n\n",
        query_suffix=(
            "\n\nOUTPUT: Markdown table:\n"
            "| Statistic | Value | Context | Significant? | Source |\n"
            "Flag any p-values > 0.05 with ⚠️. "
            "Do NOT add conclusions beyond what's stated."
        ),
        temperature=0.1,
        description="Pull p-values, effect sizes, CIs, and sample sizes into tables.",
        example_query="Extract all statistical results from these research documents.",
    )
)

# ── Data Quality / ETL ─────────────────────────────────────────────────────

_register(
    PromptTemplate(
        name="data_quality",
        label="Data Quality Inspector",
        icon="🔎",
        category="Data",
        system_prompt=(
            "You are a data quality inspector. Identify inconsistencies, "
            "missing values, format errors, duplicates, and outliers in data. "
            "Quantify each issue. Suggest specific fixes. "
            "Do NOT modify data — only report. Respond in the user's language."
        ),
        query_prefix="INSPECT data quality for:\n\n",
        query_suffix=(
            "\n\nOUTPUT:\n"
            "• 🔴 Critical: [issue] — Affected: [N rows/fields]\n"
            "• 🟡 Warning: [issue] — Fix: [suggestion]\n"
            "• 📊 Coverage: [X]% complete\n"
            "Summary: [overall quality score out of 10]"
        ),
        temperature=0.1,
        description="Detect data quality issues: gaps, duplicates, inconsistencies.",
        example_query="Check this dataset for missing values and inconsistencies.",
    )
)

_register(
    PromptTemplate(
        name="entity_mapper",
        label="Entity Relationship Mapper",
        icon="🗺️",
        category="Data",
        system_prompt=(
            "You are an entity-relationship extractor. Identify all entities "
            "(people, organizations, locations, products) and their relationships. "
            "Map connections between entities. Use short labels. "
            "Do NOT infer relationships not stated in documents. "
            "Respond in the user's language."
        ),
        query_prefix="MAP all entities and relationships in:\n\n",
        query_suffix=(
            "\n\nOUTPUT:\n"
            "**Entities:** [Name] (Type: Person/Org/Location/Product)\n"
            "**Relationships:**\n"
            "• [Entity A] → [relationship] → [Entity B] (Source [N])\n\n"
            "List strongest connections first."
        ),
        temperature=0.2,
        description="Extract people, orgs, locations and map their relationships.",
        example_query="Who are the key people and organizations mentioned, and how are they connected?",
    )
)


# ─── Custom Prompt Persistence ─────────────────────────────────────────────

_CUSTOM_PROMPTS_FILE = Path("data") / "custom_prompts.json"

# Small-LLM validation limits
_MAX_SYSTEM_PROMPT_TOKENS = 200  # ~150 words
_MAX_SYSTEM_PROMPT_CHARS = 800  # safety cap in characters


def _estimate_tokens(text: str) -> int:
    """Rough token estimate (≈ 0.75 words per token for English)."""
    return max(1, int(len(text.split()) / 0.75))


def validate_prompt(system_prompt: str) -> List[str]:
    """Validate a prompt against small-LLM design rules.

    Returns a list of warnings (empty = all good).
    These are advisory, not blocking — user can still save.
    """
    warnings: List[str] = []
    tokens = _estimate_tokens(system_prompt)

    if tokens > _MAX_SYSTEM_PROMPT_TOKENS:
        warnings.append(
            f"System prompt ~{tokens} tokens (recommended ≤{_MAX_SYSTEM_PROMPT_TOKENS}). "
            "Small models may lose coherence with long instructions."
        )

    if len(system_prompt) > _MAX_SYSTEM_PROMPT_CHARS:
        warnings.append(f"System prompt {len(system_prompt)} chars — consider trimming.")

    # Check for imperative verbs
    _IMPERATIVES = re.compile(
        r"\b(extract|list|compare|identify|find|check|analyze|verify|"
        r"summarize|output|determine|map|review|flag|cite|note)\b",
        re.IGNORECASE,
    )
    if not _IMPERATIVES.search(system_prompt):
        warnings.append(
            "No imperative verbs found. Small LLMs respond better to direct commands like 'Extract', 'List', 'Compare'."
        )

    # Check for format constraint
    if not re.search(r"(output|format|respond|structure)", system_prompt, re.IGNORECASE):
        warnings.append(
            "No format constraint detected. Add 'Output as: ...' to force structured responses from small models."
        )

    # Check for negative constraint
    if not re.search(r"(do not|don\'t|never|avoid|skip)", system_prompt, re.IGNORECASE):
        warnings.append(
            "No negative constraint. Adding 'Do NOT ...' prevents the #1 small-LLM failure: rambling off-topic."
        )

    return warnings


class PromptTemplateLibrary:
    """Manages both built-in templates and user-created custom prompts.

    Built-in templates are read-only examples. Users can:
    1. Use them as-is  (apply_template)
    2. Clone + edit them  (clone_as_custom)
    3. Create from scratch  (save_custom)
    4. Delete custom ones  (delete_custom)

    Custom prompts are persisted to data/custom_prompts.json.
    """

    def __init__(self, storage_dir: Optional[Path] = None):
        self._builtins = dict(_BUILTIN_TEMPLATES)
        self._customs: Dict[str, PromptTemplate] = {}
        self._storage = storage_dir or _CUSTOM_PROMPTS_FILE
        self._load_customs()

    # ── Listing ───────────────────────────────────────────────────────

    def list_templates(
        self,
        category: Optional[str] = None,
        include_builtins: bool = True,
        include_customs: bool = True,
    ) -> List[PromptTemplate]:
        """List templates, optionally filtered by category."""
        result = []
        if include_builtins:
            result.extend(self._builtins.values())
        if include_customs:
            result.extend(self._customs.values())
        if category:
            result = [t for t in result if t.category.lower() == category.lower()]
        return sorted(result, key=lambda t: (t.category, t.label))

    def list_categories(self) -> List[str]:
        """List unique categories across all templates."""
        cats = set()
        for t in self._builtins.values():
            cats.add(t.category)
        for t in self._customs.values():
            cats.add(t.category)
        return sorted(cats)

    def get_template(self, name: str) -> Optional[PromptTemplate]:
        """Get a template by name (checks customs first, then builtins)."""
        return self._customs.get(name) or self._builtins.get(name)

    @property
    def builtin_count(self) -> int:
        return len(self._builtins)

    @property
    def custom_count(self) -> int:
        return len(self._customs)

    # ── Apply ─────────────────────────────────────────────────────────

    def apply_template(
        self,
        name: str,
        user_query: str,
    ) -> Tuple[str, str]:
        """Apply a template to a query. Returns (system_prompt, wrapped_query)."""
        tpl = self.get_template(name)
        if not tpl:
            logger.warning(f"[PromptTemplateLibrary] Unknown template '{name}', using passthrough")
            return "", user_query

        wrapped = user_query
        if tpl.query_prefix or tpl.query_suffix:
            wrapped = f"{tpl.query_prefix}{user_query}{tpl.query_suffix}"

        logger.info(f"[PromptTemplate] Applied '{name}' ({tpl.category}), query {len(user_query)}→{len(wrapped)} chars")
        return tpl.system_prompt, wrapped

    # ── Custom CRUD ───────────────────────────────────────────────────

    def save_custom(
        self,
        name: str,
        label: str,
        system_prompt: str,
        category: str = "Custom",
        icon: str = "✏️",
        query_prefix: str = "",
        query_suffix: str = "",
        temperature: float = 0.3,
        description: str = "",
        example_query: str = "",
    ) -> Tuple[PromptTemplate, List[str]]:
        """Create or update a custom prompt template.

        Returns:
            (template, warnings) — warnings are advisory from validate_prompt.
        """
        # Sanitize name to slug
        slug = re.sub(r"[^a-z0-9_]", "_", name.lower().strip())
        if not slug:
            slug = "custom_prompt"

        # Prevent overwriting builtins
        if slug in self._builtins:
            slug = f"custom_{slug}"

        warnings = validate_prompt(system_prompt)

        tpl = PromptTemplate(
            name=slug,
            label=label,
            icon=icon,
            category=category,
            system_prompt=system_prompt,
            query_prefix=query_prefix,
            query_suffix=query_suffix,
            temperature=temperature,
            description=description,
            is_builtin=False,
            example_query=example_query,
        )
        self._customs[slug] = tpl
        self._save_customs()

        logger.info(f"[PromptTemplateLibrary] Saved custom template '{slug}' ({category})")
        return tpl, warnings

    def delete_custom(self, name: str) -> bool:
        """Delete a custom template. Returns True if deleted."""
        if name in self._customs:
            del self._customs[name]
            self._save_customs()
            logger.info(f"[PromptTemplateLibrary] Deleted custom template '{name}'")
            return True
        return False

    def clone_as_custom(
        self,
        source_name: str,
        new_name: Optional[str] = None,
    ) -> Optional[PromptTemplate]:
        """Clone a built-in template as a custom one for editing."""
        source = self.get_template(source_name)
        if not source:
            return None

        slug = new_name or f"custom_{source.name}"
        slug = re.sub(r"[^a-z0-9_]", "_", slug.lower().strip())

        tpl = PromptTemplate(
            name=slug,
            label=f"{source.label} (Custom)",
            icon=source.icon,
            category=source.category,
            system_prompt=source.system_prompt,
            query_prefix=source.query_prefix,
            query_suffix=source.query_suffix,
            temperature=source.temperature,
            description=source.description,
            is_builtin=False,
            example_query=source.example_query,
        )
        self._customs[slug] = tpl
        self._save_customs()
        return tpl

    # ── Persistence ───────────────────────────────────────────────────

    def _load_customs(self) -> None:
        """Load custom prompts from disk."""
        try:
            if self._storage.exists():
                data = json.loads(self._storage.read_text(encoding="utf-8"))
                for entry in data:
                    try:
                        tpl = PromptTemplate.from_dict(entry)
                        self._customs[tpl.name] = tpl
                    except Exception as e:
                        logger.warning(f"[PromptTemplateLibrary] Skipping bad entry: {e}")
                logger.info(f"[PromptTemplateLibrary] Loaded {len(self._customs)} custom templates")
        except Exception as e:
            logger.warning(f"[PromptTemplateLibrary] Could not load customs: {e}")

    def _save_customs(self) -> None:
        """Persist custom prompts to disk."""
        try:
            self._storage.parent.mkdir(parents=True, exist_ok=True)
            data = [tpl.to_dict() for tpl in self._customs.values()]
            self._storage.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception as e:
            logger.error(f"[PromptTemplateLibrary] Save failed: {e}")


# ─── Module-level singleton ────────────────────────────────────────────────

_library_instance: Optional[PromptTemplateLibrary] = None


def get_template_library() -> PromptTemplateLibrary:
    """Get the singleton PromptTemplateLibrary instance."""
    global _library_instance
    if _library_instance is None:
        _library_instance = PromptTemplateLibrary()
    return _library_instance
