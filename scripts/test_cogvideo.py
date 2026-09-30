"""
CogVideoX-2B Test Script
Runs end-to-end: loads model, generates one 6-second MP4 clip, reports results.
"""
import sys
import time
import platform
from pathlib import Path

# Make backend importable
backend_path = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_path))

import torch
from app.config.settings import settings
from app.services.video_service import CogVideoXService

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "generated" / "videos" / "cogvideox"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_FILE = OUTPUT_DIR / "cogvideox_test.mp4"

TEST_PROMPT = (
    "A modern electric car driving smoothly on a clean city road at sunset, "
    "cinematic camera movement, realistic lighting, detailed environment, smooth motion."
)

print("=" * 64)
print("CogVideoX-2B Local Video Generation Test")
print("=" * 64)
print(f"Python    : {sys.version}")
print(f"Platform  : {platform.system()} {platform.release()}")
print(f"PyTorch   : {torch.__version__}")
print(f"CUDA      : {torch.cuda.is_available()}")
if torch.cuda.is_available():
    props = torch.cuda.get_device_properties(0)
    vram_total = props.total_memory / 1024**3
    vram_free = (props.total_memory - torch.cuda.memory_reserved(0)) / 1024**3
    print(f"GPU       : {torch.cuda.get_device_name(0)}")
    print(f"VRAM      : {vram_total:.2f} GB total | {vram_free:.2f} GB free")
print(f"Model     : {settings.cogvideo_model_id}")
print(f"Frames    : {settings.cogvideo_num_frames} frames @ {settings.cogvideo_fps} FPS")
print(f"Resolution: {settings.cogvideo_width}x{settings.cogvideo_height}")
print(f"Steps     : {settings.cogvideo_num_inference_steps}")
print(f"Output    : {OUTPUT_FILE}")
print("-" * 64)

svc = CogVideoXService()

print("\n[1/4] Loading CogVideoX-2B model with memory optimisations...")
t0 = time.time()
svc.load_model()
load_time = time.time() - t0
print(f"      Model loaded in {load_time:.1f}s")

print("\n[2/4] Generating video clip...")
result = svc.generate_video(
    prompt=TEST_PROMPT,
    output_path=OUTPUT_FILE,
    num_inference_steps=settings.cogvideo_num_inference_steps,
    guidance_scale=settings.cogvideo_guidance_scale,
    num_frames=settings.cogvideo_num_frames,
    fps=settings.cogvideo_fps,
    width=settings.cogvideo_width,
    height=settings.cogvideo_height,
)

print("\n[3/4] Generation Result:")
print("-" * 64)
if result.get("success"):
    print(f"  Status           : SUCCESS ✓")
    print(f"  Output file      : {result['video_path']}")
    print(f"  File size        : {result['file_size_bytes'] / 1024:.1f} KB")
    print(f"  Video duration   : {result['duration']:.2f}s")
    print(f"  FPS              : {result['fps']}")
    print(f"  Resolution       : {result['width']}x{result['height']}")
    print(f"  Model load time  : {result['model_load_time']:.1f}s")
    print(f"  Generation time  : {result['generation_time']:.1f}s")
    print(f"  Total time       : {result['total_time']:.1f}s")
else:
    print(f"  Status           : FAILED ✗")
    print(f"  Error type       : {result.get('error_type')}")
    print(f"  Error            : {result.get('error')}")
    if result.get("device_info"):
        di = result["device_info"]
        print(f"  VRAM total       : {di.get('vram_total_gb')} GB")
        print(f"  VRAM allocated   : {di.get('vram_allocated_gb')} GB")
        print(f"  VRAM free        : {di.get('vram_free_gb')} GB")

if torch.cuda.is_available():
    print(f"\n  CUDA after gen   : allocated={torch.cuda.memory_allocated(0)/1024**2:.1f} MB, "
          f"reserved={torch.cuda.memory_reserved(0)/1024**2:.1f} MB")

print("\n[4/4] Unloading model...")
svc.unload_model()
print("      Model unloaded.")

if torch.cuda.is_available():
    print(f"      CUDA after unload: allocated={torch.cuda.memory_allocated(0)/1024**2:.1f} MB, "
          f"reserved={torch.cuda.memory_reserved(0)/1024**2:.1f} MB")

print("\n" + "=" * 64)
if result.get("success") and Path(result["video_path"]).exists():
    file_size = Path(result["video_path"]).stat().st_size
    print(f"TEST PASSED — {OUTPUT_FILE.name} ({file_size} bytes)")
else:
    print("TEST FAILED — No valid MP4 was produced.")
    print(f"Reason: {result.get('error')}")
print("=" * 64)
