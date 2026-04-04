import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from sklearn.datasets import load_iris
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score, silhouette_samples
from scipy.cluster.hierarchy import linkage, dendrogram
from sklearn.mixture import GaussianMixture
from scipy.stats import multivariate_normal

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
# Plot 4 — Silhouette grid (3×3, k=2..10)
# ══════════════════════════════════════════════════════════════════════════════
import matplotlib.cm as cm

ks = range(2, 11)
avg_scores = {}
for k in ks:
    km = KMeans(n_clusters=k, random_state=42, n_init=10)
    avg_scores[k] = silhouette_score(X, km.fit_predict(X))
best_k = max(avg_scores, key=avg_scores.get)

fig, axes = plt.subplots(3, 3, figsize=(14, 12))
fig.suptitle("Silhouette Plots for k=2 to k=10 (Iris Dataset)", fontsize=13, fontweight="bold")

for idx, k in enumerate(ks):
    ax = axes[idx // 3][idx % 3]
    km = KMeans(n_clusters=k, random_state=42, n_init=10)
    labels = km.fit_predict(X)
    sample_sil = silhouette_samples(X, labels)
    avg = avg_scores[k]
    colors = cm.tab10(np.linspace(0, 1, k))
    y_lower = 10
    for ci in range(k):
        vals = np.sort(sample_sil[labels == ci])
        y_upper = y_lower + len(vals)
        ax.fill_betweenx(np.arange(y_lower, y_upper), 0, vals,
                         facecolor=colors[ci], edgecolor=colors[ci], alpha=0.8)
        y_lower = y_upper + 5
    ax.axvline(avg, color="red", linestyle="--", linewidth=1.2)
    is_best = (k == best_k)
    ax.set_title(f"k={k}  (avg={avg:.3f})", fontsize=9,
                 fontweight="bold" if is_best else "normal",
                 color="red" if is_best else "black")
    ax.set_xlim([-0.2, 1.0])
    ax.set_yticks([])
    ax.set_xlabel("Silhouette coeff.", fontsize=7)

plt.tight_layout()
plt.savefig("iris_silhouette.png", dpi=150)
plt.close()
print("Saved iris_silhouette.png")
avg_score = avg_scores[3]   # k=3 score used in stdout answers

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
# Plot 6 — Gaussian Mixture Model with covariance ellipses
# ══════════════════════════════════════════════════════════════════════════════
gmm = GaussianMixture(n_components=3, covariance_type="full", random_state=42)
gmm.fit(X_pca)                        # fit directly in 2D — exact 2D normal distributions
gmm_labels = gmm.predict(X_pca)

GMM_COLORS = ["#1b9e77", "#d95f02", "#7570b3"]  # teal, orange, purple

def hex_to_rgb01(h):
    h = h.lstrip("#")
    return np.array([int(h[i:i+2], 16) / 255 for i in (0, 2, 4)])

# Soft assignment probabilities — each row sums to 1
proba = gmm.predict_proba(X_pca)                      # (150, 3)
rgb_components = np.array([hex_to_rgb01(c) for c in GMM_COLORS])  # (3, 3)
point_colors = proba @ rgb_components                 # (150, 3) blended RGB
edge_widths   = 0.3 + 1.5 * (1 - proba.max(axis=1)) # thick edge = uncertain

# Build meshgrid over PCA extent
x_min, x_max = X_pca[:, 0].min() - 0.5, X_pca[:, 0].max() + 0.5
y_min, y_max = X_pca[:, 1].min() - 0.5, X_pca[:, 1].max() + 0.5
xx, yy = np.meshgrid(np.linspace(x_min, x_max, 200),
                     np.linspace(y_min, y_max, 200))
grid = np.c_[xx.ravel(), yy.ravel()]

fig, ax = plt.subplots(figsize=(9, 5))

# Density backdrop — exact 2D Gaussian PDFs (no projection needed)
for ci in range(3):
    Z = multivariate_normal(mean=gmm.means_[ci], cov=gmm.covariances_[ci]).pdf(grid).reshape(xx.shape)
    ax.contourf(xx, yy, Z, levels=6, colors=[GMM_COLORS[ci]], alpha=0.20)
    ax.contour(xx, yy, Z, levels=6, colors=[GMM_COLORS[ci]], linewidths=0.8, alpha=0.6)

# Soft-assignment scatter — color blended by probability
ax.scatter(X_pca[:, 0], X_pca[:, 1],
           c=point_colors, edgecolors="k",
           linewidths=edge_widths, s=70, alpha=0.9, zorder=3)

# Component means + legend patches
from matplotlib.patches import Patch
from matplotlib.lines import Line2D
legend_handles = []
for ci in range(3):
    ax.scatter(*gmm.means_[ci], marker="*", s=220, color="white",
               edgecolors=GMM_COLORS[ci], linewidths=1.5, zorder=5)
    legend_handles.append(Patch(facecolor=GMM_COLORS[ci], edgecolor="k",
                                label=f"Component {ci+1}"))
legend_handles.append(Line2D([0], [0], marker="*", color="w",
                             markerfacecolor="white", markeredgecolor="black",
                             markersize=11, label="Component mean"))

ax.set_xlabel(f"PC 1 ({var[0]*100:.1f}% variance)")
ax.set_ylabel(f"PC 2 ({var[1]*100:.1f}% variance)")
ax.set_title("Iris — GMM Soft Assignments (n=3)\nColor blend = membership probability · Edge width = uncertainty")
ax.legend(handles=legend_handles, title="GMM Component", fontsize=8,
          bbox_to_anchor=(1.02, 1), loc="upper left", borderaxespad=0)
plt.tight_layout()
plt.savefig("iris_gmm.png", dpi=150)
plt.close()
print("Saved iris_gmm.png")

gmm_bic = gmm.bic(X_pca)
gmm_ll  = gmm.score(X_pca) * len(X_pca)   # total log-likelihood
print(f"  GMM log-likelihood: {gmm_ll:.2f}  |  BIC: {gmm_bic:.2f}")

# ══════════════════════════════════════════════════════════════════════════════
# Highlighted answers to stdout
# ══════════════════════════════════════════════════════════════════════════════
print()
print("=" * 65)
print("  ANSWERS")
print("=" * 65)
print(f"  Silhouette score for k=3: {avg_score:.4f}")
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
