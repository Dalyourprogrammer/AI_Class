# Plan: Churn Prediction (R)

## Overview
Load the Telco Customer Churn dataset in R, perform exploratory analysis focused on MultipleLines
and Contract features, build a Gaussian Mixture Model (GMM) to predict churn, evaluate on a 20%
holdout test set, and write a short summary with business recommendations.

## Dataset
- `WA_Fn-UseC_-Telco-Customer-Churn.csv`
- 21 columns — demographics, services, contract info, billing; target: `Churn` (Yes/No)
- Known issue: `TotalCharges` has blank strings for new customers → coerce to numeric, replace NAs with 0

## Output Files
```
Sprint5/Churn/
  churn_analysis.R              ← single R script
  churn_multilines_plot.png     ← Plot 1: churn fraction by MultipleLines category
  churn_contract_plot.png       ← Plot 2: churn fraction by Contract type
  churn_confusion_matrix.png    ← Plot 3: confusion matrix heatmap
  churn_writeup.md              ← writeup: EDA findings, model results, recommendations
```

## Steps

### 1 — Load & Preprocess
- `read.csv(...)`, inspect with `str()` and `summary()`
- Convert `TotalCharges` to numeric: `as.numeric(as.character(df$TotalCharges))`; replace NAs with 0
- Keep `Churn` as a factor (Yes/No)

### 2 — EDA: Churn Fraction Plots
Focus only on MultipleLines and Contract.
- Group by feature, compute `churn_rate = sum(Churn=="Yes") / n()`
- **Plot 1** (`churn_multilines_plot.png`): stacked bar chart — MultipleLines categories on x-axis (No, Yes, No phone service), stacked fill = Churn Yes/No, y-axis as fraction/percent
- **Plot 2** (`churn_contract_plot.png`): same style for Contract (Month-to-month, One year, Two year)
- Use `ggplot2`: `geom_bar(position="fill")` + `scale_y_continuous(labels=scales::percent)`

### 3 — Preprocessing for GMM
- Drop `customerID`
- Binary encode all Yes/No columns → 0/1
- One-hot encode multi-class categoricals: `InternetService`, `Contract`, `PaymentMethod`, `MultipleLines`
- `set.seed(42)` then 80/20 split with `sample()` or `caret::createDataPartition`
- Scale numeric features with `scale()`

### 4 — GMM Model
- Package: `mclust`
- Fit: `Mclust(X_train, G=2)` — 2 components for binary churn target
- Map GMM components to churn classes (Yes/No) by majority vote on training labels
- Predict on test set: `predict(gmm_model, X_test)$classification`, then remap to Yes/No

### 5 — Evaluation
- Confusion matrix, precision, recall via `caret::confusionMatrix(predicted, actual)`
- Save confusion matrix as a PNG heatmap using `ggplot2`
- **Do we need a validation set?** No separate validation set is required here. GMM has no hyperparameters being tuned on data — `G=2` is fixed by domain knowledge (binary target). If G were selected by BIC score on training data, a validation set would be warranted to avoid overfitting that selection. With a fixed G, the 80/20 train/test split is sufficient.

### 6 — Writeup (`churn_writeup.md`)
1. **EDA Summary** — churn rates per MultipleLines and Contract category; key patterns
2. **Model** — GMM approach, preprocessing, component-to-class mapping
3. **Results** — confusion matrix values, precision, recall; interpretation
4. **Recommendations** — which customer segments to target for retention or sales focus

## Verification
```bash
cd /workspaces/AI_Class/Sprint5/Churn
Rscript churn_analysis.R
ls *.png *.md
```
