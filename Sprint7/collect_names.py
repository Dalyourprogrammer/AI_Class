"""
Run makemore in sample-only mode across many seeds, collect names
that are novel (not in the training set), stop at 200+.
"""
import subprocess
import sys
from pathlib import Path

MAKEMORE_DIR = Path(__file__).parent / "makemore"
TRAINING_SET = {
    n.strip().lower()
    for n in (MAKEMORE_DIR / "names.txt").read_text().splitlines()
    if n.strip()
}

novel = []
seen  = set()

seed = 1
while len(novel) < 200:
    result = subprocess.run(
        [sys.executable, "makemore.py",
         "-i", "names.txt", "-o", "names",
         "--sample-only", f"--seed={seed}"],
        capture_output=True, text=True, cwd=MAKEMORE_DIR
    )

    in_new_block = False
    for line in result.stdout.splitlines():
        line = line.strip()
        if line.endswith("that are new:"):
            in_new_block = True
            continue
        if in_new_block:
            if line.endswith("that are in train:") or line.endswith("that are in test:") or line.startswith("---"):
                in_new_block = False
                continue
            name = line.lower()
            if name and name.isalpha() and name not in TRAINING_SET and name not in seen:
                seen.add(name)
                novel.append(name)

    print(f"seed {seed:3d} → {len(novel):3d} novel names so far")
    seed += 1
    if seed > 500:   # safety valve
        break

print(f"\nCollected {len(novel)} novel names.")
print("-" * 40)
for i, name in enumerate(novel[:200], 1):
    print(f"{i:3}. {name}")

out_path = Path(__file__).parent / "novel_names.txt"
out_path.write_text("\n".join(novel[:200]) + "\n")
print(f"\nSaved to {out_path}")
