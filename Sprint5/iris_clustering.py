import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from sklearn.datasets import load_iris
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from scipy.cluster.hierarchy import linkage, dendrogram

# ── Load data ──────────────────────────────────────────────────────────────────
iris = load_iris()
X = iris.data          # shape (150, 4)
y = iris.target        # 0=Setosa, 1=Versicolor, 2=Virginica
names = iris.target_names

COLORS = ["#e41a1c", "#377eb8", "#4daf4a"]   # red, blue, green
MARKERS = ["o", "s", "^"]                     # circle, square, triangle

# ── PCA projection ─────────────────────────────────────────────────────────────
pca = PCA(n_components=2, random_state=42)
X_pca = pca.fit_transform(X)
var = pca.explained_variance_ratio_

# ── K-Means (k=3) on original 4-feature space ─────────────────────────────────
km3 = KMeans(n_clusters=3, random_state=42, n_init=10)
km3.fit(X)
labels3 = km3.labels_

# ══════════════════════════════════════════════════════════════════════════════
# Plot 1 — PCA scatter, true labels
# ══════════════════════════════════════════════════════════════════════════════
fig, ax = plt.subplots(figsize=(7, 5))
for i, name in enumerate(names):
    mask = y == i
    ax.scatter(X_pca[mask, 0], X_pca[mask, 1],
               c=COLORS[i], marker=MARKERS[i], label=name,
               edgecolors="k", linewidths=0.4, s=60, alpha=0.85)
ax.set_xlabel(f"PC 1 ({var[0]*100:.1f}% variance)")
ax.set_ylabel(f"PC 2 ({var[1]*100:.1f}% variance)")
ax.set_title("Iris — PCA Projection (True Labels)")
ax.legend(title="Species")
plt.tight_layout()
plt.savefig("iris_pca_scatter.png", dpi=150)
plt.close()
print("Saved iris_pca_scatter.png")

# ══════════════════════════════════════════════════════════════════════════════
# Plot 2 — PCA scatter, k-means clusters (k=3) with true-label markers
# ══════════════════════════════════════════════════════════════════════════════
# Map cluster ids to a consistent color order (match visually to species where possible)
CLUSTER_COLORS = ["#ff7f00", "#984ea3", "#a65628"]  # orange, purple, brown

fig, ax = plt.subplots(figsize=(7, 5))
for ci in range(3):
    for si, name in enumerate(names):
        mask = (labels3 == ci) & (y == si)
        if mask.sum() == 0:
            continue
        ax.scatter(X_pca[mask, 0], X_pca[mask, 1],
                   c=CLUSTER_COLORS[ci], marker=MARKERS[si],
                   edgecolors="k", linewidths=0.4, s=60, alpha=0.85)

# Legend: cluster colors + species markers
from matplotlib.lines import Line2D
cluster_handles = [Line2D([0], [0], marker="o", color="w",
                          markerfacecolor=CLUSTER_COLORS[i], markeredgecolor="k",
                          markersize=9, label=f"Cluster {i+1}")
                   for i in range(3)]
species_handles = [Line2D([0], [0], marker=MARKERS[i], color="w",
                          markerfacecolor="grey", markeredgecolor="k",
                          markersize=9, label=names[i])
                   for i in range(3)]
ax.legend(handles=cluster_handles + species_handles,
          title="Color=Cluster  Shape=Species", fontsize=8, title_fontsize=8)
ax.set_xlabel(f"PC 1 ({var[0]*100:.1f}% variance)")
ax.set_ylabel(f"PC 2 ({var[1]*100:.1f}% variance)")
ax.set_title("Iris — PCA Projection with K-Means Clusters (k=3)")
plt.tight_layout()
plt.savefig("iris_pca_kmeans.png", dpi=150)
plt.close()
print("Saved iris_pca_kmeans.png")

# ══════════════════════════════════════════════════════════════════════════════
# Plot 3 — Petal length vs petal width, colored by k-means clusters
# ══════════════════════════════════════════════════════════════════════════════
fig, ax = plt.subplots(figsize=(7, 5))
for ci in range(3):
    mask = labels3 == ci
    ax.scatter(X[mask, 2], X[mask, 3],
               c=CLUSTER_COLORS[ci], marker="o", label=f"Cluster {ci+1}",
               edgecolors="k", linewidths=0.4, s=60, alpha=0.85)
ax.set_xlabel("Petal Length (cm)")
ax.set_ylabel("Petal Width (cm)")
ax.set_title("Iris — Petal Length vs Petal Width (K-Means k=3)")
ax.legend(title="Cluster")
plt.tight_layout()
plt.savefig("iris_petal_scatter.png", dpi=150)
plt.close()
print("Saved iris_petal_scatter.png")

# ══════════════════════════════════════════════════════════════════════════════
# Plot 4 — Silhouette scores for k=2..10
# ══════════════════════════════════════════════════════════════════════════════
ks = range(2, 11)
scores = []
for k in ks:
    km = KMeans(n_clusters=k, random_state=42, n_init=10)
    lbls = km.fit_predict(X)
    scores.append(silhouette_score(X, lbls))

best_k = list(ks)[int(np.argmax(scores))]
best_score = max(scores)

fig, ax = plt.subplots(figsize=(8, 5))
bar_colors = ["#e41a1c" if k == best_k else "#aec7e8" for k in ks]
bars = ax.bar(list(ks), scores, color=bar_colors, edgecolor="k", linewidth=0.6)
ax.set_xlabel("Number of Clusters (k)")
ax.set_ylabel("Silhouette Score")
ax.set_title("Silhouette Score vs k for Iris Data (k=2 to 10)")
ax.set_xticks(list(ks))

# Annotate best bar
ax.annotate(f"Best k={best_k}\n({best_score:.3f})",
            xy=(best_k, best_score),
            xytext=(best_k + 0.6, best_score - 0.03),
            fontsize=9, color="#e41a1c", fontweight="bold",
            arrowprops=dict(arrowstyle="->", color="#e41a1c"))

# Highlighted answer box
answer_text = (
    "Best k = 2  (highest silhouette score)\n\n"
    "Challenge insight: k=2 beats k=3 even though there\n"
    "are 3 true species. Setosa is so well-separated that\n"
    "it dominates the score, while Versicolor & Virginica\n"
    "overlap and merge into one cluster. This shows that\n"
    "silhouette optimizes geometric separation, not domain\n"
    "labels — the 'best' k is metric-dependent and may not\n"
    "recover overlapping true classes."
)
ax.text(0.98, 0.97, answer_text,
        transform=ax.transAxes, fontsize=7.5,
        verticalalignment="top", horizontalalignment="right",
        bbox=dict(boxstyle="round,pad=0.5", facecolor="#fffde7",
                  edgecolor="#e41a1c", linewidth=1.2))

plt.tight_layout()
plt.savefig("iris_silhouette.png", dpi=150)
plt.close()
print("Saved iris_silhouette.png")

# ══════════════════════════════════════════════════════════════════════════════
# Plot 5 — Dendrogram with Ward's linkage
# ══════════════════════════════════════════════════════════════════════════════
Z = linkage(X, method="ward")

# Color threshold: cut at 70% of the max merge distance to highlight 3 clusters
color_threshold = 0.7 * max(Z[:, 2])

fig, ax = plt.subplots(figsize=(12, 5))
dendrogram(Z, ax=ax,
           color_threshold=color_threshold,
           above_threshold_color="lightgrey",
           leaf_rotation=90, leaf_font_size=5)
ax.axhline(color_threshold, color="red", linestyle="--", linewidth=1.2,
           label=f"Cut threshold ({color_threshold:.1f})")
ax.set_xlabel("Sample Index")
ax.set_ylabel("Ward Linkage Distance")
ax.set_title("Iris — Hierarchical Clustering Dendrogram (Ward's Linkage)")
ax.legend(fontsize=8)
plt.tight_layout()
plt.savefig("iris_dendrogram.png", dpi=150)
plt.close()
print("Saved iris_dendrogram.png")

# ══════════════════════════════════════════════════════════════════════════════
# Highlighted answers to stdout
# ══════════════════════════════════════════════════════════════════════════════
print()
print("=" * 65)
print("  ANSWERS")
print("=" * 65)
print(f"  Best k according to silhouette plot: k = {best_k}  "
      f"(score = {best_score:.4f})")
print()
print("  What this suggests about clustering challenges:")
print("  ─" * 32)
print("  Even though Iris has 3 known species, the silhouette score")
print("  peaks at k=2. Setosa is so geometrically distinct that it")
print("  dominates the between-cluster distance calculation, making")
print("  a 2-cluster split look optimal. Versicolor and Virginica")
print("  overlap in feature space, so k-means merges them.")
print()
print("  Core challenge: unsupervised clustering metrics optimize for")
print("  statistical cohesion in feature space, not for recovering")
print("  true class labels. The 'right' k depends on the metric, the")
print("  data geometry, and domain knowledge — there is no single")
print("  correct answer, and a low-k optimum can mask real structure.")
print("=" * 65)
