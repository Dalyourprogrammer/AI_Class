# ============================================================
# Sprint5 - Churn Prediction
# Dataset: WA_Fn-UseC_-Telco-Customer-Churn.csv
# Method:  Gaussian Mixture Model (mclust)
# ============================================================

# ----- 0. Install / load packages -----
pkgs <- c("ggplot2", "dplyr", "scales", "mclust", "caret", "reshape2")
for (p in pkgs) {
  if (!requireNamespace(p, quietly = TRUE)) install.packages(p, repos = "https://cloud.r-project.org")
  library(p, character.only = TRUE)
}

setwd("/workspaces/AI_Class/Sprint5/Churn")

# ----- 1. Load & Preprocess -----
df <- read.csv("WA_Fn-UseC_-Telco-Customer-Churn.csv", stringsAsFactors = FALSE)

cat("=== Dataset Overview ===\n")
cat("Rows:", nrow(df), "  Cols:", ncol(df), "\n")
cat("Churn distribution:\n"); print(table(df$Churn))

# Fix TotalCharges blank strings
df$TotalCharges <- as.numeric(df$TotalCharges)
df$TotalCharges[is.na(df$TotalCharges)] <- 0

# Drop customerID
df$customerID <- NULL

# Keep Churn as factor for evaluation; also create numeric version
df$Churn <- factor(df$Churn, levels = c("No", "Yes"))

# ----- 2. EDA: Churn Fraction Plots -----

# Plot 1 — MultipleLines
p1 <- ggplot(df, aes(x = MultipleLines, fill = Churn)) +
  geom_bar(position = "fill") +
  scale_y_continuous(labels = percent_format()) +
  scale_fill_manual(values = c("No" = "#4CAF50", "Yes" = "#F44336")) +
  labs(
    title = "Churn Rate by Multiple Lines",
    x = "Multiple Lines", y = "Fraction of Customers", fill = "Churned"
  ) +
  theme_minimal(base_size = 13) +
  theme(plot.title = element_text(face = "bold"))
ggsave("churn_multilines_plot.png", p1, width = 7, height = 5, dpi = 150)
cat("\nSaved: churn_multilines_plot.png\n")

# Churn rates by MultipleLines
ml_rates <- df %>%
  group_by(MultipleLines) %>%
  summarise(churn_rate = mean(Churn == "Yes"), n = n()) %>%
  arrange(desc(churn_rate))
cat("\nChurn rate by MultipleLines:\n"); print(as.data.frame(ml_rates))

# Plot 2 — Contract
p2 <- ggplot(df, aes(x = Contract, fill = Churn)) +
  geom_bar(position = "fill") +
  scale_y_continuous(labels = percent_format()) +
  scale_fill_manual(values = c("No" = "#4CAF50", "Yes" = "#F44336")) +
  labs(
    title = "Churn Rate by Contract Type",
    x = "Contract Type", y = "Fraction of Customers", fill = "Churned"
  ) +
  theme_minimal(base_size = 13) +
  theme(plot.title = element_text(face = "bold"))
ggsave("churn_contract_plot.png", p2, width = 7, height = 5, dpi = 150)
cat("Saved: churn_contract_plot.png\n")

# Churn rates by Contract
ct_rates <- df %>%
  group_by(Contract) %>%
  summarise(churn_rate = mean(Churn == "Yes"), n = n()) %>%
  arrange(desc(churn_rate))
cat("\nChurn rate by Contract:\n"); print(as.data.frame(ct_rates))

# ----- 3. Preprocessing for GMM -----

# Binary encode Yes/No columns
binary_cols <- c("Partner", "Dependents", "PhoneService", "PaperlessBilling",
                 "OnlineSecurity", "OnlineBackup", "DeviceProtection",
                 "TechSupport", "StreamingTV", "StreamingMovies")
for (col in binary_cols) {
  df[[col]] <- ifelse(df[[col]] == "Yes", 1L, 0L)
}
df$gender <- ifelse(df$gender == "Male", 1L, 0L)

# One-hot encode multi-class categoricals
encode_onehot <- function(data, col) {
  vals <- unique(data[[col]])
  for (v in vals[-1]) {  # drop first level to avoid multicollinearity
    data[[paste0(col, "_", gsub(" |-", "_", v))]] <- as.integer(data[[col]] == v)
  }
  data[[col]] <- NULL
  data
}
for (col in c("MultipleLines", "InternetService", "Contract", "PaymentMethod")) {
  df <- encode_onehot(df, col)
}

# Separate features and target
y <- df$Churn
df$Churn <- NULL
X <- as.matrix(df)

# Scale
X_scaled <- scale(X)

# Train / test split (80/20, stratified)
set.seed(42)
train_idx <- caret::createDataPartition(y, p = 0.8, list = FALSE)
X_train <- X_scaled[train_idx, ]
X_test  <- X_scaled[-train_idx, ]
y_train <- y[train_idx]
y_test  <- y[-train_idx]

cat("\nTrain size:", nrow(X_train), "  Test size:", nrow(X_test), "\n")

# ----- 4. GMM Model -----
cat("\nFitting GMM (G=2)...\n")
gmm <- Mclust(X_train, G = 2, verbose = FALSE)
cat("GMM model type:", gmm$modelName, "\n")

# Map component numbers to Churn labels via majority vote
train_components <- gmm$classification
comp_labels <- sapply(1:2, function(c) {
  idx <- train_components == c
  ifelse(sum(y_train[idx] == "Yes") >= sum(y_train[idx] == "No"), "Yes", "No")
})
cat("Component mapping:", paste0("Component ", 1:2, " -> ", comp_labels, collapse = ", "), "\n")

# Predict on test set
test_pred_comp <- predict(gmm, X_test)$classification
test_pred <- factor(comp_labels[test_pred_comp], levels = c("No", "Yes"))

# ----- 5. Evaluation -----
cat("\n=== Confusion Matrix & Metrics ===\n")
cm <- confusionMatrix(test_pred, y_test, positive = "Yes")
print(cm)

cat("\nPrecision (Yes):", round(cm$byClass["Precision"], 4), "\n")
cat("Recall    (Yes):", round(cm$byClass["Recall"],    4), "\n")
cat("F1 Score  (Yes):", round(cm$byClass["F1"],        4), "\n")

# Save confusion matrix as PNG
cm_df <- as.data.frame(cm$table)
colnames(cm_df) <- c("Predicted", "Actual", "Count")
p_cm <- ggplot(cm_df, aes(x = Actual, y = Predicted, fill = Count)) +
  geom_tile(color = "white") +
  geom_text(aes(label = Count), size = 7, fontface = "bold") +
  scale_fill_gradient(low = "#E3F2FD", high = "#1565C0") +
  labs(title = "Confusion Matrix — GMM Churn Prediction",
       x = "Actual", y = "Predicted") +
  theme_minimal(base_size = 13) +
  theme(plot.title = element_text(face = "bold"),
        legend.position = "right")
ggsave("churn_confusion_matrix.png", p_cm, width = 6, height = 5, dpi = 150)
cat("Saved: churn_confusion_matrix.png\n")

# ----- 6. Validation Set Note -----
cat("\n=== Validation Set Discussion ===\n")
cat("A separate validation set is NOT required for this GMM configuration.\n")
cat("G=2 is fixed by domain knowledge (binary target), so no hyperparameter\n")
cat("is being tuned on data. If G were selected via BIC on training data,\n")
cat("a validation set would be needed to avoid overfitting the G selection.\n")

cat("\nDone. All plots saved to Sprint5/Churn/\n")
