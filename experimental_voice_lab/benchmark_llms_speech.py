# benchmark_llms_speech.py
"""
Benchmark LLMs (in C:/AI/Models) for speed and accuracy on technical questions of various lengths.
Uses llama.cpp to generate answers for each prompt.
"""

import time
import os
from llama_cpp import Llama

MODELS = [
    {
        "name": "Phi-2-2.7B-q4",
        "file": "C:/AI/Models/phi-2-2.7b.Q4_K_M.gguf"
    },
    {
        "name": "TinyLlama-1.1B-q4",
        "file": "C:/AI/Models/tinyllama-1.1b-chat.Q4_K_M.gguf"
    },
    {
        "name": "Mistral-7B-Instruct-q4",
        "file": "C:/AI/Models/mistral-7b-instruct-v0.2.Q4_K_M.gguf"
    },
]


N_TOKENS = 128

PROMPTS = [
    {
        "desc": "Short technical question",
        "prompt": "What is the time complexity of binary search?"
    },
    {
        "desc": "Medium technical question",
        "prompt": "Explain the difference between a Python list and a tuple, and give an example where a tuple is preferred."
    },
    {
        "desc": "Long technical question",
        "prompt": "Describe how a transformer neural network works, including the concepts of self-attention, positional encoding, and how it differs from a recurrent neural network."
    },
]


def run_llama_python(model_file, prompt, n_predict=N_TOKENS):
    t0 = time.time()
    try:
        llm = Llama(model_path=model_file, n_ctx=2048, n_threads=8)
        output = llm(prompt, max_tokens=n_predict, stop=["\n"])
        elapsed = time.time() - t0
        return output["choices"][0]["text"].strip(), elapsed
    except Exception as e:
        return f"ERROR: {e}", -1

def main():
    results = []
    for m in MODELS:
        if not os.path.exists(m['file']):
            print(f"Model file not found: {m['file']}")
            continue
        for p in PROMPTS:
            print(f"\n=== {m['name']} | {p['desc']} ===")
            output, elapsed = run_llama_python(m['file'], p['prompt'])
            print(f"Time: {elapsed:.2f}s\nOutput: {output[:400]}\n")
            results.append((m['name'], p['desc'], elapsed, output))
    # Save results
    with open("llm_speech_benchmark_results.txt", "w", encoding="utf-8") as f:
        for name, desc, elapsed, output in results:
            f.write(f"=== {name} | {desc} ===\nTime: {elapsed:.2f}s\nOutput: {output}\n\n")
    print("\nBenchmark complete. Results saved to llm_speech_benchmark_results.txt")

if __name__ == "__main__":
    main()
