import sys
from pathlib import Path

# Add backend to sys.path
backend_path = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from app.services.llm_service import llm_service
from app.schemas.generation import GenerateRequest

print("Testing LocalLLMService Device Detection...")
device_info = llm_service.get_device_info()
print(f"Device Info: {device_info}")

test_req = GenerateRequest(
    prompt="Create a 15 second cinematic video of a futuristic electric sports car speeding through Tokyo neon night streets in rain.",
    duration=15,
    aspect_ratio="16:9",
    language="English"
)

print("\nRunning test generation with Qwen2.5-1.5B-Instruct...")
plan = llm_service.generate_plan(test_req)
print("\n--- GENERATED PLAN ---")
print(f"Title: {plan.title}")
print(f"Style: {plan.style}")
print(f"Total Duration: {plan.total_duration}s")
print(f"Scenes ({len(plan.scenes)}):")
for s in plan.scenes:
    print(f"  Scene #{s.scene_number} ({s.duration}s): {s.description}")
    print(f"    Video Prompt: {s.video_prompt}")
print(f"Voiceover: {plan.voiceover}")

print("\nTesting model unloading...")
llm_service.unload_model()
print("Unload completed successfully!")
