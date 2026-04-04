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
  churn_dependents_plot.png     ← Plot 2: churn fraction by Dependents (Yes/No)
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
- **Plot 2** (`churn_dependents_plot.png`): same style for Dependents (Yes / No)
- Use `ggplot2`: `geom_bar(position="fill")` + `scale_y_continuous(labels=scales::percent)`

### 3 — Preprocessing for GMM
- Drop `customerID`
- Binary encode all Yes/No columns → 0/1
- One-hot encode multi-class categoricals: `InternetService`, `Contract`, `PaymentMethod`, `MultipleLines`
- Scale numeric features with `scale()`
- No train/test split — full dataset used in cross-validation

### 4 — GMM Model with 5-Fold Cross-Validation
- Package: `mclust`
- `set.seed(42)`, create 5 stratified folds with `caret::createFolds(y, k=5)`
- For each fold: fit `Mclust(X_train_fold, G=2)`, map components to Yes/No by majority vote, predict on held-out fold
- Collect out-of-fold (OOF) predictions across all 5 folds

### 5 — Evaluation
- Aggregate OOF predictions across all folds → single confusion matrix over full dataset
- `caret::confusionMatrix(all_preds, all_actual, positive="Yes")`
- Print accuracy, recall, precision, F1
- Save confusion matrix as PNG heatmap using `ggplot2`

### 6 — Update Writeup (`churn_writeup.md`)
- Update model section to describe 5-fold CV instead of 80/20 split
- Update results with CV metrics

### 7 — Writeup (`churn_writeup.md`)
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
