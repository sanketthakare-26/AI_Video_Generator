import urllib.request
import os
import sys
from pathlib import Path

models_dir = Path(__file__).resolve().parent.parent / "models" / "qwen"
models_dir.mkdir(parents=True, exist_ok=True)
target_file = models_dir / "model.safetensors"

url = "https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct/resolve/main/model.safetensors"

if target_file.exists() and target_file.stat().st_size > 3000000000:
    print(f"{target_file} already downloaded and verified ({target_file.stat().st_size} bytes).")
    sys.exit(0)

print(f"Downloading {url} to {target_file}...")

def reporthook(blocknum, blocksize, totalsize):
    readsofar = blocknum * blocksize
    if totalsize > 0:
        percent = readsofar * 100 / totalsize
        if blocknum % 2000 == 0 or readsofar >= totalsize:
            print(f"Downloaded: {readsofar / (1024*1024):.1f} MB / {totalsize / (1024*1024):.1f} MB ({percent:.1f}%)", flush=True)

urllib.request.urlretrieve(url, str(target_file), reporthook)
print("Download finished successfully!", flush=True)
