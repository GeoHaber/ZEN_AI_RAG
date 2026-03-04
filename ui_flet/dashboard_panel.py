# -*- coding: utf-8 -*-
"""
ui_flet/dashboard_panel.py — Performance & Quality Dashboard
==============================================================

Performance metrics (TPS, TTFT, RAG latency) and Intelligence Judge
quality evaluation panel.
"""

from __future__ import annotations

import asyncio
import logging

import flet as ft

from ui_flet.theme import TH, MONO_FONT
from ui_flet.widgets import metric_tile, section_title, spacer

logger = logging.getLogger(__name__)


def build_performance_bar(page: ft.Page, state: dict) -> ft.Container:
    """Thin horizontal bar showing live TPS, TTFT, and RAG latency."""
    tps_text = ft.Text("TPS: —", size=11, color=TH.dim, font_family=MONO_FONT)
    ttft_text = ft.Text("TTFT: —", size=11, color=TH.dim, font_family=MONO_FONT)
    rag_text = ft.Text("RAG: —", size=11, color=TH.dim, font_family=MONO_FONT)

    async def _refresh_metrics():
        """Reload RAG pipeline stats and update the metric tiles."""
        while True:
            try:
                import httpx
                async with httpx.AsyncClient() as client:
                    resp = await client.get("http://127.0.0.1:8002/metrics", timeout=3)
                    if resp.status_code == 200:
                        data = resp.json()
                        tps_text.value = f"TPS: {data.get('tps', 0):.1f}"
                        ttft_text.value = f"TTFT: {data.get('ttft_ms', 0):.0f}ms"
                        rag_text.value = f"RAG: {data.get('rag_latency_ms', 0):.0f}ms"
                        page.update()
            except Exception:
                logger.debug("[Dashboard] Metrics refresh failed")
            await asyncio.sleep(5)

    page.run_task(_refresh_metrics)

    return ft.Container(
        content=ft.Row(
            [tps_text, ttft_text, rag_text],
            spacing=20,
            alignment=ft.MainAxisAlignment.CENTER,
        ),
        bgcolor=TH.surface,
        border=ft.Border.all(1, TH.border),
        border_radius=8,
        padding=ft.Padding.symmetric(vertical=4, horizontal=12),
    )



def _build_quality_dashboard_part2(results_column, status_text):
    """Continue build_quality_dashboard logic."""
    async def on_run_judge(e):
        """Execute the quality benchmark and display scores."""
        status_text.value = "🧪 Running quality evaluation…"
        results_column.controls.clear()
        page.update()

        try:
            import httpx
            async with httpx.AsyncClient() as client:
                # Get model info
                resp = await client.get("http://127.0.0.1:8001/v1/models", timeout=10)
                resp.json() if resp.status_code == 200 else {}

            # Run benchmark questions
            benchmark_qs = [
                "What is the capital of France?",
                "Explain quantum computing in simple terms.",
                "Write a Python function to sort a list.",
            ]

            scores = []
            for q in benchmark_qs:
                try:
                    import httpx
                    async with httpx.AsyncClient() as client:
                        resp = await client.post(
                            "http://127.0.0.1:8002/api/chat",
                            json={"message": q, "mode": "fast"},
                            timeout=60,
                        )
                        if resp.status_code == 200:
                            data = resp.json()
                            answer = data.get("response", "")
                            latency = data.get("latency_ms", 0)
                            scores.append({
                                "question": q,
                                "answer": answer[:200],
                                "latency": latency,
                                "has_answer": bool(answer.strip()),
                            })
                except Exception as exc:
                    scores.append({"question": q, "answer": f"Error: {exc}",
                                   "latency": 0, "has_answer": False})

            # Display results
            quality_score = sum(1 for s in scores if s["has_answer"]) / max(len(scores), 1) * 100
            avg_latency = sum(s["latency"] for s in scores) / max(len(scores), 1)

            results_column.controls = [
                ft.Row([
                    metric_tile("🎯", f"{quality_score:.0f}%", "Quality Score",
                                color=TH.success if quality_score >= 80 else TH.warning_c),
                    metric_tile("⚡", f"{avg_latency:.0f}ms", "Avg Latency"),
                    metric_tile("📝", str(len(scores)), "Questions"),
                ], spacing=8),
                ft.Divider(color=TH.divider, height=12),
            ]

            for s in scores:
                q_color = TH.success if s["has_answer"] else TH.error_c
                results_column.controls.append(
                    ft.ExpansionTile(
                        title=ft.Text(s["question"], size=13),
                        subtitle=ft.Text(
                            f"{'✅' if s['has_answer'] else '❌'} · {s['latency']:.0f}ms",
                            size=11, color=q_color,
                        ),
                        controls=[
                            ft.Container(
                                content=ft.Text(s["answer"], size=12, color=TH.dim,
                                                selectable=True),
                                bgcolor=TH.code_bg,
                                border_radius=8,
                                padding=10,
                            )
                        ],
                        initially_expanded=False,
                    )
                )

            status_text.value = f"✅ Evaluation complete — {quality_score:.0f}% quality"
            page.update()

        except Exception as exc:
            status_text.value = f"❌ Error: {exc}"
            page.update()
            logger.error("Quality evaluation failed: %s", exc)

    return ft.Column(
        [
            build_performance_bar(page, state),
            ft.Divider(color=TH.divider, height=8),
            section_title("Intelligence Judge", "⚖️"),
            ft.Text("Run quality benchmarks against the active LLM.",
                    size=12, color=TH.muted),
            spacer(8),
            ft.Row([
                ft.ElevatedButton(
                    "🧪 Run Evaluation",
                    on_click=lambda e: page.run_task(on_run_judge, e),
                    bgcolor=TH.accent2,
                    color=ft.Colors.WHITE,
                ),
                status_text,
            ], spacing=12),
            ft.Divider(color=TH.divider, height=16),
            results_column,
        ],
        spacing=10,
        expand=True,
    )


def build_quality_dashboard(page: ft.Page, state: dict) -> ft.Column:
    """Intelligence Judge — quality evaluation with benchmarks."""
    results_column = ft.Column([], spacing=8)
    status_text = ft.Text("", size=12, color=TH.dim)

    return _build_quality_dashboard_part2(results_column, status_text)
