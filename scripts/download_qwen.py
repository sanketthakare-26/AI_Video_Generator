from huggingface_hub import snapshot_download
from pathlib import Path

models_dir = Path(__file__).resolve().parent.parent / "models" / "qwen"
models_dir.mkdir(parents=True, exist_ok=True)

print(f"Downloading Qwen2.5-1.5B-Instruct to {models_dir}...")
snapshot_download(
    repo_id="Qwen/Qwen2.5-1.5B-Instruct",
    local_dir=str(models_dir),
    local_dir_use_symlinks=False,
    resume_download=True
)
print("Download complete!")
