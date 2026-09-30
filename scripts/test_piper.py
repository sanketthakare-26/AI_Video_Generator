"""
Piper TTS Test Script
Runs local neural text-to-speech inference and validates the generated WAV file.
"""
import sys
import time
import wave
from pathlib import Path

# Add backend to Python path
backend_path = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from app.config.settings import settings
from app.services.tts_service import LocalTTSService

TEST_TEXT = (
    "Welcome to our AI video generator. "
    "This video was created using a local artificial intelligence system."
)

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "generated" / "audio" / "piper"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_FILE = OUTPUT_DIR / "test_voice.wav"

print("=" * 64)
print("Piper TTS Local Voice Generation Test")
print("=" * 64)
print(f"Python       : {sys.version}")
print(f"Model Path   : {settings.piper_model_path}")
print(f"Sample Rate  : {settings.piper_sample_rate} Hz")
print(f"Target Output: {OUTPUT_FILE}")
print(f"Input Text   : \"{TEST_TEXT}\"")
print("-" * 64)

svc = LocalTTSService()

# 1. Load Model
print("\n[1/3] Loading Piper voice model...")
t0 = time.time()
try:
    svc.load_model()
    load_time = time.time() - t0
    print(f"  [OK] Model loaded in {load_time:.2f}s")
    print(f"  Model File  : {svc.get_model_path()}")
    print(f"  Model Size  : {svc.get_model_path().stat().st_size / (1024*1024):.2f} MB")
except Exception as exc:
    print(f"  [ERROR] Failed to load model: {exc}")
    sys.exit(1)

# 2. Generate Audio
print("\n[2/3] Generating speech audio...")
result = svc.generate_audio(
    text=TEST_TEXT,
    output_path=OUTPUT_FILE,
    language="en",
)

# 3. Validate and Inspect WAV
print("\n[3/3] Inspecting Generated WAV Audio...")
print("-" * 64)

if not result.get("success"):
    print(f"  [ERROR] Generation failed: {result.get('error')}")
    print(f"  Error Type: {result.get('error_type')}")
    sys.exit(1)

if not OUTPUT_FILE.exists() or OUTPUT_FILE.stat().st_size == 0:
    print("  [ERROR] Output file does not exist or is 0 bytes.")
    sys.exit(1)

file_size_bytes = OUTPUT_FILE.stat().st_size
file_size_kb = file_size_bytes / 1024

with wave.open(str(OUTPUT_FILE), "rb") as wf:
    channels = wf.getnchannels()
    sample_width = wf.getsampwidth()
    sample_rate = wf.getframerate()
    num_frames = wf.getnframes()
    duration = num_frames / float(sample_rate)

print(f"  Status        : SUCCESS")
print(f"  Output Path   : {OUTPUT_FILE}")
print(f"  File Size     : {file_size_kb:.2f} KB ({file_size_bytes} bytes)")
print(f"  Channels      : {channels} ({'Mono' if channels == 1 else 'Stereo'})")
print(f"  Sample Width  : {sample_width * 8}-bit ({sample_width} bytes per sample)")
print(f"  Sample Rate   : {sample_rate} Hz")
print(f"  Number Frames : {num_frames}")
print(f"  Duration      : {duration:.2f} seconds")
print(f"  Load Time     : {result.get('model_load_time')}s")
print(f"  Gen Time      : {result.get('generation_time')}s")
print(f"  Total Time    : {result.get('total_time')}s")

# Unload model
print("\n[Cleanup] Unloading Piper model...")
svc.unload_model()
print("  [OK] Model unloaded.")

print("\n" + "=" * 64)
if duration > 0 and file_size_bytes > 0:
    print(f"TEST PASSED - Real WAV file generated ({duration:.2f}s, {file_size_kb:.1f} KB)")
else:
    print("TEST FAILED - Invalid audio parameters.")
print("=" * 64)
