# Tools Directory

This directory holds external binary dependencies such as FFmpeg and FFprobe.

Binary executables (`ffmpeg.exe`, `ffprobe.exe`) are excluded from version control due to GitHub's file size limits (>100MB).

## Automated Setup

To download and configure FFmpeg and FFprobe automatically:

```bash
python scripts/setup_ffmpeg.py
```

This will download the official static Windows binaries to `tools/ffmpeg/bin/`.
