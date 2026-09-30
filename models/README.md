# AI Models Directory

This directory will store the local AI model weights for the low-resource execution pipeline.

> **Note**: For Task 1 (Foundation), no model weights are downloaded or loaded.

## Planned Local Models

1. **LLM (Script & Scene Planning)**: `Qwen2.5-1.5B-Instruct`
   - Memory footprint: ~1.5B parameters (~3GB in int4/fp16 quantization)
   - Role: Parses the user prompt, breaks down scenes, and generates the narration script.
   
2. **Video Generation**: `CogVideoX-2B` (or quantized variant)
   - Role: Generates short 2-4 second video clips per scene.
   
3. **Voice Narration (TTS)**: `Piper TTS`
   - Role: Fast, lightweight on-device speech synthesis for English and Hindi.

## Sequential Memory Architecture (4GB VRAM Target)
To operate reliably within 4GB VRAM on an RTX 2050 laptop GPU:
- Models are loaded into memory one by one on-demand.
- Each model is immediately unloaded after finishing its stage before the next model is loaded.
