import os
import sys
import time
import shutil
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

URL = "https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct/resolve/main/model.safetensors"
MODELS_DIR = Path(__file__).resolve().parent.parent / "models" / "qwen"
MODELS_DIR.mkdir(parents=True, exist_ok=True)
TARGET_FILE = MODELS_DIR / "model.safetensors"
PARTS_DIR = MODELS_DIR / ".parts"
PARTS_DIR.mkdir(parents=True, exist_ok=True)

NUM_WORKERS = 16
CHUNK_SIZE = 15 * 1024 * 1024  # 15MB chunks
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

def get_file_size(url):
    req = urllib.request.Request(url, headers=HEADERS, method="HEAD")
    with urllib.request.urlopen(req) as resp:
        return int(resp.headers.get("Content-Length", 0))

def download_chunk(url, start, end, chunk_id, progress_tracker):
    part_file = PARTS_DIR / f"chunk_{chunk_id:04d}.part"
    expected_len = end - start + 1
    
    if part_file.exists() and part_file.stat().st_size == expected_len:
        progress_tracker["downloaded"] += expected_len
        return True

    chunk_headers = {**HEADERS, "Range": f"bytes={start}-{end}"}
    req = urllib.request.Request(url, headers=chunk_headers)
    
    max_retries = 5
    for attempt in range(max_retries):
        try:
            with urllib.request.urlopen(req, timeout=45) as resp:
                data = resp.read()
                if len(data) != expected_len:
                    raise IOError(f"Incomplete read: got {len(data)}, expected {expected_len}")
                with open(part_file, "wb") as f:
                    f.write(data)
                progress_tracker["downloaded"] += len(data)
                return True
        except Exception as e:
            if attempt == max_retries - 1:
                print(f"\nChunk {chunk_id} ({start}-{end}) failed after {max_retries} attempts: {e}", flush=True)
                raise e
            time.sleep(1)

def main():
    total_size = get_file_size(URL)
    print(f"Total model size: {total_size / (1024*1024):.1f} MB ({total_size} bytes)")

    chunks = []
    chunk_id = 0
    for start in range(0, total_size, CHUNK_SIZE):
        end = min(start + CHUNK_SIZE - 1, total_size - 1)
        chunks.append((start, end, chunk_id))
        chunk_id += 1

    print(f"Split into {len(chunks)} chunks across {NUM_WORKERS} parallel threads...")
    progress_tracker = {"downloaded": 0}

    start_time = time.time()
    with ThreadPoolExecutor(max_workers=NUM_WORKERS) as executor:
        futures = [
            executor.submit(download_chunk, URL, start, end, c_id, progress_tracker)
            for start, end, c_id in chunks
        ]

        while any(not f.done() for f in futures):
            downloaded = progress_tracker["downloaded"]
            percent = (downloaded / total_size) * 100
            elapsed = time.time() - start_time
            speed = (downloaded / (1024 * 1024)) / (elapsed + 1e-5)
            print(f"Downloaded: {downloaded / (1024*1024):.1f} MB / {total_size / (1024*1024):.1f} MB ({percent:.1f}%) - Speed: {speed:.2f} MB/s", flush=True)
            time.sleep(2)

        for f in futures:
            f.result()

    print(f"\nAll chunks downloaded in {time.time() - start_time:.1f}s. Assembling final model.safetensors...")
    with open(TARGET_FILE, "wb") as outfile:
        for _, _, c_id in chunks:
            part_file = PARTS_DIR / f"chunk_{c_id:04d}.part"
            with open(part_file, "rb") as infile:
                shutil.copyfileobj(infile, outfile, length=1024*1024)
            part_file.unlink()

    if PARTS_DIR.exists():
        shutil.rmtree(PARTS_DIR, ignore_errors=True)

    print(f"Model assembled successfully! Final file size: {TARGET_FILE.stat().st_size} bytes.")

if __name__ == "__main__":
    main()
