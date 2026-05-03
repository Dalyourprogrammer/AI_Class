import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

BASE = Path(__file__).parent

def load_names(path):
    return [n.strip().lower() for n in Path(path).read_text().splitlines() if n.strip()]

def build_prob_matrix(names):
    chars = ['.'] + sorted(set(''.join(names)))
    stoi  = {c: i for i, c in enumerate(chars)}
    V     = len(chars)
    N = np.zeros((V, V), dtype=np.int32)
    for name in names:
        tokens = ['.'] + list(name) + ['.']
        for c1, c2 in zip(tokens, tokens[1:]):
            if c1 in stoi and c2 in stoi:
                N[stoi[c1], stoi[c2]] += 1
    row_sums = N.sum(axis=1, keepdims=True)
    row_sums[row_sums == 0] = 1   # avoid divide-by-zero for unseen chars
    P = N.astype(float) / row_sums
    return P, chars, stoi

# ── Load both datasets ────────────────────────────────────────────────────────
real_names      = load_names(BASE / "makemore" / "names.txt")
generated_names = load_names(BASE / "novel_names.txt")

P_real, chars_real, _ = build_prob_matrix(real_names)
P_gen,  chars_gen,  _ = build_prob_matrix(generated_names)

# Shared alphabet so both matrices are 27×27 with the same axis order
ALL_CHARS = ['.'] + list('abcdefghijklmnopqrstuvwxyz')

def reindex(P, src_chars):
    """Expand/reorder P to match ALL_CHARS ordering."""
    V = len(ALL_CHARS)
    stoi_src = {c: i for i, c in enumerate(src_chars)}
    M = np.zeros((V, V))
    for i, ci in enumerate(ALL_CHARS):
        for j, cj in enumerate(ALL_CHARS):
            if ci in stoi_src and cj in stoi_src:
                M[i, j] = P[stoi_src[ci], stoi_src[cj]]
    return M

M_real = reindex(P_real, chars_real)
M_gen  = reindex(P_gen,  chars_gen)

# Shared colour scale so brightness is directly comparable
vmax = max(M_real.max(), M_gen.max())

# ── Side-by-side heat maps ────────────────────────────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(32, 13))

for ax, M, title in [
    (axes[0], M_real, f"Real names  ({len(real_names):,})"),
    (axes[1], M_gen,  f"Makemore-generated  ({len(generated_names)})"),
]:
    im = ax.imshow(M, cmap='Blues', vmin=0, vmax=vmax)
    ax.set_xticks(range(27)); ax.set_xticklabels(ALL_CHARS, fontsize=8)
    ax.set_yticks(range(27)); ax.set_yticklabels(ALL_CHARS, fontsize=8)
    ax.set_xlabel("Second letter", fontsize=11)
    ax.set_ylabel("First letter",  fontsize=11)
    ax.set_title(title, fontsize=13)
    for i in range(27):
        for j in range(27):
            v = M[i, j]
            if v > 0.01:
                ax.text(j, i, f"{v:.2f}", ha='center', va='center',
                        fontsize=4.5, color='black' if v < vmax * 0.6 else 'white')

fig.colorbar(im, ax=axes, fraction=0.015, label="Transition probability")
fig.suptitle("Bigram transition probabilities: real vs. generated names", fontsize=15, y=1.01)
plt.tight_layout()

out = BASE / "bigram_comparison.png"
plt.savefig(out, dpi=150, bbox_inches='tight')
print(f"Saved → {out}")
plt.show()

# ── Numerical comparison ──────────────────────────────────────────────────────
print("\n" + "="*65)
print("COMPARISON ANALYSIS")
print("="*65)

dot = ALL_CHARS.index('.')

# Starting letter distributions
print("\nStarting letter probabilities  (row '.'):")
print(f"{'Letter':>8}  {'Real':>8}  {'Generated':>10}  {'Diff':>8}")
for j, c in enumerate(ALL_CHARS[1:], 1):
    r, g = M_real[dot, j], M_gen[dot, j]
    if r > 0.001 or g > 0.001:
        print(f"  '{c}'    {r:8.4f}  {g:10.4f}  {g-r:+8.4f}")

# Ending letter distributions
print("\nEnding letter probabilities  (column '.'):")
print(f"{'Letter':>8}  {'Real':>8}  {'Generated':>10}  {'Diff':>8}")
for i, c in enumerate(ALL_CHARS[1:], 1):
    r, g = M_real[i, dot], M_gen[i, dot]
    if r > 0.005 or g > 0.005:
        print(f"  '{c}'    {r:8.4f}  {g:10.4f}  {g-r:+8.4f}")

# Most different cells overall
diffs = np.abs(M_gen - M_real)
flat  = np.argsort(diffs.ravel())[::-1][:15]
print("\nTop 15 largest differences between matrices:")
print(f"  {'Bigram':>8}  {'Real':>8}  {'Generated':>10}  {'|Diff|':>8}")
for idx in flat:
    i, j = divmod(idx, 27)
    r, g = M_real[i, j], M_gen[i, j]
    print(f"  '{ALL_CHARS[i]}{ALL_CHARS[j]}'    {r:8.4f}  {g:10.4f}  {diffs[i,j]:8.4f}")
