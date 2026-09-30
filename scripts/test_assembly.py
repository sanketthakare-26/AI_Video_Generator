"""
FFmpeg Video Assembly Test Script.
Tests combining video clips + Piper voiceover audio + SRT subtitles into a final MP4.
Does NOT invoke Qwen, CogVideoX, or Piper during this test.
"""
import os
import subprocess
import sys
import time
from pathlib import Path

# Add backend to sys.path
backend_path = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from app.config.settings import settings
from app.services.video_assembly_service import video_assembly_service

ROOT_DIR = Path(__file__).resolve().parent.parent
VIDEOS_DIR = ROOT_DIR / "generated" / "videos" / "cogvideox"
VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
AUDIO_DIR = ROOT_DIR / "generated" / "audio" / "piper"
FINAL_DIR = ROOT_DIR / "generated" / "videos" / "final"
FINAL_DIR.mkdir(parents=True, exist_ok=True)

COGVIDEO_TEST_CLIP = VIDEOS_DIR / "cogvideox_test.mp4"
PIPER_TEST_AUDIO = AUDIO_DIR / "test_voice.wav"
OUTPUT_FINAL_MP4 = FINAL_DIR / "test_final_video.mp4"

TEST_VOICEOVER = (
    "Welcome to our AI video generator. "
    "This video was created using a local artificial intelligence system."
)

print("=" * 64)
print("FFmpeg Video Assembly Test (Standalone)")
print("=" * 64)

# 1. Verify FFmpeg & FFprobe
print("\n[1/4] Checking FFmpeg & FFprobe binaries...")
try:
    ffmpeg_exe = video_assembly_service.get_ffmpeg_path()
    ffprobe_exe = video_assembly_service.get_ffprobe_path()
    v_info = video_assembly_service.get_version()
    print(f"  [OK] FFmpeg : {v_info.get('ffmpeg_version')}")
    print(f"  [OK] FFprobe: {v_info.get('ffprobe_version')}")
except Exception as exc:
    print(f"  [ERROR] FFmpeg/FFprobe check failed: {exc}")
    sys.exit(1)

# 2. Check or prepare test video clip
print("\n[2/4] Checking input video and audio assets...")
if COGVIDEO_TEST_CLIP.exists() and COGVIDEO_TEST_CLIP.stat().st_size > 0:
    print(f"  [OK] Detected existing CogVideoX test clip: {COGVIDEO_TEST_CLIP}")
else:
    print(f"  [INFO] Generating standalone 6s test video pattern (720x480, 8 FPS) with FFmpeg...")
    # Generate a clean 6s synthetic test pattern without invoking AI models
    gen_pattern_cmd = [
        ffmpeg_exe,
        "-y",
        "-f", "lavfi",
        "-i", "testsrc=duration=6:size=720x480:rate=8",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-crf", "23",
        str(COGVIDEO_TEST_CLIP)
    ]
    res_pat = subprocess.run(gen_pattern_cmd, capture_output=True, text=True, check=False)
    if res_pat.returncode != 0:
        print(f"  [ERROR] Failed to create test pattern: {res_pat.stderr}")
        sys.exit(1)
    print(f"  [OK] Prepared test clip: {COGVIDEO_TEST_CLIP} ({COGVIDEO_TEST_CLIP.stat().st_size / 1024:.1f} KB)")

if PIPER_TEST_AUDIO.exists() and PIPER_TEST_AUDIO.stat().st_size > 0:
    print(f"  [OK] Detected existing Piper voice WAV: {PIPER_TEST_AUDIO} ({PIPER_TEST_AUDIO.stat().st_size / 1024:.1f} KB)")
else:
    print(f"  [ERROR] Piper voice WAV not found at {PIPER_TEST_AUDIO}. Please run scripts/test_piper.py first.")
    sys.exit(1)

# 3. Assemble Final Video
print("\n[3/4] Assembling Final MP4 (Video + Audio + Subtitles)...")
t0 = time.time()
result = video_assembly_service.assemble_video(
    video_files=[COGVIDEO_TEST_CLIP],
    audio_file=PIPER_TEST_AUDIO,
    output_mp4=OUTPUT_FINAL_MP4,
    voiceover_text=TEST_VOICEOVER,
    burn_subtitles=False,
    shortest=True,
)
elapsed = time.time() - t0

if not result.get("success"):
    print(f"  [ERROR] Assembly failed: {result.get('error')}")
    print(f"  Error Type: {result.get('error_type')}")
    sys.exit(1)

# 4. Inspect with FFprobe
print("\n[4/4] Inspecting Assembled Final Video with FFprobe...")
print("-" * 64)
try:
    meta = video_assembly_service.inspect_video(OUTPUT_FINAL_MP4)
    print(f"  Output File       : {OUTPUT_FINAL_MP4}")
    print(f"  File Size         : {meta.get('size_bytes') / 1024:.2f} KB ({meta.get('size_bytes')} bytes)")
    print(f"  Duration          : {meta.get('duration'):.2f} seconds")
    print(f"  Video Codec       : {meta.get('video_codec')}")
    print(f"  Audio Codec       : {meta.get('audio_codec')}")
    print(f"  Resolution        : {meta.get('width')}x{meta.get('height')}")
    print(f"  FPS               : {meta.get('fps')}")
    print(f"  Audio Sample Rate : {meta.get('sample_rate')} Hz")
    print(f"  Audio Channels    : {meta.get('channels')}")
    print(f"  SRT Subtitles     : {result.get('has_subtitles')} ({result.get('srt_path')})")
    print(f"  Assembly Time     : {elapsed:.2f}s")
except Exception as exc:
    print(f"  [ERROR] Inspection failed: {exc}")
    sys.exit(1)

print("\n" + "=" * 64)
if meta.get("has_video") and meta.get("has_audio") and meta.get("duration", 0) > 0:
    print(f"TEST PASSED - Final MP4 verified ({meta.get('duration'):.2f}s, {meta.get('video_codec')}/{meta.get('audio_codec')})")
else:
    print("TEST FAILED - Incomplete video/audio streams.")
print("=" * 64)
