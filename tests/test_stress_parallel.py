import pytest
import subprocess
import sys
import os
from pathlib import Path

# --- Config ---
# Path to the model used for testing
MODEL_PATH = Path("C:/AI/Models/qwen2.5-0.5b-instruct-q5_k_m.gguf")
ROOT_DIR = Path(__file__).parent.parent.resolve()
BIN_DIR = ROOT_DIR / "_bin"
PARALLEL_EXE = BIN_DIR / "llama-parallel.exe"


def test_parallel_stress():
    """
    Run llama-parallel.exe to stress test the decoding engine.
    This simulates multiple users generating text simultaneously.
    """
    if not PARALLEL_EXE.exists():
        pytest.fail(f"llama-parallel.exe not found at {PARALLEL_EXE}")

    if not MODEL_PATH.exists():
        pytest.skip(f"Test Model not found at {MODEL_PATH}")

    # [X-Ray auto-fix] print(f"\n[Stress] Running Parallel Decoding Test...")
    # [X-Ray auto-fix] print(f"Model: {MODEL_PATH.name}")
    # 4 Parallel Sequences, 128 tokens prediction
    # This stresses KV cache and compute.
    cmd = [
        str(PARALLEL_EXE),
        "--model",
        str(MODEL_PATH),
        "-ns",
        "4",  # 4 Concurrent Sequences
        "-n",
        "64",  # Generate 64 tokens each
        "-c",
        "2048",  # Context size
        "-p",
        "The future of AI is",  # Prompt
        "--temp",
        "0.7",
    ]

    # Run synchronously
    try:
        result = subprocess.run(
            cmd,
            cwd=BIN_DIR,
            capture_output=True,
            text=True,
            timeout=120,  # 2 minute timeout,
            shell=False,
        )

        # Check exit code
        if result.returncode != 0:
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
            pytest.fail(f"llama-parallel failed with code {result.returncode}")

        # Verify output contains decoding stats or completion
        # Ideally check for "decoded" or specific log lines.
        # But return code 0 usually means success for this tool.
        # [X-Ray auto-fix] print(f"[Stress] Success! Output sample:\n{result.stdout[:200]}...")
    except subprocess.TimeoutExpired:
        pytest.fail("Test timed out! Parallel decoding took too long.")
