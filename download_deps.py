
import os
import requests
import zipfile
import sys
from pathlib import Path

def download_llama():
    print("Finding latest llama.cpp release...")
    try:
        response = requests.get("https://api.github.com/repos/ggerganov/llama.cpp/releases/latest")
        data = response.json()
        
        assets = data.get("assets", [])
        target_url = None
        
        target_url = None
        candidates = []
        
        for asset in assets:
            name = asset["name"].lower()
            # Must start with llama- to match the full binary package (not cudart libs)
            if name.startswith("llama-") and "bin-win" in name and "x64" in name and ".zip" in name:
                candidates.append(asset)
        
        # Priority 1: CUDA 12 (Modern NVIDIA)
        for c in candidates:
            if "cuda-12" in c["name"].lower():
                target_url = c["browser_download_url"]
                print(f"Selected CUDA 12 build: {c['name']}")
                break
                
        # Priority 2: CPU (Fall safe) (Replaces old AVX2 logic)
        if not target_url:
            for c in candidates:
                if "cpu" in c["name"].lower():
                    target_url = c["browser_download_url"]
                    print(f"Selected CPU build: {c['name']}")
                    break
        
        if not target_url:
            print("Could not auto-match binary. Please download manually from:")
            print(data.get("html_url"))
            return

        print(f"Downloading {target_url}...")
        r = requests.get(target_url, stream=True)
        
        with open("llama_temp.zip", "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
                
        print("Extracting all files...")
        _bin = Path("_bin")
        _bin.mkdir(exist_ok=True)
        
        with zipfile.ZipFile("llama_temp.zip", 'r') as z:
            z.extractall(_bin)
            print(f"Extracted {len(z.namelist())} files to {_bin}")
                    
        os.remove("llama_temp.zip")
        print("Done! Engine ready.")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    download_llama()
