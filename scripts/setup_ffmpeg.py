"""
Setup FFmpeg & FFprobe for Windows.
Downloads the official static release of FFmpeg (including ffmpeg.exe and ffprobe.exe)
and places them in tools/ffmpeg/bin.
"""
import os
import sys
import time
import zipfile
import urllib.request
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
TOOLS_DIR = ROOT_DIR / "tools" / "ffmpeg" / "bin"
TOOLS_DIR.mkdir(parents=True, exist_ok=True)

FFMPEG_EXE = TOOLS_DIR / "ffmpeg.exe"
FFPROBE_EXE = TOOLS_DIR / "ffprobe.exe"

# Official static build from Gyan.dev / GitHub releases
DOWNLOAD_URL = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
FALLBACK_URL = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}


def download_and_extract():
    if FFMPEG_EXE.exists() and FFPROBE_EXE.exists():
        print(f"[OK] FFmpeg already installed:")
        print(f"  ffmpeg : {FFMPEG_EXE}")
        print(f"  ffprobe: {FFPROBE_EXE}")
        return True

    zip_dest = ROOT_DIR / "tools" / "ffmpeg.zip"
    print(f"[>>] Downloading official FFmpeg + FFprobe static binaries for Windows...")
    print(f"     URL: {DOWNLOAD_URL}")

    urls = [DOWNLOAD_URL, FALLBACK_URL]
    download_success = False

    for url in urls:
        try:
            print(f"     Trying {url}...")
            req = urllib.request.Request(url, headers=HEADERS)
            t_start = time.time()
            with urllib.request.urlopen(req, timeout=120) as resp:
                total = int(resp.headers.get("Content-Length", 0))
                downloaded = 0
                block_size = 1024 * 128
                with open(zip_dest, "wb") as f:
                    while True:
                        chunk = resp.read(block_size)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total > 0:
                            pct = (downloaded / total) * 100
                            mb = downloaded / (1024 * 1024)
                            total_mb = total / (1024 * 1024)
                            speed = mb / max(time.time() - t_start, 0.001)
                            print(f"\r     Progress: {mb:.1f}/{total_mb:.1f} MB ({pct:.1f}%) - {speed:.2f} MB/s", end="", flush=True)
                print()
                download_success = True
                break
        except Exception as exc:
            print(f"\n     [WARN] Failed to download from {url}: {exc}")
            if zip_dest.exists():
                zip_dest.unlink()

    if not download_success or not zip_dest.exists():
        print("[ERROR] Could not download FFmpeg zip.")
        return False

    print(f"[>>] Extracting ffmpeg.exe and ffprobe.exe to {TOOLS_DIR}...")
    try:
        with zipfile.ZipFile(zip_dest, "r") as zf:
            for item in zf.namelist():
                filename = Path(item).name.lower()
                if filename in ["ffmpeg.exe", "ffprobe.exe"]:
                    dest_file = TOOLS_DIR / filename
                    with zf.open(item) as src, open(dest_file, "wb") as dst:
                        dst.write(src.read())
                    print(f"  [OK] Extracted: {dest_file} ({dest_file.stat().st_size / (1024*1024):.1f} MB)")

        if zip_dest.exists():
            zip_dest.unlink()

        return FFMPEG_EXE.exists() and FFPROBE_EXE.exists()
    except Exception as exc:
        print(f"[ERROR] Extraction failed: {exc}")
        return False


if __name__ == "__main__":
    ok = download_and_extract()
    if ok:
        print("\nFFmpeg and FFprobe are ready for use!")
        sys.exit(0)
    else:
        print("\nFFmpeg setup failed.")
        sys.exit(1)
