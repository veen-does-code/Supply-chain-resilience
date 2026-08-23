import pandas as pd

from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    classification_report
)


# ============================================================
# LOAD DATA
# ============================================================

print("Loading training data...")

df = pd.read_csv("training_data.csv")

df["date"] = pd.to_datetime(df["date"])

# Sort chronologically
df = df.sort_values("date").reset_index(drop=True)


# ============================================================
# FEATURES AND TARGET
# ============================================================

features = [
    "event_count",
    "avg_goldstein",
    "avg_tone",
    "total_mentions",
    "risk_score",
    "goldstein_change",
    "tone_change",
    "event_count_change",
    "risk_change"
]

target = "risk_increase_tomorrow"


X = df[features]
y = df[target]


# ============================================================
# TIME-BASED TRAIN / TEST SPLIT
# ============================================================

# 80% training, 20% testing
split_index = int(len(df) * 0.8)

X_train = X.iloc[:split_index]
X_test = X.iloc[split_index:]

y_train = y.iloc[:split_index]
y_test = y.iloc[split_index:]

dates_test = df["date"].iloc[split_index:]


print()
print("Training samples:", len(X_train))
print("Testing samples :", len(X_test))

print()
print("Training target distribution:")
print(y_train.value_counts())

print()
print("Testing target distribution:")
print(y_test.value_counts())


# ============================================================
# LOGISTIC REGRESSION PIPELINE
# ============================================================

print()
print("==============================")
print("   LOGISTIC REGRESSION")
print("==============================")


model = Pipeline([
    (
        "scaler",
        StandardScaler()
    ),
    (
        "logreg",
        LogisticRegression(
            max_iter=5000,
            random_state=42
        )
    )
])


# Train
model.fit(X_train, y_train)


# ============================================================
# PREDICTION
# ============================================================

y_pred = model.predict(X_test)


# ============================================================
# EVALUATION
# ============================================================

accuracy = accuracy_score(y_test, y_pred)

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


# ============================================================
# FEATURE IMPORTANCE
# ============================================================

print()
print("==============================")
print("   FEATURE IMPORTANCE")
print("==============================")


# Get coefficients from Logistic Regression
coefficients = model.named_steps["logreg"].coef_[0]

importance_df = pd.DataFrame({
    "feature": features,
    "coefficient": coefficients,
    "absolute_importance": abs(coefficients)
})

# Sort by importance
importance_df = importance_df.sort_values(
    "absolute_importance",
    ascending=False
).reset_index(drop=True)


print(importance_df.to_string(index=False))


# ============================================================
# SAVE FEATURE IMPORTANCE
# ============================================================

importance_df.to_csv(
    "feature_importance.csv",
    index=False
)


print()
print("Saved:")
print("feature_importance.csv")