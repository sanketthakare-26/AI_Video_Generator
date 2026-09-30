"""
Diagnostic script for testing Qwen2.5-1.5B-Instruct generation speed and parameters.
Measures model load time, tokenization time, generation speed, memory, and tokens/second.
"""
import gc
import os
import sys
import time
from pathlib import Path

# Add backend to sys.path
backend_path = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_path))

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from app.config.settings import settings

MODEL_DIR = settings.models_dir / "qwen"
TEST_PROMPT = "Write a short 2 sentence description of an electric car."

print("=" * 60)
print("QWEN2.5-1.5B INFERENCE & SPEED DIAGNOSTIC")
print("=" * 60)

# 1. Device and Environment Info
device = "cuda" if torch.cuda.is_available() else "cpu"
dtype = torch.float16 if device == "cuda" else torch.bfloat16
print(f"PyTorch Version : {torch.__version__}")
print(f"Target Device   : {device}")
print(f"Target Dtype    : {dtype}")
print(f"Local Model Path: {MODEL_DIR}")

# 2. Model Loading
print("\n[1/4] Loading Tokenizer and Model...")
t_load_start = time.time()
tokenizer = AutoTokenizer.from_pretrained(str(MODEL_DIR), trust_remote_code=True)
model = AutoModelForCausalLM.from_pretrained(
    str(MODEL_DIR),
    dtype=dtype,
    device_map="auto" if device == "cuda" else None,
    low_cpu_mem_usage=True,
    trust_remote_code=True,
)
if device == "cpu":
    model.to("cpu")
model.eval()
t_load = time.time() - t_load_start
print(f"  [OK] Model loaded in {t_load:.2f} seconds.")

# 3. Tokenization
print("\n[2/4] Tokenizing test prompt...")
messages = [
    {"role": "system", "content": "You are a helpful assistant. Give concise responses."},
    {"role": "user", "content": TEST_PROMPT}
]
text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
t_tok_start = time.time()
inputs = tokenizer([text], return_tensors="pt").to(model.device)
t_tok = time.time() - t_tok_start
input_tokens = inputs.input_ids.shape[1]
print(f"  [OK] Tokenized {input_tokens} input tokens in {t_tok*1000:.1f} ms.")

# 4. Generation with bounded tokens (e.g. max_new_tokens=64)
print("\n[3/4] Running generation test (max_new_tokens=64)...")
t_gen_start = time.time()
with torch.no_grad():
    output_ids = model.generate(
        **inputs,
        max_new_tokens=64,
        temperature=0.3,
        do_sample=False,
        pad_token_id=tokenizer.eos_token_id,
    )
t_gen = time.time() - t_gen_start

generated_ids = output_ids[0][input_tokens:]
generated_tokens = len(generated_ids)
output_text = tokenizer.decode(generated_ids, skip_special_tokens=True)
speed = generated_tokens / t_gen if t_gen > 0 else 0

print(f"  [OK] Generated {generated_tokens} tokens in {t_gen:.2f} seconds ({speed:.2f} tokens/sec).")
print(f"  Output:\n  \"{output_text.strip()}\"")

# 5. Cleanup
print("\n[4/4] Unloading model...")
del model
del tokenizer
gc.collect()
if torch.cuda.is_available():
    torch.cuda.empty_cache()
print("  [OK] Model unloaded and memory cleaned.")

print("\n" + "=" * 60)
print("QWEN DIAGNOSTIC SUMMARY")
print("=" * 60)
print(f"Device        : {device.upper()}")
print(f"Dtype         : {dtype}")
print(f"Model Load    : {t_load:.2f} s")
print(f"Tokenization  : {t_tok*1000:.1f} ms")
print(f"Generation    : {t_gen:.2f} s ({generated_tokens} tokens @ {speed:.2f} tok/s)")
print(f"Total Time    : {t_load + t_gen:.2f} s")
print("=" * 60)
