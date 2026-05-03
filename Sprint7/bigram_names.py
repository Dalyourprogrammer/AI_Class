import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

# ── Load names ────────────────────────────────────────────────────────────────
names_path = Path(__file__).parent / "makemore" / "names.txt"
names = names_path.read_text().strip().splitlines()
names = [n.strip().lower() for n in names if n.strip()]

# ── Build character vocabulary ────────────────────────────────────────────────
chars = ['.'] + sorted(set(''.join(names)))   # '.' = start/end token
stoi  = {c: i for i, c in enumerate(chars)}
itos  = {i: c for c, i in stoi.items()}
V     = len(chars)  # 27

# ── Build bigram count matrix ─────────────────────────────────────────────────
N = np.zeros((V, V), dtype=np.int32)

for name in names:
    tokens = ['.'] + list(name) + ['.']
    for ch1, ch2 in zip(tokens, tokens[1:]):
        N[stoi[ch1], stoi[ch2]] += 1

# ── Probability matrix (row-normalised) ───────────────────────────────────────
P = N.astype(float)
P /= P.sum(axis=1, keepdims=True)   # each row sums to 1

# ── Heat-map visualisation ────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(16, 14))
im = ax.imshow(P, cmap='Blues')

ax.set_xticks(range(V)); ax.set_xticklabels(chars, fontsize=9)
ax.set_yticks(range(V)); ax.set_yticklabels(chars, fontsize=9)
ax.set_xlabel("Second letter", fontsize=12)
ax.set_ylabel("First letter",  fontsize=12)
ax.set_title("Bigram probability heat-map (names)", fontsize=14)

# Annotate each cell with the probability
for i in range(V):
    for j in range(V):
        v = P[i, j]
        if v > 0:
            ax.text(j, i, f"{v:.2f}", ha='center', va='center',
                    fontsize=5, color='black' if v < 0.5 else 'white')

plt.colorbar(im, ax=ax, fraction=0.03)
plt.tight_layout()
out_path = Path(__file__).parent / "bigram_heatmap.png"
plt.savefig(out_path, dpi=150)
print(f"Heatmap saved → {out_path}")
plt.show()

# ── Analysis ──────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("ANALYSIS")
print("="*60)

dot_idx = stoi['.']

# 1. Starting letters: row for '.' (but skip '.' → '.' column)
start_probs = P[dot_idx].copy()
start_probs[dot_idx] = 0   # '.' never starts with '.'
top3_start    = np.argsort(start_probs)[::-1][:3]
bottom3_start = [i for i in np.argsort(start_probs) if start_probs[i] > 0][:3]

print("\n1. Most likely starting letters:")
for i in top3_start:
    print(f"   '{itos[i]}' : {start_probs[i]:.4f}")

print("\n   Least likely starting letters (non-zero):")
for i in bottom3_start:
    print(f"   '{itos[i]}' : {start_probs[i]:.4f}")

# 2. Ending letters: column for '.'
end_probs = P[:, dot_idx].copy()
end_probs[dot_idx] = 0   # skip '.' → '.'
top3_end    = np.argsort(end_probs)[::-1][:3]
bottom3_end = [i for i in np.argsort(end_probs) if end_probs[i] > 0][:3]

print("\n2. Most likely ending letters:")
for i in top3_end:
    print(f"   '{itos[i]}' : {end_probs[i]:.4f}")

print("\n   Least likely ending letters (non-zero):")
for i in bottom3_end:
    print(f"   '{itos[i]}' : {end_probs[i]:.4f}")

# 3. Letters that follow 'q'
q_idx = stoi['q']
q_row = P[q_idx]
print("\n3. Letters following 'q':")
for i, p in enumerate(q_row):
    if p > 0:
        print(f"   'q' → '{itos[i]}' : {p:.4f}")

# 4. Most likely second letter for names starting with 'x'
x_idx = stoi['x']
x_row = P[x_idx].copy()
x_row[dot_idx] = 0   # exclude '.' (end token)
best_x = np.argmax(x_row)
print(f"\n4. Most likely second letter after 'x': '{itos[best_x]}' ({x_row[best_x]:.4f})")
print("\n   Full distribution after 'x' (non-zero):")
for i in np.argsort(x_row)[::-1]:
    if x_row[i] > 0:
        print(f"   'x' → '{itos[i]}' : {x_row[i]:.4f}")

# ── Name generation ───────────────────────────────────────────────────────────
print("\n" + "="*60)
print("GENERATED NAMES")
print("="*60)

rng = np.random.default_rng(seed=42)

def random_choice(probs):
    """Sample one index from a probability distribution."""
    return rng.choice(len(probs), p=probs)

def generate_name():
    letter = '.'
    name = ''
    while True:
        letter = itos[random_choice(P[stoi[letter]])]
        if letter == '.':
            break
        name += letter
    return name

generated = []
while len(generated) < 25:
    name = generate_name()
    if len(name) >= 3:
        generated.append(name)

print()
for i, name in enumerate(generated, 1):
    print(f"  {i:2}. {name}")
