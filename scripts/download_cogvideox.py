"""
CogVideoX-2b full model download script.
Redirects HF cache to D: drive where there is 171 GB free space.
Downloads the full model including text_encoder and transformer weights.
"""
import os
import sys
import time
from pathlib import Path

# ── Redirect HF cache to D: drive BEFORE importing transformers/diffusers ──
HF_CACHE_DIR = r"D:\AIvideoGenerator_main\models\hf_cache"
os.environ["HF_HOME"] = HF_CACHE_DIR
os.environ["HUGGINGFACE_HUB_CACHE"] = HF_CACHE_DIR + r"\hub"
os.environ["TRANSFORMERS_CACHE"] = HF_CACHE_DIR + r"\hub"

Path(HF_CACHE_DIR).mkdir(parents=True, exist_ok=True)

print("=" * 60)
print("CogVideoX-2b Model Download")
print("=" * 60)
print(f"HF Cache: {HF_CACHE_DIR}")
print()

from huggingface_hub import snapshot_download

MODEL_ID = "THUDM/CogVideoX-2b"
print(f"Downloading: {MODEL_ID}")
print("This will download ~9-13 GB. Please wait...")
print()

t0 = time.time()
try:
    local_dir = snapshot_download(
        repo_id=MODEL_ID,
        cache_dir=HF_CACHE_DIR + r"\hub",
        local_dir=None,
        ignore_patterns=["*.msgpack", "flax_model*", "tf_model*", "rust_model*"],
    )
    elapsed = time.time() - t0
    print()
    print("=" * 60)
    print(f"SUCCESS: Downloaded to {local_dir}")
    print(f"Time: {elapsed/60:.1f} minutes")
    print("=" * 60)
    print()
    print("IMPORTANT: Update your .env or settings to set:")
    print(f'  HF_HOME={HF_CACHE_DIR}')
    print()
    print("Now verify files:")
    from pathlib import Path as P
    for f in sorted(P(local_dir).rglob("*.safetensors")):
        print(f"  {f.relative_to(local_dir)} ({f.stat().st_size/1e9:.2f} GB)")
except KeyboardInterrupt:
    print("\nDownload interrupted by user. Re-run to resume.")
    sys.exit(1)
except Exception as e:
    print(f"\nERROR: {e}")
    sys.exit(1)
