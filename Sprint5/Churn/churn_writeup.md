# Churn Prediction — GMM Analysis Writeup

## 1. EDA Summary

### MultipleLines
| Category | Churn Rate | N |
|---|---|---|
| Yes (has multiple lines) | 28.6% | 2,971 |
| No (single line) | 25.0% | 3,390 |
| No phone service | 24.9% | 682 |

Customers with multiple lines churn at a slightly higher rate (~3.6 pp above single-line customers), but the difference is modest. Multiple Lines is a weak predictor on its own.

### Dependents
| Category | Churn Rate | N |
|---|---|---|
| No dependents | 31.3% | 4,933 |
| Has dependents | 15.5% | 2,110 |

Customers without dependents churn at **twice the rate** of customers with dependents (31.3% vs 15.5%). Customers with dependents appear more stable, likely due to greater household stability and higher switching costs.

---

## 2. Model

**Method:** Gaussian Mixture Model (GMM) via the `mclust` package, fit with `G=2` components on the preprocessed training set.

**Preprocessing:**
- Dropped `customerID`
- Binary-encoded all Yes/No columns → 0/1
- One-hot encoded `MultipleLines`, `InternetService`, `Contract`, `PaymentMethod` (dropping first level)
- All features scaled with `scale()`
- 80/20 stratified train/test split (`set.seed(42)`) → 5,636 train / 1,407 test

**Model selection:** `G=2` was fixed by domain knowledge (binary churn target), not tuned. `mclust` selected the **VII** covariance structure (spherical, varying volume) as the best-fitting geometry for 2 components.

**Component-to-class mapping:** After fitting, each component's training samples were majority-voted to assign a class label (Yes/No).

---

## 3. Results

**Component mapping:** Both components mapped to **"No"** (non-churn). This is the core finding: with only 26.5% of customers churning, GMM found two geometric clusters in the feature space that are both dominated by non-churners. The model predicts "No" for every test sample.

| Metric | Value |
|---|---|
| Accuracy | 73.5% |
| Recall (Churn=Yes) | 0.0 |
| Precision (Churn=Yes) | N/A |
| F1 (Churn=Yes) | N/A |

**Interpretation:** The 73.5% accuracy matches the no-information rate (predicting "No" always). GMM is an **unsupervised** method — it clusters by geometric density in feature space, not by the churn label. With a 73/27 class imbalance, both natural density clusters are majority non-churn, so the label assignment collapses.

This is a known limitation of applying unsupervised clustering to imbalanced classification: the clusters reflect feature-space geometry, not the target variable. A supervised model (logistic regression, random forest) or an oversampling technique (SMOTE) before GMM would be needed to actually separate churners from non-churners.

---

## 4. Recommendations

**Segment to prioritize for retention:**
- **Customers without dependents** are the highest-risk group (31.3% churn rate, representing 70% of the customer base). Family-oriented bundles or household plan incentives could improve retention for this segment.
- **Customers with multiple lines** show slightly elevated churn — they are high-value customers (paying for more services), so retention spend is well justified here.

**Model recommendations:**
- Use a supervised classifier (e.g., logistic regression or gradient boosting) for operational churn scoring — GMM is better suited to customer segmentation than binary prediction.
- If unsupervised clustering is required, consider addressing class imbalance first (oversampling the churn class) so that GMM components can align with the minority class.
- Dependent-status segmentation (targeting no-dependent customers with loyalty incentives) is a practical, low-cost retention lever given the 2× churn-rate difference.
