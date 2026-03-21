"""
Core/prompt_focus.py — Focus Modes & Prompt Template Library.

Focus Modes (7):
  General, Data Extraction, Summarization, Comparison,
  Fact Check, Timeline, Deep Analysis

Prompt Templates (12+ built-in):
  Medical (Symptoms, Contraindications), Legal (Risk, Compliance),
  Business (Financial, Meeting), Technical (Code Review, API Docs),
  Research (Literature, Statistics), Data (Quality, Entity Mapper)

Custom prompt CRUD with persistence to data/custom_prompts.json.

Ported from ZEN_RAG.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ─── Focus Modes ───────────────────────────────────────────────────────────


class FocusMode(str, Enum):
    GENERAL = "general"
    DATA_EXTRACTION = "data_extraction"
    SUMMARIZATION = "summarization"
    COMPARISON = "comparison"
    FACT_CHECK = "fact_check"
    TIMELINE = "timeline"
    DEEP_ANALYSIS = "deep_analysis"


@dataclass
class FocusConfig:
    """Configuration for a focus mode."""

    mode: FocusMode
    system_prompt_addition: str
    temperature: float = 0.7
    max_tokens: int = 1024
    description: str = ""

    def apply_to_prompt(self, base_prompt: str) -> str:
        """Prepend focus instructions to the base system prompt."""
        if self.system_prompt_addition:
            return f"{self.system_prompt_addition}\n\n{base_prompt}"
        return base_prompt


# Pre-built focus configs
FOCUS_CONFIGS: Dict[FocusMode, FocusConfig] = {
    FocusMode.GENERAL: FocusConfig(
        mode=FocusMode.GENERAL,
        system_prompt_addition="",
        temperature=0.7,
        description="Default mode — balanced answer generation.",
    ),
    FocusMode.DATA_EXTRACTION: FocusConfig(
        mode=FocusMode.DATA_EXTRACTION,
        system_prompt_addition=(
            "You are a precision data extractor. Extract ONLY factual data from the provided sources. "
            "Output as structured lists or tables. Do NOT add interpretation or commentary. "
            "If data is missing, say 'Not found in sources'."
        ),
        temperature=0.1,
        description="Extract structured data: numbers, dates, names, lists.",
    ),
    FocusMode.SUMMARIZATION: FocusConfig(
        mode=FocusMode.SUMMARIZATION,
        system_prompt_addition=(
            "You are a concise summarizer. Provide a clear, structured summary of the information. "
            "Use bullet points for key findings. Keep it brief — max 5-7 sentences for the main summary. "
            "Include a 'Key Takeaways' section at the end."
        ),
        temperature=0.3,
        description="Concise summaries with key takeaways.",
    ),
    FocusMode.COMPARISON: FocusConfig(
        mode=FocusMode.COMPARISON,
        system_prompt_addition=(
            "You are a comparison analyst. Compare items side-by-side using consistent criteria. "
            "Use tables when possible. Rate each item on relevant dimensions. "
            "End with a recommendation based on the evidence."
        ),
        temperature=0.3,
        description="Side-by-side comparison with structured criteria.",
    ),
    FocusMode.FACT_CHECK: FocusConfig(
        mode=FocusMode.FACT_CHECK,
        system_prompt_addition=(
            "You are a fact-checker. For each claim, determine: SUPPORTED, CONTRADICTED, or UNVERIFIABLE "
            "based on the provided sources. Cite the specific source for each verdict. "
            "Do NOT accept claims without evidence."
        ),
        temperature=0.1,
        description="Fact verification with source citations.",
    ),
    FocusMode.TIMELINE: FocusConfig(
        mode=FocusMode.TIMELINE,
        system_prompt_addition=(
            "You are a timeline analyst. Extract and organize all events chronologically. "
            "Format: [Date/Period] — [Event] (Source). "
            "Flag any date conflicts between sources."
        ),
        temperature=0.2,
        description="Chronological event extraction and ordering.",
    ),
    FocusMode.DEEP_ANALYSIS: FocusConfig(
        mode=FocusMode.DEEP_ANALYSIS,
        system_prompt_addition=(
            "You are a deep analysis expert. Provide comprehensive analysis covering: "
            "1) Background & Context, 2) Key Findings, 3) Evidence Assessment, "
            "4) Implications, 5) Limitations, 6) Conclusion. "
            "Cite sources for every claim. Be thorough but organized."
        ),
        temperature=0.5,
        max_tokens=2048,
        description="Comprehensive analysis with structured sections.",
    ),
}


# ─── Prompt Templates ──────────────────────────────────────────────────────


@dataclass
class PromptTemplate:
    """A reusable prompt template."""

    name: str
    label: str
    icon: str
    category: str
    system_prompt: str
    query_prefix: str = ""
    query_suffix: str = ""
    temperature: float = 0.3
    description: str = ""
    is_builtin: bool = True
    example_query: str = ""

    def to_dict(self) -> Dict[str, Any]:
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
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# ─── Built-in Template Registry ───────────────────────────────────────────

_BUILTIN_TEMPLATES: Dict[str, PromptTemplate] = {}


def _register(tpl: PromptTemplate):
    _BUILTIN_TEMPLATES[tpl.name] = tpl


# ── Medical ────────────────────────────────────────────────────────────────

_register(PromptTemplate(
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
))

_register(PromptTemplate(
    name="medical_contraindications",
    label="Contraindication Checker",
    icon="⚠️",
    category="Medical",
    system_prompt=(
        "You are a pharmacovigilance analyst. Cross-reference medications, "
        "conditions, and allergies to identify potential contraindications "
        "and interactions. Be precise — cite evidence. "
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
))

# ── Legal / Compliance ─────────────────────────────────────────────────────

_register(PromptTemplate(
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
))

_register(PromptTemplate(
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
))

# ── Business / Finance ─────────────────────────────────────────────────────

_register(PromptTemplate(
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
))

_register(PromptTemplate(
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
))

# ── Technical / Engineering ────────────────────────────────────────────────

_register(PromptTemplate(
    name="code_review",
    label="Code Review Analyst",
    icon="🔍",
    category="Technical",
    system_prompt=(
        "You are a code review analyst. Identify bugs, security issues, "
        "performance problems, and code smells. "
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
))

_register(PromptTemplate(
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
))

# ── Research / Academic ────────────────────────────────────────────────────

_register(PromptTemplate(
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
))

_register(PromptTemplate(
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
))

# ── Data Quality / ETL ─────────────────────────────────────────────────────

_register(PromptTemplate(
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
))

_register(PromptTemplate(
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
    example_query="Who are the key people and organizations, and how are they connected?",
))


# ─── Custom Prompt Persistence ─────────────────────────────────────────────

_CUSTOM_PROMPTS_FILE = Path("data") / "custom_prompts.json"

_MAX_SYSTEM_PROMPT_TOKENS = 200
_MAX_SYSTEM_PROMPT_CHARS = 800


def _estimate_tokens(text: str) -> int:
    """Rough token estimate."""
    return max(1, int(len(text.split()) / 0.75))


def validate_prompt(system_prompt: str) -> List[str]:
    """Validate a prompt against small-LLM design rules. Returns warnings."""
    warnings: List[str] = []
    tokens = _estimate_tokens(system_prompt)

    if tokens > _MAX_SYSTEM_PROMPT_TOKENS:
        warnings.append(
            f"System prompt ~{tokens} tokens (recommended ≤{_MAX_SYSTEM_PROMPT_TOKENS}). "
            "Small models may lose coherence with long instructions."
        )

    if len(system_prompt) > _MAX_SYSTEM_PROMPT_CHARS:
        warnings.append(f"System prompt {len(system_prompt)} chars — consider trimming.")

    _IMPERATIVES = re.compile(
        r"\b(extract|list|compare|identify|find|check|analyze|verify|"
        r"summarize|output|determine|map|review|flag|cite|note)\b",
        re.IGNORECASE,
    )
    if not _IMPERATIVES.search(system_prompt):
        warnings.append(
            "No imperative verbs found. Small LLMs respond better to direct commands."
        )

    if not re.search(r"(output|format|respond|structure)", system_prompt, re.IGNORECASE):
        warnings.append("No format constraint detected. Add 'Output as: ...' for structured responses.")

    if not re.search(r"(do not|don\'t|never|avoid|skip)", system_prompt, re.IGNORECASE):
        warnings.append("No negative constraint. Adding 'Do NOT ...' prevents rambling.")

    return warnings


class PromptTemplateLibrary:
    """Manages built-in + user-created custom prompt templates.

    Usage:
        lib = get_template_library()
        system_prompt, wrapped_query = lib.apply_template("medical_symptoms", "patient data?")
    """

    def __init__(self, storage_dir: Optional[Path] = None):
        self._builtins = dict(_BUILTIN_TEMPLATES)
        self._customs: Dict[str, PromptTemplate] = {}
        self._storage = storage_dir or _CUSTOM_PROMPTS_FILE
        self._load_customs()

    def list_templates(
        self,
        category: Optional[str] = None,
        include_builtins: bool = True,
        include_customs: bool = True,
    ) -> List[PromptTemplate]:
        result = []
        if include_builtins:
            result.extend(self._builtins.values())
        if include_customs:
            result.extend(self._customs.values())
        if category:
            result = [t for t in result if t.category.lower() == category.lower()]
        return sorted(result, key=lambda t: (t.category, t.label))

    def list_categories(self) -> List[str]:
        cats = set()
        for t in self._builtins.values():
            cats.add(t.category)
        for t in self._customs.values():
            cats.add(t.category)
        return sorted(cats)

    def get_template(self, name: str) -> Optional[PromptTemplate]:
        return self._customs.get(name) or self._builtins.get(name)

    @property
    def builtin_count(self) -> int:
        return len(self._builtins)

    @property
    def custom_count(self) -> int:
        return len(self._customs)

    def apply_template(self, name: str, user_query: str) -> Tuple[str, str]:
        """Apply a template to a query. Returns (system_prompt, wrapped_query)."""
        tpl = self.get_template(name)
        if not tpl:
            return "", user_query

        wrapped = user_query
        if tpl.query_prefix or tpl.query_suffix:
            wrapped = f"{tpl.query_prefix}{user_query}{tpl.query_suffix}"

        return tpl.system_prompt, wrapped

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
        """Create or update a custom prompt template."""
        slug = re.sub(r"[^a-z0-9_]", "_", name.lower().strip())
        if not slug:
            slug = "custom_prompt"
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
        return tpl, warnings

    def delete_custom(self, name: str) -> bool:
        if name in self._customs:
            del self._customs[name]
            self._save_customs()
            return True
        return False

    def clone_as_custom(self, source_name: str, new_name: Optional[str] = None) -> Optional[PromptTemplate]:
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

    def _load_customs(self) -> None:
        try:
            if self._storage.exists():
                data = json.loads(self._storage.read_text(encoding="utf-8"))
                for entry in data:
                    try:
                        tpl = PromptTemplate.from_dict(entry)
                        self._customs[tpl.name] = tpl
                    except Exception as e:
                        logger.warning(f"[PromptTemplateLibrary] Skipping bad entry: {e}")
        except Exception as e:
            logger.warning(f"[PromptTemplateLibrary] Could not load customs: {e}")

    def _save_customs(self) -> None:
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
