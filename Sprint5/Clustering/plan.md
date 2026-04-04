# Plan: Iris Clustering Analysis

## Output Files
```
Sprint5/
  iris_clustering.py       ← single script: python3 iris_clustering.py
  iris_pca_scatter.png     ← Plot 1: PCA projection colored by true label
  iris_pca_kmeans.png      ← Plot 2: PCA projection colored by k-means clusters (k=3)
  iris_petal_scatter.png   ← Plot 3: petal length vs petal width, colored by k-means clusters
  iris_silhouette.png      ← Plot 4: silhouette scores for k=2..10
  iris_dendrogram.png      ← Plot 5: Ward's linkage dendrogram
  iris_gmm.png             ← Plot 6: GMM components with covariance ellipses in PCA space
```

## Plot Details

### Plot 1 — PCA Scatter (true labels)
- `PCA(n_components=2)` on all 4 iris features → project to 2D
- Color by true class (Setosa / Versicolor / Virginica)
- Setosa clearly separates; Versicolor & Virginica overlap in PC space

### Plot 2 — PCA Scatter + K-Means (k=3)
- Same PCA projection as Plot 1
- `KMeans(n_clusters=3, random_state=42)` fit on original 4-feature data
- Color by cluster assignment; use different marker shapes for true labels
  so the viewer can see where clustering agrees/diverges from ground truth

### Plot 3 — Petal-only Scatter
- X: petal length (feature 2), Y: petal width (feature 3)
- Color by k-means cluster labels (same model as Plot 2)

### Plot 5 — Dendrogram (Ward's Linkage)
- Use `scipy.cluster.hierarchy.linkage(X, method='ward')` and `dendrogram()`
- Ward's criterion minimizes total within-cluster variance at each merge step
- Color threshold set at a natural gap in the merge distances to visually highlight 3 clusters
- X-axis: sample index, Y-axis: merge distance (Ward linkage distance)
- Save → `iris_dendrogram.png`
- Note: scipy's `dendrogram` is the standard tool; scikit-learn's `AgglomerativeClustering` provides the same Ward linkage for cluster labels if needed, but scipy produces the actual dendrogram plot

### Plot 4 — Silhouette Grid (3×3, k=2..10)
- 3×3 subplot grid, one silhouette plot per k from 2 to 10
- Each subplot: fit `KMeans(n_clusters=k)`, compute `silhouette_samples` + `silhouette_score`
- One horizontal band per cluster, samples sorted descending within band; colors from `cm.tab10`
- Vertical dashed red line at the mean silhouette score per subplot
- Subplot title: `k={k}  (avg={score:.3f})`; best-k title highlighted in bold red
- X-axis: silhouette coefficient [-0.2, 1.0]; Y-axis ticks hidden
- Overall figure title: "Silhouette Plots for k=2 to k=10 (Iris Dataset)"
- Save → `iris_silhouette.png`

### Plot 6 — GMM Soft-Assignment in 2D PCA Space (n_components=3)
- `GaussianMixture(n_components=3, covariance_type='full', random_state=42)` fit directly on `X_pca` (2D)
  — model lives in the same space as the plot; no projection approximation
- Density backdrop: `contourf` + `contour` per component using `gmm.means_[ci]` and `gmm.covariances_[ci]` directly (exact 2D normals)
- Soft assignments: `proba = gmm.predict_proba(X_pca)` → shape (150, 3)
- Each point's color = probability-weighted blend of the 3 component RGB colors: `point_colors = proba @ rgb_components`
  - Pure-cluster points → solid component color; boundary points → blended/intermediate color
- Edge thickness encodes confidence: `linewidths = 0.3 + 1.5 * (1 - proba.max(axis=1))`
  - Confident points: thin edge; uncertain points: thick black edge
- Component means marked with white stars
- Legend placed beside (outside) the axes to the right; includes colored patches per component + a star entry labeled "Component mean"
- Save → `iris_gmm.png`

---

## Answers (highlighted)

> **Best k according to silhouette = 2**

> **What this suggests about clustering challenges:**
> The silhouette score peaks at k=2 even though there are 3 known species.
> Setosa is so well-separated that it dominates the inter-cluster distance,
> while Versicolor and Virginica overlap enough that the algorithm merges them.
> This reveals the core challenge of cluster analysis: unsupervised metrics
> optimize for geometric separation in feature space, not domain-meaningful
> categories. The "best" k is metric-dependent and may not recover true class
> structure when classes overlap. Analysts must interpret silhouette scores
> alongside domain knowledge rather than treating them as ground truth.

---

## Verification
```bash
cd /workspaces/AI_Class/Sprint5
python3 iris_clustering.py
ls *.png   # should see 6 PNG files
```
