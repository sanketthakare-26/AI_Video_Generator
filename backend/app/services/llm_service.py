"""Local LLM Service using Qwen2.5-1.5B-Instruct.

Responsibilities:
1. Lazy loading of Qwen tokenizer and model into CPU or GPU memory.
2. Generating structured video plans (title, style, scenes, video prompts, voiceover).
3. Memory cleanup and model unloading (for low VRAM 4GB hardware).
4. Automatic device detection and dtype optimization.

PERFORMANCE NOTE (CPU-only mode):
  Qwen on CPU-only PyTorch runs at ~2-3 tokens/sec.
  We keep max_new_tokens=400 and use greedy decoding (do_sample=False)
  to keep generation time under ~3 minutes on this hardware.
  The system prompt is compact so the model outputs short JSON only.
"""
import gc
import json
import re
import time
from typing import Dict, Any, Optional
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from app.config.settings import settings
from app.schemas.generation import GenerateRequest, VideoPlan, ScenePlan
from app.utils.logger import logger


class LocalLLMService:
    """Manages local inference for Qwen2.5-1.5B-Instruct."""

    MODEL_ID = "Qwen/Qwen2.5-1.5B-Instruct"

    # Maximum new tokens for video plan generation.
    # At ~2.5 tok/s on CPU, 400 tokens ≈ 160 seconds max.
    MAX_NEW_TOKENS = 400

    def __init__(self):
        self.model = None
        self.tokenizer = None
        self.is_loaded = False
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

    def get_device_info(self) -> Dict[str, Any]:
        """Detect and return hardware device and memory status."""
        cuda_avail = torch.cuda.is_available()
        info: Dict[str, Any] = {
            "device": "cuda" if cuda_avail else "cpu",
            "cuda_available": cuda_avail,
            "gpu_name": None,
            "vram_total_gb": None,
            "vram_allocated_gb": None,
            "model_loaded": self.is_loaded,
        }
        if cuda_avail:
            info["gpu_name"] = torch.cuda.get_device_name(0)
            props = torch.cuda.get_device_properties(0)
            info["vram_total_gb"] = round(props.total_memory / (1024 ** 3), 2)
            info["vram_allocated_gb"] = round(torch.cuda.memory_allocated(0) / (1024 ** 3), 2)
        return info

    def load_model(self):
        """Loads Qwen2.5-1.5B-Instruct lazily into memory with optimal dtype."""
        if self.is_loaded and self.model is not None and self.tokenizer is not None:
            return

        logger.info(f"[Qwen] Loading {self.MODEL_ID} on {self.device}...")
        t0 = time.time()
        dtype = torch.float16 if self.device == "cuda" else torch.bfloat16

        # Check if local model directory has downloaded model files
        local_qwen_path = settings.models_dir / "qwen"
        if (local_qwen_path / "config.json").exists() and (local_qwen_path / "model.safetensors").exists():
            model_source = str(local_qwen_path)
            logger.info(f"[Qwen] Loading local weights from {model_source}")
        else:
            model_source = self.MODEL_ID
            logger.info(f"[Qwen] Loading from Hugging Face hub ({self.MODEL_ID})")

        self.tokenizer = AutoTokenizer.from_pretrained(
            model_source,
            trust_remote_code=True,
        )

        self.model = AutoModelForCausalLM.from_pretrained(
            model_source,
            dtype=dtype,
            device_map="auto" if self.device == "cuda" else None,
            low_cpu_mem_usage=True,
            trust_remote_code=True,
        )

        if self.device == "cpu":
            self.model.to("cpu")

        self.model.eval()
        self.is_loaded = True
        elapsed = time.time() - t0
        logger.info(f"[Qwen] Model loaded in {elapsed:.1f}s on {self.device} ({dtype}).")

    def unload_model(self):
        """Unloads model and frees GPU/system memory."""
        if not self.is_loaded:
            return

        logger.info("[Qwen] Unloading model from memory...")
        if self.model is not None:
            del self.model
            self.model = None

        if self.tokenizer is not None:
            del self.tokenizer
            self.tokenizer = None

        self.is_loaded = False
        gc.collect()

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.ipc_collect()

        logger.info("[Qwen] Model unloaded and VRAM cleared.")

    def _build_system_prompt(self) -> str:
        """
        Compact system prompt that produces short, structured JSON.
        Shorter output = fewer tokens = faster generation on CPU.
        """
        return (
            "You are a video planning AI. Output ONLY a valid compact JSON object. "
            "No markdown, no code fences, no extra text.\n"
            "JSON format:\n"
            '{"title":"...", "style":"cinematic", "total_duration":<int>, '
            '"scenes":[{"scene_number":1,"duration":<int>,"description":"<15 words max>","video_prompt":"<20 words max>"},...], '
            '"voiceover":"<2-3 sentences max>"}\n'
            "Rules: scene durations sum to total_duration. Video prompts in English. Be concise."
        )

    def _build_user_prompt(self, request: GenerateRequest) -> str:
        """Build compact user prompt with explicit scene count."""
        scene_count_map = {10: 2, 15: 3, 20: 4, 30: 5}
        num_scenes = scene_count_map.get(request.duration, 3)
        secs_per_scene = request.duration // num_scenes

        return (
            f"Video idea: \"{request.prompt}\"\n"
            f"Duration: {request.duration}s, {num_scenes} scenes of ~{secs_per_scene}s each.\n"
            f"Language: {request.language}. Output JSON only."
        )

    def _extract_json(self, raw_text: str) -> Dict[str, Any]:
        """Extract and parse JSON from LLM output, handling possible markdown fences."""
        cleaned = raw_text.strip()

        # Remove markdown fences if present
        if "```json" in cleaned:
            match = re.search(r"```json\s*(.*?)\s*```", cleaned, re.DOTALL)
            if match:
                cleaned = match.group(1).strip()
        elif "```" in cleaned:
            match = re.search(r"```\s*(.*?)\s*```", cleaned, re.DOTALL)
            if match:
                cleaned = match.group(1).strip()

        # Find first '{' and last '}'
        start_idx = cleaned.find("{")
        end_idx = cleaned.rfind("}")
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            cleaned = cleaned[start_idx: end_idx + 1]

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as err:
            logger.error(f"[Qwen] JSON decode failed.\nRaw output:\n{raw_text}\nCleaned:\n{cleaned}")
            raise ValueError(f"Failed to parse Qwen output as JSON: {str(err)}")

    def generate_plan(self, request: GenerateRequest) -> VideoPlan:
        """
        Generates a validated structured VideoPlan using Qwen2.5-1.5B-Instruct.
        Called ONCE per full pipeline run. Loads once, generates once, returns plan.
        """
        logger.info(f"[Qwen] Stage 1: Loading model...")
        self.load_model()

        messages = [
            {"role": "system", "content": self._build_system_prompt()},
            {"role": "user", "content": self._build_user_prompt(request)},
        ]

        text = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )

        logger.info(f"[Qwen] Stage 2: Tokenizing prompt for: '{request.prompt[:40]}...'")
        t_tok = time.time()
        model_inputs = self.tokenizer([text], return_tensors="pt").to(self.model.device)
        input_token_count = model_inputs.input_ids.shape[1]
        logger.info(f"[Qwen] Input tokens: {input_token_count} (tok in {(time.time()-t_tok)*1000:.0f}ms)")

        logger.info(f"[Qwen] Stage 3: Generating video plan (max_new_tokens={self.MAX_NEW_TOKENS}, greedy)...")
        t_gen = time.time()

        with torch.no_grad():
            generated_ids = self.model.generate(
                **model_inputs,
                max_new_tokens=self.MAX_NEW_TOKENS,
                do_sample=False,                  # Greedy decode — faster and more predictable on CPU
                repetition_penalty=1.15,          # Prevent repetition loops
                pad_token_id=self.tokenizer.eos_token_id,
                eos_token_id=self.tokenizer.eos_token_id,
            )

        new_token_ids = generated_ids[0][input_token_count:]
        new_token_count = len(new_token_ids)
        gen_elapsed = time.time() - t_gen
        tok_per_sec = new_token_count / gen_elapsed if gen_elapsed > 0 else 0

        response_text = self.tokenizer.decode(new_token_ids, skip_special_tokens=True)
        logger.info(
            f"[Qwen] Stage 3 complete: {new_token_count} tokens in {gen_elapsed:.1f}s "
            f"({tok_per_sec:.2f} tok/s)"
        )
        logger.info(f"[Qwen] Raw output:\n{response_text}")

        # Parse and validate JSON
        logger.info("[Qwen] Stage 4: Parsing JSON plan...")
        data = self._extract_json(response_text)

        # Extract fields with safe fallbacks
        title = data.get("title") or request.prompt[:30].strip()
        style = data.get("style") or "cinematic photorealistic"
        total_duration = int(data.get("total_duration") or request.duration)
        voiceover = data.get("voiceover") or data.get("narration") or request.prompt

        raw_scenes = data.get("scenes", [])
        if not raw_scenes:
            logger.warning("[Qwen] No scenes in output. Using single-scene fallback.")
            raw_scenes = [
                {
                    "scene_number": 1,
                    "duration": request.duration,
                    "description": request.prompt,
                    "video_prompt": f"Cinematic, {request.prompt}, high resolution, realistic lighting",
                }
            ]

        parsed_scenes = []
        for idx, s in enumerate(raw_scenes, 1):
            scene_num = int(s.get("scene_number", idx))
            scene_dur = int(s.get("duration", max(2, request.duration // max(1, len(raw_scenes)))))
            desc = str(s.get("description", f"Scene {idx}"))
            v_prompt = str(s.get("video_prompt") or s.get("prompt") or desc)
            parsed_scenes.append(
                ScenePlan(
                    scene_number=scene_num,
                    duration=scene_dur,
                    description=desc,
                    video_prompt=v_prompt,
                )
            )

        video_plan = VideoPlan(
            title=title,
            style=style,
            total_duration=total_duration,
            scenes=parsed_scenes,
            voiceover=voiceover,
        )

        logger.info(
            f"[Qwen] Plan ready: '{title}' | {len(parsed_scenes)} scenes | "
            f"{total_duration}s | voiceover: {len(voiceover)} chars"
        )
        return video_plan


# Singleton instance
llm_service = LocalLLMService()
