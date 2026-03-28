"""
tests/test_conflict_resolver.py — Unit tests for Core/conflict_resolver.py

Tests: Assertion/Conflict dataclasses, SourceCredibilityMap, ConflictResolver,
       detect_conflicts, resolve_conflict, recency scoring, assertion summary.
"""

import pytest
import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from Core.conflict_resolver import (
    Assertion,
    Conflict,
    SourceCredibilityMap,
    ConflictResolver,
    extract_entities_and_claims,
)


# ── Assertion dataclass ──────────────────────────────────────────────────────


class TestAssertion:
    def test_fields(self):
        a = Assertion(
            entity="Einstein",
            predicate="birth_year",
            value="1879",
            source_name="wiki",
            source_type="academic",
        )
        assert a.entity == "Einstein"
        assert a.confidence == 1.0  # default

    def test_optional_date(self):
        a = Assertion(
            entity="X",
            predicate="p",
            value="v",
            source_name="s",
            source_type="web",
            source_date=datetime(2024, 1, 1),
        )
        assert a.source_date.year == 2024


# ── Conflict dataclass ───────────────────────────────────────────────────────


class TestConflict:
    def test_default_resolution(self):
        c = Conflict(entity="X", predicate="p", assertions=[])
        assert c.resolution is None
        assert c.reasoning == ""


# ── SourceCredibilityMap ─────────────────────────────────────────────────────


class TestSourceCredibilityMap:
    def test_type_scores(self):
        scm = SourceCredibilityMap()
        assert scm.TYPE_SCORES["academic"] == 0.90
        assert scm.TYPE_SCORES["web"] == 0.50

    def test_override_matches(self):
        scm = SourceCredibilityMap()
        a = Assertion(
            entity="X",
            predicate="p",
            value="v",
            source_name="reuters.com/article/123",
            source_type="news",
        )
        assert scm.score(a) == 0.85  # reuters override

    def test_fallback_to_type(self):
        scm = SourceCredibilityMap()
        a = Assertion(
            entity="X",
            predicate="p",
            value="v",
            source_name="random-blog.com",
            source_type="txt",
        )
        assert scm.score(a) == 0.40

    def test_unknown_type(self):
        scm = SourceCredibilityMap()
        a = Assertion(
            entity="X",
            predicate="p",
            value="v",
            source_name="test",
            source_type="nonexistent_type",
        )
        assert scm.score(a) == 0.5


# ── ConflictResolver.detect_conflicts ────────────────────────────────────────


class TestDetectConflicts:
    @pytest.fixture
    def resolver(self):
        return ConflictResolver()

    def test_empty(self, resolver):
        assert resolver.detect_conflicts([]) == []

    def test_no_conflicts(self, resolver):
        assertions = [
            Assertion("Einstein", "birth_year", "1879", "src1", "wiki"),
            Assertion("Einstein", "birth_year", "1879", "src2", "web"),
        ]
        assert resolver.detect_conflicts(assertions) == []

    def test_detects_conflict(self, resolver):
        assertions = [
            Assertion("Einstein", "birth_year", "1879", "src1", "wiki"),
            Assertion("Einstein", "birth_year", "1878", "src2", "web"),
        ]
        conflicts = resolver.detect_conflicts(assertions)
        assert len(conflicts) == 1
        assert conflicts[0].entity == "einstein"
        assert len(conflicts[0].assertions) == 2

    def test_multiple_conflicts(self, resolver):
        assertions = [
            Assertion("Einstein", "birth_year", "1879", "src1", "wiki"),
            Assertion("Einstein", "birth_year", "1878", "src2", "web"),
            Assertion("Berlin", "population", "3.6M", "src1", "wiki"),
            Assertion("Berlin", "population", "4M", "src3", "news"),
        ]
        conflicts = resolver.detect_conflicts(assertions)
        assert len(conflicts) == 2

    def test_case_insensitive_grouping(self, resolver):
        assertions = [
            Assertion("Einstein", "Birth_Year", "1879", "src1", "wiki"),
            Assertion("einstein", "birth_year", "1878", "src2", "web"),
        ]
        conflicts = resolver.detect_conflicts(assertions)
        assert len(conflicts) == 1


# ── ConflictResolver.resolve_conflict ────────────────────────────────────────


class TestResolveConflict:
    @pytest.fixture
    def resolver(self):
        return ConflictResolver()

    def test_consensus_resolution(self, resolver):
        """66%+ agreement should use consensus."""
        assertions = [
            Assertion("Einstein", "birth_year", "1879", "s1", "wiki"),
            Assertion("Einstein", "birth_year", "1879", "s2", "academic"),
            Assertion("Einstein", "birth_year", "1878", "s3", "web"),
        ]
        conflict = Conflict(entity="einstein", predicate="birth_year", assertions=assertions)
        resolved = resolver.resolve_conflict(conflict)
        assert resolved.resolution == "1879"
        assert "Consensus" in resolved.reasoning

    def test_credibility_resolution(self, resolver):
        """No consensus → use credibility+recency."""
        assertions = [
            Assertion("X", "p", "A", "bbc.com", "news", source_date=datetime(2024, 1, 1)),
            Assertion("X", "p", "B", "random.com", "txt", source_date=datetime(1990, 1, 1)),
        ]
        conflict = Conflict(entity="x", predicate="p", assertions=assertions)
        resolved = resolver.resolve_conflict(conflict)
        assert resolved.resolution is not None
        assert "reliability" in resolved.reasoning.lower() or "Highest" in resolved.reasoning


# ── _recency_score ───────────────────────────────────────────────────────────


class TestRecencyScore:
    @pytest.fixture
    def resolver(self):
        return ConflictResolver()

    def test_none_date(self, resolver):
        assert resolver._recency_score(None) == 0.5

    def test_recent(self, resolver):
        recent = datetime.now() - timedelta(days=5)
        assert resolver._recency_score(recent) == 1.0

    def test_within_year(self, resolver):
        d = datetime.now() - timedelta(days=200)
        assert resolver._recency_score(d) == 0.8

    def test_within_5_years(self, resolver):
        d = datetime.now() - timedelta(days=1000)
        assert resolver._recency_score(d) == 0.5

    def test_very_old(self, resolver):
        d = datetime.now() - timedelta(days=3000)
        assert resolver._recency_score(d) == 0.2


# ── build_assertion_summary ──────────────────────────────────────────────────


class TestBuildAssertionSummary:
    @pytest.fixture
    def resolver(self):
        return ConflictResolver()

    def test_empty(self, resolver):
        assert resolver.build_assertion_summary([]) == ""

    def test_with_conflict(self, resolver):
        assertions = [
            Assertion("Einstein", "birth_year", "1879", "wiki", "wiki"),
            Assertion("Einstein", "birth_year", "1878", "blog", "web"),
        ]
        conflict = Conflict(entity="Einstein", predicate="birth_year", assertions=assertions)
        resolver.resolve_conflict(conflict)
        summary = resolver.build_assertion_summary([conflict])
        assert "Einstein" in summary
        assert "Recommended" in summary or "Unable" in summary


# ── extract_entities_and_claims (placeholder) ────────────────────────────────


class TestExtractEntitiesAndClaims:
    def test_returns_list(self):
        result = extract_entities_and_claims("Some text about Einstein.", "test_source")
        assert isinstance(result, list)

    def test_is_empty_placeholder(self):
        result = extract_entities_and_claims("Any text", "any_source")
        assert result == []
