"""
X_Ray Analysis for Rustification
Analyzes RAG_RAT codebase to identify modules for Rust conversion
Generates metrics: complexity, performance impact, async requirements
"""

import json
import ast
from pathlib import Path
from typing import Dict
import re


class CodeAnalyzer:
    def __init__(self, root_dir: str):
        self.root = Path(root_dir)
        self.metrics = {
            "total_files": 0,
            "total_lines": 0,
            "total_functions": 0,
            "total_classes": 0,
            "modules": {},
            "complexity_metrics": {},
            "async_functions": [],
            "io_bound_operations": [],
            "cpu_bound_operations": [],
            "performance_critical": [],
        }
        self.exclude_dirs = {
            "__pycache__",
            ".git",
            "venv",
            "env",
            ".pytest_cache",
            "node_modules",
            "build",
            "dist",
            "target",
            ".streamlit",
        }

    def is_python_file(self, path: Path) -> bool:
        return path.suffix == ".py" and path.name != "__init__.py"

    def should_skip(self, path: Path) -> bool:
        for exclude in self.exclude_dirs:
            if exclude in path.parts:
                return True
        return False

    def analyze_file(self, file_path: Path) -> Dict:
        """Analyze a single Python file"""
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            lines = content.split("\n")
            file_metrics = {
                "path": str(file_path.relative_to(self.root)),
                "lines": len(lines),
                "functions": 0,
                "classes": 0,
                "async_functions": [],
                "io_operations": [],
                "cpu_intensive": [],
                "complexity_score": 0,
                "cyclomatic_complexity": 0,
            }

            tree = ast.parse(content)

            functions = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
            async_functions = [node for node in ast.walk(tree) if isinstance(node, ast.AsyncFunctionDef)]
            classes = [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]

            file_metrics["functions"] = len(functions)
            file_metrics["classes"] = len(classes)

            # Detect async functions
            for func in async_functions:
                file_metrics["async_functions"].append(func.name)
                self.metrics["async_functions"].append(
                    {
                        "file": file_path.relative_to(self.root).as_posix(),
                        "function": func.name,
                    }
                )

            # Detect I/O operations
            io_patterns = {
                "file": ["open", "read", "write", "seek"],
                "network": ["requests", "socket", "http", "urllib", "aiohttp"],
                "database": ["sql", "query", "execute", "fetch", "db"],
                "async": ["await", "asyncio", "aio"],
            }

            for pattern_type, keywords in io_patterns.items():
                for keyword in keywords:
                    if keyword in content.lower():
                        file_metrics["io_operations"].append(pattern_type)

            # Detect CPU-intensive operations
            cpu_patterns = [
                "numpy",
                "pandas",
                "scipy",
                "tensorflow",
                "torch",
                "ml",
                "math",
                "hash",
                "crypto",
            ]
            for pattern in cpu_patterns:
                if re.search(rf"\b{pattern}\b", content, re.IGNORECASE):
                    file_metrics["cpu_intensive"].append(pattern)

            # Calculate complexity
            file_metrics["complexity_score"] = len(functions) * 3 + len(classes) * 5

            # Cyclomatic complexity approximation
            if_count = content.count(" if ") + content.count("\nif ")
            for_count = content.count(" for ") + content.count("\nfor ")
            while_count = content.count(" while ") + content.count("\nwhile ")
            exception_count = content.count("except")

            file_metrics["cyclomatic_complexity"] = 1 + if_count + for_count + while_count + exception_count

            return file_metrics

        except Exception:
            print(f"Error analyzing {file_path}: {e}")
            return None

    def analyze_directory(self):
        """Recursively analyze all Python files"""
        print(f"Starting X_Ray analysis of {self.root}...")
        print("-" * 80)

        for py_file in sorted(self.root.rglob("*.py")):
            if self.should_skip(py_file):
                continue

            self.metrics["total_files"] += 1
            metrics = self.analyze_file(py_file)

            if metrics:
                module_name = str(py_file.relative_to(self.root)).replace("\\", "/")
                self.metrics["modules"][module_name] = metrics
                self.metrics["total_lines"] += metrics["lines"]
                self.metrics["total_functions"] += metrics["functions"]
                self.metrics["total_classes"] += metrics["classes"]

                print(
                    f"✓ {module_name:60} | {metrics['functions']:3} fn | {metrics['classes']:2} cls | {metrics['complexity_score']:4} cx"
                )

        print("-" * 80)
        self._identify_priority_modules()

    def _identify_priority_modules(self):
        """Identify modules with highest rustification priority"""

        # Ranking criteria:
        # 1. Async functions (network I/O) - HIGH priority
        # 2. CPU-intensive operations - HIGH priority
        # 3. File I/O operations - MEDIUM priority
        # 4. High complexity - MEDIUM priority

        priority_scores = {}

        for module, metrics in self.metrics["modules"].items():
            score = 0
            reasons = []

            # Async operations (high priority for performance)
            if metrics["async_functions"]:
                score += len(metrics["async_functions"]) * 100
                reasons.append(f"async ({len(metrics['async_functions'])} funcs)")

            # CPU-intensive operations
            if metrics["cpu_intensive"]:
                score += len(metrics["cpu_intensive"]) * 80
                reasons.append(f"cpu-intensive ({len(metrics['cpu_intensive'])} types)")

            # I/O operations
            if metrics["io_operations"]:
                score += len(set(metrics["io_operations"])) * 50
                reasons.append(f"i/o ({len(set(metrics['io_operations']))} types)")

            # High complexity
            if metrics["complexity_score"] > 50:
                score += metrics["complexity_score"] // 10
                reasons.append(f"high-complexity ({metrics['complexity_score']})")

            if score > 0:
                priority_scores[module] = {"score": score, "reasons": reasons}

        # Sort and store top priority modules
        sorted_priorities = sorted(priority_scores.items(), key=lambda x: x[1]["score"], reverse=True)
        self.metrics["performance_critical"] = [
            {"module": module, "score": data["score"], "reasons": data["reasons"]}
            for module, data in sorted_priorities[:20]  # Top 20 candidates
        ]

    def generate_report(self, output_file: str):
        """Generate rustification analysis report"""

        report = {
            "analysis_date": str(Path.cwd()),
            "summary": {
                "total_files": self.metrics["total_files"],
                "total_lines": self.metrics["total_lines"],
                "total_functions": self.metrics["total_functions"],
                "total_classes": self.metrics["total_classes"],
                "avg_lines_per_file": (self.metrics["total_lines"] // max(1, self.metrics["total_files"])),
                "avg_complexity": (
                    sum(m.get("complexity_score", 0) for m in self.metrics["modules"].values())
                    // max(1, self.metrics["total_files"])
                ),
            },
            "async_count": len(self.metrics["async_functions"]),
            "priority_modules": self.metrics["performance_critical"],
            "async_modules": [
                {"file": item["file"], "function": item["function"]}
                for item in self.metrics["async_functions"][:50]  # Top 50
            ],
            "rustification_strategy": self.generate_strategy(),
        }

        with open(output_file, "w") as f:
            json.dump(report, f, indent=2)

        return report

    def generate_strategy(self) -> Dict:
        """Generate rustification strategy"""
        return {
            "phase_1_analysis": {
                "description": "Basic module identification and dependency mapping",
                "priority": "critical_path_modules",
                "estimated_effort": "1-2 weeks",
            },
            "phase_2_bindings": {
                "description": "Create Rust bindings via PyO3/maturin for high-impact modules",
                "candidates": ["Core modules", "performance_critical functions"],
                "estimated_effort": "2-3 weeks",
            },
            "phase_3_benchmark": {
                "description": "Benchmark Python vs Rust implementations",
                "metrics": ["execution_time", "memory_usage", "throughput"],
                "estimated_effort": "1 week",
            },
            "phase_4_migration": {
                "description": "Gradual migration to Rust implementations",
                "rollback_capability": "Keep Python fallbacks",
                "estimated_effort": "ongoing",
            },
        }


def main():
    rag_rat_dir = Path(__file__).parent.parent.parent
    analyzer = CodeAnalyzer(str(rag_rat_dir))
    analyzer.analyze_directory()

    report_file = Path(__file__).parent / "rustification_analysis.json"
    report = analyzer.generate_report(str(report_file))

    print("\n" + "=" * 80)
    print("RUSTIFICATION ANALYSIS REPORT")
    print("=" * 80)
    print(f"Total Files: {report['summary']['total_files']}")
    print(f"Total Lines: {report['summary']['total_lines']}")
    print(f"Total Functions: {report['summary']['total_functions']}")
    print(f"Total Classes: {report['summary']['total_classes']}")
    print(f"Async Functions: {report['async_count']}")
    print("\nTop Priority Modules (for Rustification):")
    print("-" * 80)
    for item in report["priority_modules"][:10]:
        print(f"  {item['module']:50} | Score: {item['score']:5} | {', '.join(item['reasons'])}")
    print(f"\nReport saved to: {report_file}")
    print("=" * 80)


if __name__ == "__main__":
    main()
