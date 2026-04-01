"""
setup_zenai_core.py — Build script for the compiled ZenAI Core distribution.

Compiles all library modules (rag_core, local_llm, Core, adapters)
into native .pyd/.so binaries via Cython, then packages them into
a pip-installable wheel.

Usage:
    python dist_build/setup_zenai_core.py bdist_wheel

The resulting .whl in dist/ contains NO source code — only compiled
C extensions that collaborators install with:
    pip install zenai_core-X.Y.Z-cpXXX-win_amd64.whl
"""

import os
import sys
import shutil
from pathlib import Path

from setuptools import setup, find_packages, Extension

# ── Detect Cython ─────────────────────────────────────────────────────────
if os.environ.get("ZENAI_NO_CYTHON"):
    USE_CYTHON = False
    print("INFO: Cython disabled via ZENAI_NO_CYTHON — building .pyc-only fallback.")
else:
    try:
        from Cython.Build import cythonize
        from Cython.Distutils import build_ext

        USE_CYTHON = True
    except ImportError:
        USE_CYTHON = False
        print("WARNING: Cython not found. Install with: pip install cython")
        print("         Building .pyc-only fallback (less secure).")


# ── Project layout ────────────────────────────────────────────────────────
# This script lives in dist_build/  — project root is one level up.
HERE = Path(__file__).parent
PROJECT_ROOT = HERE.parent

# rag_core source — check env var, then common locations
RAG_CORE_ROOT = Path(os.environ.get("RAG_CORE_ROOT", str(PROJECT_ROOT.parent / "rag_core")))
# Also check sibling project layout
if not (RAG_CORE_ROOT / "rag_core").exists():
    for candidate in [
        PROJECT_ROOT.parent / "rag_core",  # ../rag_core
        PROJECT_ROOT.parent / "RAG_RAT" / "rag_core",  # ../RAG_RAT/rag_core
        PROJECT_ROOT / "rag_core",  # ./rag_core (vendored)
    ]:
        if (candidate / "rag_core").exists() or (candidate / "__init__.py").exists():
            RAG_CORE_ROOT = candidate if (candidate / "rag_core").exists() else candidate.parent
            break

# ── Staging area ──────────────────────────────────────────────────────────
# We copy all source into a staging dir so we can build a clean package
# without polluting the main project. The wheel name: zenai_core

STAGE = HERE / "_staging"


def clean_staging():
    """Remove previous staging artifacts."""
    if STAGE.exists():
        shutil.rmtree(STAGE, ignore_errors=True)
    STAGE.mkdir(parents=True, exist_ok=True)


def stage_package(src_dir: Path, pkg_name: str, files: list[str] = None):
    """Copy a package directory into staging, optionally filtering files."""
    dest = STAGE / pkg_name
    dest.mkdir(parents=True, exist_ok=True)
    if files:
        for f in files:
            src = src_dir / f
            if src.exists():
                shutil.copy2(src, dest / f)
    else:
        # Copy all .py files, preserving subdirectories
        for py in src_dir.rglob("*.py"):
            rel = py.relative_to(src_dir)
            (dest / rel.parent).mkdir(parents=True, exist_ok=True)
            shutil.copy2(py, dest / rel)


def stage_single_module(src_file: Path, pkg_name: str):
    """Place a single .py file into a package inside staging."""
    dest = STAGE / pkg_name
    dest.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src_file, dest / src_file.name)
    # Ensure __init__.py exists
    init = dest / "__init__.py"
    if not init.exists():
        init.write_text(
            f'"""zenai_core.{pkg_name} — auto-generated package wrapper."""\n',
            encoding="utf-8",
        )


# ── Collect .py files to compile ──────────────────────────────────────────


def collect_extensions() -> list[Extension]:
    """Walk staging dir and build Cython Extension objects for every .py."""
    exts = []
    for py_file in STAGE.rglob("*.py"):
        rel = py_file.relative_to(STAGE)
        # Convert path to dotted module name: rag_core/engine.py → rag_core.engine
        module_name = str(rel.with_suffix("")).replace(os.sep, ".")
        # Skip __init__ from compilation — Cython can't compile them into
        # importable packages cleanly, so we keep them as .pyc
        if rel.stem == "__init__":
            continue
        exts.append(Extension(module_name, [str(py_file)]))
    return exts


def build_pyc_fallback():
    """If Cython unavailable, compile to .pyc and strip .py sources.

    The .pyc files are placed alongside __init__.py so setuptools
    picks them up.  Not as secure as .pyd but still strips source.
    """
    import compileall

    # Compile all .py to .pyc
    compileall.compile_dir(str(STAGE), force=True, quiet=1, optimize=2)

    # Move .pyc files from __pycache__ up to their package dirs
    for pyc in STAGE.rglob("*.pyc"):
        # __pycache__/module.cpython-3XX.opt-2.pyc → module.pyc
        # Extract original module name
        stem = pyc.stem.split(".")[0]  # "module" from "module.cpython-314.opt-2"
        if stem == "__init__":
            continue  # keep __init__.py as-is
        dest = pyc.parent.parent / f"{stem}.pyc"
        shutil.copy2(pyc, dest)

    # Remove __pycache__ dirs
    for cache_dir in list(STAGE.rglob("__pycache__")):
        shutil.rmtree(cache_dir, ignore_errors=True)

    # Remove .py sources but keep __init__.py (needed for package discovery)
    for py in list(STAGE.rglob("*.py")):
        if py.stem != "__init__":
            py.unlink()

    print("Built .pyc-only fallback (install Cython + MSVC for .pyd binaries).")


# ── Main setup ────────────────────────────────────────────────────────────


def main():
    clean_staging()

    # ── Stage packages ──

    # 1. rag_core (from the external rag_core project)
    rag_core_src = RAG_CORE_ROOT / "rag_core"
    if not rag_core_src.exists():
        print(f"ERROR: rag_core not found at {rag_core_src}")
        print("       Set RAG_CORE_ROOT or copy rag_core/ into dist_build/")
        sys.exit(1)
    stage_package(rag_core_src, "rag_core")

    # 2. local_llm (from project root)
    local_llm_src = PROJECT_ROOT / "local_llm"
    stage_package(
        local_llm_src,
        "local_llm",
        files=[
            "__init__.py",
            "llama_cpp_manager.py",
            "model_card.py",
            "local_llm_manager.py",
            "enhanced_model_card.py",
            # Exclude demo_model_expertise.py — it's a dev-only demo
        ],
    )

    # 3. Core/ (models, exceptions, interfaces, services)
    core_src = PROJECT_ROOT / "Core"
    stage_package(core_src, "Core")

    # 4. Standalone modules → zenai_adapters package
    adapters_dest = STAGE / "zenai_adapters"
    adapters_dest.mkdir(parents=True, exist_ok=True)

    # Copy adapter modules
    for mod in ["llm_adapters.py", "adapter_factory.py", "rag_integration.py"]:
        src = PROJECT_ROOT / mod
        if src.exists():
            shutil.copy2(src, adapters_dest / mod)

    # Write __init__.py that re-exports everything
    (adapters_dest / "__init__.py").write_text(
        '"""zenai_adapters — LLM adapter layer + RAG integration."""\n'
        "try:\n"
        "    from .llm_adapters import LLMFactory, LLMRequest, LLMResponse, LLMProvider\n"
        "except ImportError:\n"
        "    pass\n"
        "try:\n"
        "    from .adapter_factory import create_adapter, ADAPTER_MAP\n"
        "except ImportError:\n"
        "    pass\n"
        "try:\n"
        "    from .rag_integration import RAGIntegration, get_rag\n"
        "except ImportError:\n"
        "    pass\n",
        encoding="utf-8",
    )

    # ── Create top-level zenai_core __init__.py ──
    (STAGE / "__init__.py").write_text(
        '"""zenai_core — Compiled ZenAI libraries (no source)."""\n__version__ = \'1.0.0\'\n',
        encoding="utf-8",
    )

    # ── Build ──
    os.chdir(str(STAGE))

    if USE_CYTHON:
        extensions = collect_extensions()
        print(f"\nCompiling {len(extensions)} modules with Cython...\n")
        setup(
            name="zenai_core",
            version="1.0.0",
            description="ZenAI Core Libraries — RAG, LLM adapters, model management (compiled)",
            author="ZenAI Team",
            packages=find_packages(where="."),
            package_dir={"": "."},
            ext_modules=cythonize(
                extensions,
                compiler_directives={
                    "language_level": "3",
                    "boundscheck": False,
                    "wraparound": False,
                },
                nthreads=os.cpu_count() or 4,
            ),
            cmdclass={"build_ext": build_ext},
            python_requires=">=3.10",
            install_requires=[
                # Minimal runtime deps (heavy ML libs are optional)
                "numpy>=1.24",
            ],
            extras_require={
                "full": [
                    "sentence-transformers>=3.0.0",
                    "rank-bm25>=0.2.2",
                    "torch>=2.0",
                    "qdrant-client>=1.7",
                    "psutil>=5.9",
                    "httpx>=0.24",
                ],
                "llm": [
                    "psutil>=5.9",
                    "httpx>=0.24",
                ],
                "rag": [
                    "sentence-transformers>=3.0.0",
                    "rank-bm25>=0.2.2",
                    "qdrant-client>=1.7",
                ],
            },
            zip_safe=False,
        )
    else:
        build_pyc_fallback()
        setup(
            name="zenai_core",
            version="1.0.0",
            description="ZenAI Core Libraries (bytecode only)",
            packages=find_packages(where="."),
            package_dir={"": "."},
            # Include .pyc files in the wheel
            package_data={
                "": ["*.pyc"],
                "Core": ["*.pyc"],
                "Core.interfaces": ["*.pyc"],
                "Core.services": ["*.pyc"],
                "local_llm": ["*.pyc"],
                "rag_core": ["*.pyc"],
                "zenai_adapters": ["*.pyc"],
            },
            python_requires=">=3.10",
            install_requires=["numpy>=1.24"],
            zip_safe=False,
        )


if __name__ == "__main__":
    main()
