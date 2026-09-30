"""
Full Qwen video plan diagnostic — uses the EXACT same settings as the production llm_service.
Measures load time, token count, generation time, and validates the JSON output.
"""
import gc
import sys
import time
from pathlib import Path

backend_path = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_path))

import torch
from app.config.settings import settings
from app.services.llm_service import llm_service
from app.schemas.generation import GenerateRequest

print("=" * 60)
print("QWEN VIDEO PLAN DIAGNOSTIC (Production Settings)")
print("=" * 60)
print(f"Device: {'CUDA' if torch.cuda.is_available() else 'CPU (cpu-only PyTorch)'}")
print(f"MAX_NEW_TOKENS: {llm_service.MAX_NEW_TOKENS} (greedy decode)")
print()

request = GenerateRequest(
    prompt="A futuristic electric car driving through a modern city at sunset.",
    duration=15,
    aspect_ratio="16:9",
    language="English",
)

print("[Step 1] Loading Qwen model...")
t0 = time.time()
llm_service.load_model()
load_time = time.time() - t0
print(f"  Load time: {load_time:.2f}s")

print("\n[Step 2] Generating video plan...")
t1 = time.time()
plan = llm_service.generate_plan(request)
gen_time = time.time() - t1

print("\n[Step 3] Plan Output:")
print(f"  Title      : {plan.title}")
print(f"  Style      : {plan.style}")
print(f"  Duration   : {plan.total_duration}s")
print(f"  Scenes     : {len(plan.scenes)}")
for s in plan.scenes:
    vp_len = len(s.video_prompt)
    print(f"    Scene {s.scene_number}: {s.duration}s | desc={len(s.description)} chars | vp={vp_len} chars")
print(f"  Voiceover  : {len(plan.voiceover)} chars")
print()

print("[Step 4] Unloading model...")
llm_service.unload_model()
print("  Unloaded.")

total_time = load_time + gen_time
print("\n" + "=" * 60)
print("RESULTS SUMMARY")
print("=" * 60)
print(f"Model Load   : {load_time:.2f}s")
print(f"Generation   : {gen_time:.2f}s")
print(f"Total        : {total_time:.2f}s")
print(f"Scenes       : {len(plan.scenes)}")
print(f"Voiceover    : {plan.voiceover[:80]}...")
print("=" * 60)

if len(plan.scenes) >= 2:
    print("\nSTATUS: PASS - Plan generated successfully with multiple scenes.")
else:
    print("\nSTATUS: WARN - Only 1 scene generated; check prompt compactness.")
