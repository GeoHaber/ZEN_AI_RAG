"""
Core/data_analyst_agent.py — ZEN_RAG Data Analyst Agent
=========================================================
Natural-language CSV/Excel analysis using DataSchema inference,
LLM-generated pandas code, safe execution, and LLM synthesis.

Usage:
    from Core.data_analyst_agent import DataAnalystAgent, DataSchema
    import pandas as pd

    df = pd.read_csv("data.csv")
    agent = DataAnalystAgent()
    schema = agent.infer_schema(df)
    result = agent.analyze("What is the average sales per region?", df, llm_fn=my_llm)
    print(result.answer)
"""

from __future__ import annotations

import io
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ── Optional pandas import ─────────────────────────────────────────────────
try:
    import pandas as pd
    import numpy as np

    _PANDAS = True
except ImportError:
    _PANDAS = False
    logger.warning("pandas/numpy not installed — DataAnalystAgent unavailable")


# =============================================================================
# DATA MODELS
# =============================================================================


@dataclass
class ColumnInfo:
    """Metadata for a single DataFrame column."""

    name: str
    dtype: str  # pandas dtype string
    role: str  # "date" | "numeric" | "categorical" | "text" | "id"
    nunique: int = 0
    sample_values: List[Any] = field(default_factory=list)
    # Numeric stats (role == "numeric")
    min_val: Optional[float] = None
    max_val: Optional[float] = None
    mean_val: Optional[float] = None
    std_val: Optional[float] = None
    # Categorical stats (role == "categorical")
    top_values: List[Tuple[Any, int]] = field(default_factory=list)  # (value, count)
    # Missing
    null_count: int = 0
    null_pct: float = 0.0

    def describe(self) -> str:
        """Human-readable one-line description for LLM prompt."""
        parts = [f"`{self.name}` ({self.dtype}, {self.role})"]
        if self.role == "numeric" and self.min_val is not None:
            parts.append(f"range [{self.min_val:.2g}…{self.max_val:.2g}], mean={self.mean_val:.2g}")
        elif self.role == "categorical" and self.top_values:
            top = ", ".join(f"'{v}'" for v, _ in self.top_values[:5])
            parts.append(f"top values: {top}")
        elif self.role == "date":
            if self.sample_values:
                parts.append(f"sample: {self.sample_values[0]}")
        if self.null_pct > 0:
            parts.append(f"{self.null_pct:.0f}% null")
        return " — ".join(parts)


@dataclass
class DataSchema:
    """Complete schema for a DataFrame."""

    columns: List[ColumnInfo]
    row_count: int
    col_count: int
    sheet_name: Optional[str] = None
    file_name: Optional[str] = None

    def to_prompt_str(self) -> str:
        """Compact schema representation for LLM prompts."""
        lines = [
            f"DataFrame: {self.row_count} rows × {self.col_count} columns"
            + (f" (sheet: {self.sheet_name})" if self.sheet_name else "")
            + (f" from {self.file_name}" if self.file_name else ""),
            "",
            "Columns:",
        ]
        for col in self.columns:
            lines.append(f"  • {col.describe()}")
        return "\n".join(lines)

    def column_names(self) -> List[str]:
        return [c.name for c in self.columns]


@dataclass
class AnalysisResult:
    """Result of a data analysis query."""

    question: str
    answer: str
    pandas_code: str
    raw_result: Any  # actual pandas result (scalar, Series, DataFrame)
    result_type: str  # "scalar" | "series" | "dataframe" | "error"
    error: Optional[str] = None
    chart_data: Optional[Any] = None  # pandas Series/DataFrame suitable for charting
    sources_used: int = 0


# =============================================================================
# DATA ANALYST AGENT
# =============================================================================


class DataAnalystAgent:
    """
    Analyzes tabular data via natural language questions.

    Pipeline:
        1. infer_schema(df)             → DataSchema
        2. nl_to_pandas_code(q, schema) → Python/pandas code string (via LLM)
        3. execute_safely(code, df)     → (result, error)
        4. synthesize_answer(...)       → natural language answer (via LLM)
    """

    # Code execution sandbox: only allow safe pandas/numpy operations
    _SAFE_IMPORTS = {
        "pd": None,  # filled at runtime
        "np": None,
        "df": None,
    }

    _FORBIDDEN_PATTERNS = [
        r"\bimport\b",
        r"\bexec\b",
        r"\beval\b",
        r"\bopen\b",
        r"\bos\.",
        r"\bsys\.",
        r"\bsubprocess\b",
        r"\b__import__\b",
        r"\bshutil\b",
        r"\bpathlib\b",
        r"requests\.",
        r"socket\.",
    ]

    def __init__(self, max_rows_in_prompt: int = 5, max_code_retries: int = 2):
        self.max_rows_in_prompt = max_rows_in_prompt
        self.max_code_retries = max_code_retries

    # ── Schema Inference ──────────────────────────────────────────────────

    def infer_schema(
        self,
        df: "pd.DataFrame",
        sheet_name: Optional[str] = None,
        file_name: Optional[str] = None,
    ) -> DataSchema:
        """Auto-detect column roles and statistics from a DataFrame."""
        if not _PANDAS:
            raise RuntimeError("pandas is required for DataAnalystAgent")

        columns: List[ColumnInfo] = []
        n_rows = len(df)

        for col_name in df.columns:
            series = df[col_name]
            dtype_str = str(series.dtype)
            null_count = int(series.isna().sum())
            null_pct = round(100 * null_count / max(n_rows, 1), 1)
            nunique = int(series.nunique(dropna=True))
            sample = [v for v in series.dropna().head(3).tolist() if v is not None]

            # Determine role
            role = self._detect_role(series, col_name, nunique, n_rows)

            col_info = ColumnInfo(
                name=col_name,
                dtype=dtype_str,
                role=role,
                nunique=nunique,
                sample_values=sample,
                null_count=null_count,
                null_pct=null_pct,
            )

            # Add stats based on role
            if role == "numeric":
                try:
                    numeric = pd.to_numeric(series, errors="coerce").dropna()
                    if len(numeric) > 0:
                        col_info.min_val = float(numeric.min())
                        col_info.max_val = float(numeric.max())
                        col_info.mean_val = float(numeric.mean())
                        col_info.std_val = float(numeric.std())
                except Exception as exc:
                    logger.debug("%s", exc)

            elif role == "categorical":
                try:
                    vc = series.value_counts().head(10)
                    col_info.top_values = [(v, int(c)) for v, c in vc.items()]
                except Exception as exc:
                    logger.debug("%s", exc)

            columns.append(col_info)

        return DataSchema(
            columns=columns,
            row_count=n_rows,
            col_count=len(df.columns),
            sheet_name=sheet_name,
            file_name=file_name,
        )

    def _detect_role(
        self,
        series: "pd.Series",
        col_name: str,
        nunique: int,
        n_rows: int,
    ) -> str:
        """Heuristic column role detection."""
        name_lower = col_name.lower()
        dtype_str = str(series.dtype)

        # Date detection
        if "datetime" in dtype_str or "timestamp" in dtype_str:
            return "date"
        if any(
            kw in name_lower
            for kw in [
                "date",
                "time",
                "year",
                "month",
                "day",
                "data",
                "zi",
                "luna",
                "an",
            ]
        ):
            # Try to parse as date
            try:
                sample = series.dropna().head(20)
                pd.to_datetime(sample, errors="raise", infer_datetime_format=True)
                return "date"
            except Exception as exc:
                logger.debug("%s", exc)

        # Numeric detection
        if "int" in dtype_str or "float" in dtype_str:
            # Distinguish ID (high cardinality int) from numeric
            if nunique == n_rows and "id" in name_lower:
                return "id"
            return "numeric"

        # Try to coerce to numeric
        if dtype_str == "object":
            try:
                numeric_count = pd.to_numeric(series.dropna().head(50), errors="coerce").notna().sum()
                if numeric_count > 40:  # >80% convertible
                    return "numeric"
            except Exception as exc:
                logger.debug("%s", exc)

        # Categorical (low cardinality)
        if nunique <= max(20, n_rows * 0.05):
            return "categorical"

        # ID-like (every value unique, short strings)
        if nunique == n_rows:
            avg_len = series.dropna().astype(str).str.len().mean()
            if avg_len < 20:
                return "id"

        # Default: text
        return "text"

    # ── NL → Pandas Code ─────────────────────────────────────────────────

    def nl_to_pandas_code(
        self,
        question: str,
        schema: DataSchema,
        llm_fn: Optional[Callable[[str], str]] = None,
    ) -> str:
        """
        Convert a natural language question into pandas code.

        Args:
            question: User's question about the data
            schema:   DataSchema from infer_schema()
            llm_fn:   Callable(prompt: str) -> str, or None (returns template code)

        Returns:
            Python code string that operates on a variable named `df`
            and assigns the result to `result`
        """
        if llm_fn is None:
            return self._fallback_code(question, schema)

        prompt = self._build_code_prompt(question, schema)
        try:
            raw = llm_fn(prompt)
            code = self._extract_code(raw)
            return code
        except Exception as e:
            logger.error(f"LLM code generation failed: {e}")
            return self._fallback_code(question, schema)

    def _build_code_prompt(self, question: str, schema: DataSchema) -> str:
        return f"""You are a pandas expert. Generate Python code to answer the user's question about a DataFrame.

{schema.to_prompt_str()}

User question: {question}

Rules:
- The DataFrame is named `df` and is already loaded
- Assign the final answer to a variable named `result`
- Keep code minimal (1-5 lines)
- Use only pandas (pd) and numpy (np) — no imports needed
- Do NOT use print(), display(), or plt — just assign to `result`
- If the question asks for a count/sum/mean, return a scalar
- If the question asks to compare groups, return a Series or small DataFrame
- Return ONLY the code block, nothing else

Example for "total sales by region":
```python
result = df.groupby('region')['sales'].sum().sort_values(ascending=False)
```

Now write code for: {question}
```python"""

    def _extract_code(self, llm_output: str) -> str:
        """Extract Python code block from LLM response."""
        # Try markdown code block first
        patterns = [
            r"```python\n(.*?)```",
            r"```\n(.*?)```",
            r"`(.*?)`",
        ]
        for pattern in patterns:
            match = re.search(pattern, llm_output, re.DOTALL)
            if match:
                code = match.group(1).strip()
                if "result" in code or "df" in code:
                    return code

        # Fallback: take lines that look like code
        lines = []
        for line in llm_output.strip().splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith("#") and not stripped.startswith("//"):
                # Skip explanatory sentences
                if "=" in stripped or stripped.startswith("result") or stripped.startswith("df"):
                    lines.append(stripped)

        return "\n".join(lines) if lines else "result = df.describe()"

    def _fallback_code(self, question: str, schema: DataSchema) -> str:
        """Template-based fallback when LLM is unavailable."""
        q = question.lower()
        numeric_cols = [c.name for c in schema.columns if c.role == "numeric"]
        cat_cols = [c.name for c in schema.columns if c.role == "categorical"]
        date_cols = [c.name for c in schema.columns if c.role == "date"]

        # Basic keyword matching
        if any(w in q for w in ["count", "how many", "câte", "câți"]):
            return "result = len(df)"
        if any(w in q for w in ["average", "mean", "medie"]) and numeric_cols:
            return f"result = df[{numeric_cols!r}].mean()"
        if any(w in q for w in ["sum", "total", "sumă"]) and numeric_cols:
            col = numeric_cols[0]
            if cat_cols:
                return f"result = df.groupby('{cat_cols[0]}')['{col}'].sum().sort_values(ascending=False)"
            return f"result = df['{col}'].sum()"
        if any(w in q for w in ["max", "maximum", "maxim"]) and numeric_cols:
            return f"result = df['{numeric_cols[0]}'].max()"
        if any(w in q for w in ["min", "minimum", "minim"]) and numeric_cols:
            return f"result = df['{numeric_cols[0]}'].min()"
        if any(w in q for w in ["unique", "distinct", "unice"]) and cat_cols:
            return f"result = df['{cat_cols[0]}'].value_counts()"
        if any(w in q for w in ["missing", "null", "nan", "lipsă"]):
            return "result = df.isna().sum()"
        if any(w in q for w in ["describe", "summary", "statistics", "statistici"]):
            return "result = df.describe()"

        # Default: summary
        return "result = df.describe(include='all').T[['count','mean','min','max']].dropna(how='all')"

    # ── Safe Execution ────────────────────────────────────────────────────

    def execute_safely(
        self,
        code: str,
        df: "pd.DataFrame",
    ) -> Tuple[Any, Optional[str]]:
        """
        Execute pandas code in a restricted namespace.

        Returns:
            (result, error_message) — error is None on success
        """
        # Security check
        for pattern in self._FORBIDDEN_PATTERNS:
            if re.search(pattern, code):
                return None, f"Forbidden pattern detected: {pattern}"

        namespace = {
            "df": df.copy(),
            "pd": pd,
            "np": np if _PANDAS else None,
            "result": None,
        }

        try:
            exec(compile(code, "<analyst>", "exec"), namespace)  # noqa: S102
            result = namespace.get("result")
            return result, None
        except Exception as e:
            return None, f"{type(e).__name__}: {e}"

    # ── Result Classification ─────────────────────────────────────────────

    def classify_result(self, result: Any) -> Tuple[str, Optional[Any]]:
        """
        Determine result type and extract chart-ready data.

        Returns:
            (result_type, chart_data)
            result_type: "scalar" | "series" | "dataframe" | "none"
            chart_data: pandas Series or None
        """
        if result is None:
            return "none", None

        if _PANDAS:
            if isinstance(result, pd.DataFrame):
                chart_data = None
                # If single numeric column, use it for charting
                num_cols = result.select_dtypes(include="number").columns.tolist()
                if len(num_cols) == 1 and len(result) <= 50:
                    chart_data = result[num_cols[0]]
                elif len(num_cols) >= 1 and len(result) <= 20:
                    chart_data = result[num_cols[0]]
                return "dataframe", chart_data

            if isinstance(result, pd.Series):
                chart_data = (
                    result if result.dtype in (float, int) or str(result.dtype).startswith(("int", "float")) else None
                )
                # Filter to top 20 for chart
                if chart_data is not None and len(chart_data) > 20:
                    chart_data = chart_data.head(20)
                return "series", chart_data

        # Scalar
        if isinstance(result, (int, float, str, bool)):
            return "scalar", None
        if isinstance(result, (list, dict)):
            return "scalar", None

        return "scalar", None

    # ── LLM Answer Synthesis ──────────────────────────────────────────────

    def synthesize_answer(
        self,
        question: str,
        result: Any,
        schema: DataSchema,
        result_type: str,
        llm_fn: Optional[Callable[[str], str]] = None,
        error: Optional[str] = None,
    ) -> str:
        """
        Synthesize a natural language answer from the pandas result.

        Falls back to a formatted string if LLM is unavailable.
        """
        if error:
            return f"⚠️ Could not compute the answer: {error}"

        if result is None:
            return "The query returned no results."

        # Build result string for LLM
        result_str = self._result_to_str(result, result_type)

        if llm_fn is None:
            return self._fallback_answer(question, result_str, result_type)

        prompt = f"""You are a data analyst. Summarize the following query result in plain language.

Question: {question}
Data: {schema.file_name or "the dataset"} ({schema.row_count} rows)

Result ({result_type}):
{result_str}

Write a clear, concise answer (2-4 sentences). Include specific numbers.
If the result is a table/series, highlight the key insight.
Answer in the same language as the question."""

        try:
            return llm_fn(prompt).strip()
        except Exception as e:
            logger.error(f"LLM synthesis failed: {e}")
            return self._fallback_answer(question, result_str, result_type)

    def _result_to_str(self, result: Any, result_type: str) -> str:
        """Convert result to a compact string for prompts."""
        if result_type == "scalar":
            if isinstance(result, float):
                return f"{result:,.4g}"
            return str(result)

        if _PANDAS and isinstance(result, pd.Series):
            return result.head(20).to_string()

        if _PANDAS and isinstance(result, pd.DataFrame):
            return result.head(10).to_string()

        return str(result)[:500]

    def _fallback_answer(self, question: str, result_str: str, result_type: str) -> str:
        """Plain-text answer without LLM."""
        if result_type == "scalar":
            return f"**Result:** {result_str}"
        if result_type in ("series", "dataframe"):
            lines = result_str.strip().splitlines()
            preview = "\n".join(lines[:10])
            suffix = f"\n…({len(lines) - 10} more rows)" if len(lines) > 10 else ""
            return f"**Result:**\n```\n{preview}{suffix}\n```"
        return result_str

    # ── Full Pipeline ─────────────────────────────────────────────────────

    def analyze(
        self,
        question: str,
        df: "pd.DataFrame",
        schema: Optional[DataSchema] = None,
        llm_fn: Optional[Callable[[str], str]] = None,
        sheet_name: Optional[str] = None,
        file_name: Optional[str] = None,
        retry_on_error: bool = True,
    ) -> AnalysisResult:
        """
        Full NL→pandas→answer pipeline.

        Args:
            question:   Natural language question
            df:         The DataFrame to analyze
            schema:     Pre-computed schema (inferred if None)
            llm_fn:     Callable(prompt) -> str for code gen + synthesis
            retry_on_error: Re-ask LLM to fix code if execution fails
        """
        if not _PANDAS:
            return AnalysisResult(
                question=question,
                answer="pandas not installed",
                pandas_code="",
                raw_result=None,
                result_type="error",
                error="pandas not installed",
            )

        # Step 1: Schema
        if schema is None:
            schema = self.infer_schema(df, sheet_name=sheet_name, file_name=file_name)

        # Step 2: Generate code
        code = self.nl_to_pandas_code(question, schema, llm_fn=llm_fn)

        # Step 3: Execute
        result, error = self.execute_safely(code, df)

        # Step 3b: Retry with error feedback
        if error and retry_on_error and llm_fn:
            retry_prompt = (
                f"The previous pandas code failed:\n```python\n{code}\n```\n"
                f"Error: {error}\n\n"
                f"Fix it for the question: {question}\n"
                f"DataFrame schema:\n{schema.to_prompt_str()}\n\n"
                "Write corrected code only:\n```python"
            )
            try:
                fixed_raw = llm_fn(retry_prompt)
                code = self._extract_code(fixed_raw)
                result, error = self.execute_safely(code, df)
            except Exception as exc:
                logger.debug("%s", exc)

        # Step 4: Classify result
        result_type, chart_data = self.classify_result(result)

        # Step 5: Synthesize answer
        answer = self.synthesize_answer(
            question,
            result,
            schema,
            result_type,
            llm_fn=llm_fn,
            error=error,
        )

        return AnalysisResult(
            question=question,
            answer=answer,
            pandas_code=code,
            raw_result=result,
            result_type=result_type,
            error=error,
            chart_data=chart_data,
        )


# =============================================================================
# HELPERS: Load file → DataFrame
# =============================================================================


def load_file_to_dataframe(
    file_path: str | Path,
    sheet_name: Optional[str] = None,
) -> Tuple[Optional["pd.DataFrame"], str, Optional[str]]:
    """
    Load a CSV or Excel file into a pandas DataFrame.

    Returns:
        (df, sheet_name_used, error_message)
    """
    if not _PANDAS:
        return None, "", "pandas not installed"

    path = Path(file_path)
    suffix = path.suffix.lower()

    try:
        if suffix == ".csv":
            df = pd.read_csv(path, encoding_errors="replace")
            return df, "", None

        elif suffix in (".tsv", ".txt"):
            df = pd.read_csv(path, sep="\t", encoding_errors="replace")
            return df, "", None

        elif suffix in (".xlsx", ".xls", ".xlsm"):
            xls = pd.ExcelFile(path)
            sheets = xls.sheet_names
            if not sheets:
                return None, "", "Excel file has no sheets"
            target = sheet_name if sheet_name in sheets else sheets[0]
            df = xls.parse(target)
            return df, target, None

        else:
            return None, "", f"Unsupported file type: {suffix}"

    except Exception as e:
        return None, "", str(e)


def load_uploaded_file(
    uploaded_file: Any,  # st.runtime.uploaded_file_manager.UploadedFile
    sheet_name: Optional[str] = None,
) -> Tuple[Optional["pd.DataFrame"], str, Optional[str], List[str]]:
    """
    Load a Streamlit UploadedFile into a DataFrame.

    Returns:
        (df, sheet_name_used, error_message, available_sheets)
    """
    if not _PANDAS:
        return None, "", "pandas not installed", []

    name = uploaded_file.name.lower()
    data = uploaded_file.read()

    try:
        if name.endswith(".csv") or name.endswith(".tsv"):
            sep = "\t" if name.endswith(".tsv") else ","
            df = pd.read_csv(io.BytesIO(data), sep=sep, encoding_errors="replace")
            return df, "", None, []

        elif name.endswith((".xlsx", ".xls", ".xlsm")):
            xls = pd.ExcelFile(io.BytesIO(data))
            sheets = xls.sheet_names
            target = sheet_name if sheet_name in sheets else sheets[0]
            df = xls.parse(target)
            return df, target, None, sheets

        else:
            return None, "", f"Unsupported: {uploaded_file.name}", []

    except Exception as e:
        return None, "", str(e), []
