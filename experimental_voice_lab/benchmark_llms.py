# benchmark_llms.py
"""
Benchmark multiple LLMs (quantized, llama.cpp compatible) for text generation speed and quality.
Models should be placed in C:/AI/Models/<model_name>.gguf
"""
import subprocess
import time
import os

MODELS = [
    {
        "name": "Phi-2-2.7B-q4",
        "file": "C:/AI/Models/phi-2-2.7b.Q4_K_M.gguf",
        "prompt": "Hello, how are you today?"
    },
    {
        "name": "TinyLlama-1.1B-q4",
        "file": "C:/AI/Models/tinyllama-1.1b-chat.Q4_K_M.gguf",
        "prompt": "Hello, how are you today?"
    },
    {
        "name": "Mistral-7B-Instruct-q4",
        "file": "C:/AI/Models/mistral-7b-instruct-v0.2.Q4_K_M.gguf",
        "prompt": "Hello, how are you today?"
    },
    {
        "name": "Qwen1.5-1.8B-q4",
        "file": "C:/AI/Models/qwen1.5-1.8b-chat.Q4_K_M.gguf",
        "prompt": "Hello, how are you today?"
    },
    {
        "name": "Qwen1.5-3B-q4",
        "file": "C:/AI/Models/qwen1.5-3b-chat.Q4_K_M.gguf",
        "prompt": "Hello, how are you today?"
    },
    {
        "name": "Llama-2-Chat-3B-q4",
        "file": "C:/AI/Models/llama-2-3b-chat.Q4_K_M.gguf",
        "prompt": "Hello, how are you today?"
    },
]

LLAMA_CPP_PATH = "C:/AI/llama.cpp/main.exe"  # Adjust if needed
N_TOKENS = 64


def run_llama_cpp(model_file, prompt, n_predict=N_TOKENS):
    cmd = [
        LLAMA_CPP_PATH,
        "-m", model_file,
        "-p", prompt,
        "-n", str(n_predict),
        "--log-disable"
    ]
    t0 = time.time()
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        elapsed = time.time() - t0
        output = result.stdout.strip()
        return output, elapsed
    except Exception as e:
        return f"ERROR: {e}", -1


def main():
    results = []
    for m in MODELS:
        print(f"\n=== Benchmarking {m['name']} ===")
        if not os.path.exists(m['file']):
            print(f"Model file not found: {m['file']}")
            results.append((m['name'], "NOT FOUND", -1))
            continue
        output, elapsed = run_llama_cpp(m['file'], m['prompt'])
        print(f"Time: {elapsed:.2f}s\nOutput: {output[:200]}...")
        results.append((m['name'], output, elapsed))
    # Save results
    with open("llm_benchmark_results.txt", "w", encoding="utf-8") as f:
        for name, output, elapsed in results:
            f.write(f"=== {name} ===\nTime: {elapsed:.2f}s\nOutput: {output}\n\n")
    print("\nBenchmark complete. Results saved to llm_benchmark_results.txt")

if __name__ == "__main__":
    main()
