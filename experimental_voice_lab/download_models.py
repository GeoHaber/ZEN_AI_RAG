# download_models.py
"""
Automate downloading recommended LLMs for benchmarking with llama.cpp.
Models are saved to C:/AI/Models.
"""
import os
import requests

MODELS = [
    {
        "name": "phi-2-2.7b.Q4_K_M.gguf",
        "url": "https://huggingface.co/TheBloke/phi-2-GGUF/resolve/main/phi-2.Q4_K_M.gguf"
    },
    {
        "name": "tinyllama-1.1b-chat.Q4_K_M.gguf",
        "url": "https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF/resolve/main/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf"
    },
    {
        "name": "mistral-7b-instruct-v0.2.Q4_K_M.gguf",
        "url": "https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF/resolve/main/mistral-7b-instruct-v0.2.Q4_K_M.gguf"
    },
    {
        "name": "qwen1.5-1.8b-chat.Q4_K_M.gguf",
        "url": "https://huggingface.co/TheBloke/Qwen1.5-1.8B-Chat-GGUF/resolve/main/qwen1_5-1_8b-chat.Q4_K_M.gguf"
    },
    {
        "name": "qwen1.5-3b-chat.Q4_K_M.gguf",
        "url": "https://huggingface.co/TheBloke/Qwen1.5-3B-Chat-GGUF/resolve/main/qwen1_5-3b-chat.Q4_K_M.gguf"
    },
    {
        "name": "llama-2-3b-chat.Q4_K_M.gguf",
        "url": "https://huggingface.co/TheBloke/Llama-2-3B-Chat-GGUF/resolve/main/llama-2-3b-chat.Q4_K_M.gguf"
    },
]

MODEL_DIR = "C:/AI/Models"
os.makedirs(MODEL_DIR, exist_ok=True)


def download_model(model):
    out_path = os.path.join(MODEL_DIR, model["name"])
    if os.path.exists(out_path):
        print(f"Already exists: {model['name']}")
        return
    print(f"Downloading {model['name']}...")
    with requests.get(model["url"], stream=True) as r:
        r.raise_for_status()
        with open(out_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
    print(f"Downloaded: {model['name']}")


def main():
    for model in MODELS:
        try:
            download_model(model)
        except Exception as e:
            print(f"Failed to download {model['name']}: {e}")

if __name__ == "__main__":
    main()
