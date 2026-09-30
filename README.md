# AI Video Generator

A local, low-resource AI video generation platform designed to run on Windows hardware (target specs: 8 GB RAM, NVIDIA RTX 2050 4 GB VRAM).

> **Current Status**: Task 5 Integrated. Local video assembly pipeline using **FFmpeg & FFprobe** is implemented, combining Qwen scene planning, CogVideoX video clips, Piper TTS voice narration, and SRT subtitles into a unified final MP4 video.

---

## 🎞️ Task 5: FFmpeg Final Video Assembly

### Purpose
Combines generated scene video clips, neural voiceover audio, and synchronized SRT subtitles into a final H.264 / AAC MP4 video.

### Pipeline Architecture
```
User Prompt
    ↓
Qwen2.5-1.5B-Instruct (Scripting & Scene Planning)
    ↓
CogVideoX-2B (Scene Video Clips)
    ↓
Piper TTS (Voiceover Narration WAV)
    ↓
FFmpeg (Final Assembly)
    ↓
Final MP4 Video (H.264 + AAC + Subtitles)
```

### Key Assembly Features
- **Scene Concatenation**: Merges multiple CogVideoX scene clips using the FFmpeg concat demuxer with automated re-encoding fallback.
- **Audio Integration**: Mixes Piper 22.05 kHz voiceover audio with video using AAC encoding (`-b:a 128k`, `-shortest`).
- **SRT Subtitle Generation**: Automatically parses narration script sentences and generates synchronized `.srt` subtitle tracks.
- **Optional Subtitle Hardcoding**: Configurable subtitle burning (`burn_subtitles=True/False`) directly into video frames.
- **Video Standard**: Output encoded in H.264 (`libx264`), `yuv420p` pixel format, CRF 23, for maximum cross-platform compatibility.

### Verification Commands
```bash
# Check FFmpeg binaries
tools/ffmpeg/bin/ffmpeg.exe -version

# Run standalone assembly test
python scripts/test_assembly.py
```

Output:
`generated/videos/final/test_final_video.mp4`

---

## 🎙️ Task 4: Piper TTS Voice Generation

### Purpose
Local neural text-to-speech voiceover generation for narration scripts produced by Qwen.

### Voice Model
- **Model**: `en_US-lessac-medium` (ONNX neural acoustic model)
- **Sample Rate**: 22,050 Hz (16-bit Mono WAV)
- **Model Storage**: `models/piper/en_US-lessac-medium.onnx` & `models/piper/en_US-lessac-medium.onnx.json`
- **Inference**: Local CPU execution via ONNX Runtime

### Commands
```bash
python scripts/download_piper.py
python scripts/test_piper.py
```

---

## 🎬 Task 3: CogVideoX-2B Video Generation

### Purpose
Local text-to-video generation from structured scene prompts.

### Inference Engine
- **Framework**: Hugging Face `diffusers` (`CogVideoXPipeline`)
- **Model**: `THUDM/CogVideoX-2b`
- **Resolution**: 720x480, 49 frames @ 8 FPS (~6 seconds)

### Memory Strategy (Low-Resource Hardware)
To run within the 8 GB RAM / 4 GB VRAM (RTX 2050) budget:
1. **Sequential CPU Offload** (`pipe.enable_sequential_cpu_offload()`): Streams transformer layers between CPU RAM and GPU VRAM one layer at a time.
2. **VAE Slicing & Tiling** (`pipe.vae.enable_slicing()`, `pipe.vae.enable_tiling()`): Decodes high-resolution video latents in small spatial slices to avoid VRAM spikes.
3. **Strict Sequential Execution**: Qwen LLM is unloaded before CogVideoX loads; CogVideoX is unloaded immediately after generation. Models never co-exist in memory.
4. **Generation Mutex**: Concurrent generation requests are rejected with a busy error.

---

## 📡 API Endpoints

### 1. Health & Hardware Status
- **Route**: `GET /api/health`
- **Response**:
```json
{
  "status": "ok",
  "service": "AI Video Generator Backend",
  "device_info": {
    "device": "cpu",
    "cuda_available": false,
    "model_loaded": false,
    "cogvideo": { "available": true, "model_id": "THUDM/CogVideoX-2b", "loaded": false },
    "piper": { "available": true, "loaded": false, "sample_rate": 22050 },
    "ffmpeg": { "available": true, "version": "ffmpeg version N-126889..." }
  }
}
```

### 2. Generate Video Plan (Qwen LLM)
- **Route**: `POST /api/generate`
- **Request**: `{ "prompt": "...", "duration": 10, "aspect_ratio": "16:9", "language": "English" }`

### 3. Generate Single Video Clip (CogVideoX-2B)
- **Route**: `POST /api/generate-video`
- **Request**: `{ "prompt": "...", "duration": 6, "aspect_ratio": "16:9" }`

### 4. Generate Voice Narration (Piper TTS)
- **Route**: `POST /api/generate-audio`
- **Request**: `{ "text": "...", "language": "en" }`

### 5. Assemble Video (FFmpeg)
- **Route**: `POST /api/assemble-video`
- **Request**: `{ "video_files": ["scene_001.mp4"], "audio_file": "voice.wav", "voiceover_text": "...", "burn_subtitles": false }`
- **Response**: `{ "success": true, "video_url": "/api/final-video/output.mp4", "duration": 6.0, "video_codec": "h264", "audio_codec": "aac" }`

### 6. Full End-to-End Generation
- **Route**: `POST /api/generate-full-video`
- **Request**: `{ "prompt": "...", "duration": 10, "aspect_ratio": "16:9", "language": "English", "burn_subtitles": false }`

### 7. Media Serving
- **Final Video**: `GET /api/final-video/{filename}`
- **Scene Clips**: `GET /api/video/{filename}`
- **Audio WAV**: `GET /api/audio/{filename}`



