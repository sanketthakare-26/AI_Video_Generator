"""
Download Piper Voice Model (en_US-lessac-medium)
Downloads the ONNX voice model and JSON configuration from Hugging Face Hub (rhasspy/piper-voices).
"""
import os
import sys
import time
import urllib.request
from pathlib import Path

# Paths
ROOT_DIR = Path(__file__).resolve().parent.parent
MODELS_DIR = ROOT_DIR / "models" / "piper"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

MODEL_NAME = "en_US-lessac-medium"
ONNX_FILE = MODELS_DIR / f"{MODEL_NAME}.onnx"
JSON_FILE = MODELS_DIR / f"{MODEL_NAME}.onnx.json"

BASE_URL = "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium"
ONNX_URL = f"{BASE_URL}/{MODEL_NAME}.onnx"
JSON_URL = f"{BASE_URL}/{MODEL_NAME}.onnx.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}


def download_file_with_progress(url: str, dest_path: Path, desc: str) -> bool:
    """Download a file with visual progress tracking."""
    if dest_path.exists() and dest_path.stat().st_size > 0:
        size_mb = dest_path.stat().st_size / (1024 * 1024)
        print(f"  [OK] {desc} already exists ({size_mb:.2f} MB): {dest_path}")
        return True

    print(f"  [>>] Downloading {desc}...")
    print(f"      From: {url}")
    print(f"      To:   {dest_path}")

    try:
        req = urllib.request.Request(url, headers=HEADERS)
        t_start = time.time()
        
        with urllib.request.urlopen(req, timeout=60) as resp:
            total_size = int(resp.headers.get("Content-Length", 0))
            downloaded = 0
            block_size = 1024 * 64  # 64 KB
            
            temp_path = dest_path.with_suffix(dest_path.suffix + ".tmp")
            with open(temp_path, "wb") as f:
                while True:
                    chunk = resp.read(block_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    
                    if total_size > 0:
                        pct = (downloaded / total_size) * 100
                        mb = downloaded / (1024 * 1024)
                        total_mb = total_size / (1024 * 1024)
                        speed = mb / max(time.time() - t_start, 0.001)
                        print(f"\r      Progress: {mb:.2f}/{total_mb:.2f} MB ({pct:.1f}%) - {speed:.2f} MB/s", end="", flush=True)
                    else:
                        mb = downloaded / (1024 * 1024)
                        print(f"\r      Downloaded: {mb:.2f} MB", end="", flush=True)
            
            print()  # newline
            if temp_path.exists():
                if dest_path.exists():
                    dest_path.unlink()
                temp_path.rename(dest_path)
                
            elapsed = time.time() - t_start
            final_mb = dest_path.stat().st_size / (1024 * 1024)
            print(f"  [OK] Downloaded {desc} ({final_mb:.2f} MB in {elapsed:.1f}s)")
            return True

    except Exception as exc:
        print(f"\n  [ERROR] Error downloading {desc}: {exc}")
        temp_path = dest_path.with_suffix(dest_path.suffix + ".tmp")
        if temp_path.exists():
            temp_path.unlink()
        return False



def main():
    print("=" * 64)
    print("Piper TTS Model Downloader (en_US-lessac-medium)")
    print("=" * 64)
    print(f"Target Directory: {MODELS_DIR}")
    print()

    # 1. Download JSON Config
    ok_json = download_file_with_progress(JSON_URL, JSON_FILE, "JSON Config")
    if not ok_json:
        print("\nFailed to download JSON config. Exiting.")
        sys.exit(1)

    print()

    # 2. Download ONNX Model
    ok_onnx = download_file_with_progress(ONNX_URL, ONNX_FILE, "ONNX Model")
    if not ok_onnx:
        print("\nFailed to download ONNX voice model. Exiting.")
        sys.exit(1)

    print()
    print("=" * 64)
    print("Download Complete!")
    print(f"  ONNX Model:  {ONNX_FILE} ({ONNX_FILE.stat().st_size / (1024*1024):.2f} MB)")
    print(f"  JSON Config: {JSON_FILE} ({JSON_FILE.stat().st_size / 1024:.2f} KB)")
    print("=" * 64)


if __name__ == "__main__":
    main()
