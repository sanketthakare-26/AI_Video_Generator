from pathlib import Path

hf_cache = Path.home() / '.cache' / 'huggingface' / 'hub' / 'models--THUDM--CogVideoX-2b'
snap = hf_cache / 'snapshots' / '1137dacfc2c9c012bed6a0793f4ecf2ca8e7ba01'

import os
print(f"Snapshot: {snap}")
print()

missing = []
present = []
for item in sorted(snap.rglob('*')):
    if item.is_symlink():
        exists = item.exists()
        sz = item.stat().st_size if exists else 0
        status = "OK" if exists else "BROKEN"
        print(f"  [{status}] {item.relative_to(snap)}  ({sz/1e6:.1f} MB)")
        if not exists:
            missing.append(str(item.relative_to(snap)))
        else:
            present.append(str(item.relative_to(snap)))
    elif item.is_file():
        sz = item.stat().st_size
        print(f"  [FILE] {item.relative_to(snap)}  ({sz/1e6:.1f} MB)")
        present.append(str(item.relative_to(snap)))

print()
print(f"COMPLETE: {len(present)} files")
print(f"MISSING/BROKEN: {len(missing)} files")
if missing:
    print("  Missing files:")
    for m in missing:
        print(f"    - {m}")
