import requests
import json
import time

print("Testing POST /api/generate with new compact LLM settings...")
t0 = time.time()
resp = requests.post("http://127.0.0.1:8000/api/generate", json={
    "prompt": "A futuristic electric car driving through a modern city at sunset.",
    "duration": 15,
    "aspect_ratio": "16:9",
    "language": "English"
}, timeout=300)
elapsed = time.time() - t0

print(f"Status: {resp.status_code} in {elapsed:.1f}s")
data = resp.json()
plan = data.get("plan", {})
print(f"Title: {plan.get('title')}")
print(f"Style: {plan.get('style')}")
scenes = plan.get("scenes", [])
print(f"Scenes: {len(scenes)}")
for s in scenes:
    print(f"  Scene {s['scene_number']}: {s['duration']}s | {s['description'][:60]}")
vo = plan.get("voiceover", "")
print(f"Voiceover: {vo[:100]}...")
print()
print(f"=== RESULT: Qwen completed in {elapsed:.1f}s ({'PASS' if elapsed < 300 else 'SLOW'}) ===")
