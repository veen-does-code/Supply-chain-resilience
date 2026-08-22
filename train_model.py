import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    classification_report
)

print("Loading training data...")

df = pd.read_csv("training_data.csv")

# Features available at the end of today
features = [
    "event_count",
    "avg_goldstein",
    "avg_tone",
    "total_mentions",
    "risk_score",
    "goldstein_change",
    "tone_change",
    "event_count_change"
]

target = "risk_increase_tomorrow"

X = df[features]
y = df[target]

# -----------------------------------------
# TIME-BASED TRAIN / TEST SPLIT
# -----------------------------------------

split_index = int(len(df) * 0.8)

X_train = X.iloc[:split_index]
X_test = X.iloc[split_index:]

y_train = y.iloc[:split_index]
y_test = y.iloc[split_index:]

print()
print("Training samples:", len(X_train))
print("Testing samples :", len(X_test))

print()
print("Training target distribution:")
print(y_train.value_counts())

print()
print("Testing target distribution:")
print(y_test.value_counts())

# -----------------------------------------
# LOGISTIC REGRESSION
# -----------------------------------------

print()
print("==============================")
print("   LOGISTIC REGRESSION")
print("==============================")

model = LogisticRegression(
    max_iter=1000
)

model.fit(X_train, y_train)

# Predictions
y_pred = model.predict(X_test)

# -----------------------------------------
# EVALUATION
# -----------------------------------------

accuracy = accuracy_score(y_test, y_pred)

print()
print(f"Accuracy: {accuracy * 100:.2f}%")

print()
print("Confusion Matrix:")
print(confusion_matrix(y_test, y_pred))

print()
print("Classification Report:")
print(
    classification_report(
        y_test,
        y_pred,
        zero_division=0
    )
)

# -----------------------------------------
# FEATURE IMPORTANCE
# -----------------------------------------

importance = pd.DataFrame({
    "feature": features,
    "coefficient": model.coef_[0]
})

importance["absolute_importance"] = (
    importance["coefficient"].abs()
)

importance = importance.sort_values(
    "absolute_importance",
    ascending=False
)

print()
print("==============================")
print("   FEATURE IMPORTANCE")
print("==============================")

print(importance.to_string(index=False))

# -----------------------------------------
# SAVE
# -----------------------------------------

importance.to_csv(
    "feature_importance.csv",
    index=False
)

print()
print("Saved:")
print("feature_importance.csv")