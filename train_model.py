import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

print("Loading training data...")

df = pd.read_csv("training_data.csv")

# Convert date
df["date"] = pd.to_datetime(df["date"])

# Features
features = [
    "event_count",
    "avg_goldstein",
    "avg_tone",
    "total_mentions",
    "goldstein_change",
    "tone_change",
    "event_count_change",
    "risk_change"
]

target = "risk_increase_tomorrow"

X = df[features]
y = df[target]

# -----------------------------------------
# TIME-BASED TRAIN / TEST SPLIT
# -----------------------------------------

# First 80% = training
# Last 20% = testing
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

model = Pipeline([
    ("scaler", StandardScaler()),
    ("classifier", LogisticRegression(
        max_iter=1000,
        random_state=42
    ))
])

model.fit(X_train, y_train)

# Predictions
y_pred = model.predict(X_test)


# -----------------------------------------
# RESULTS
# -----------------------------------------

accuracy = accuracy_score(y_test, y_pred)

print()
print("==============================")
print("   LOGISTIC REGRESSION")
print("==============================")

print(f"Accuracy: {accuracy * 100:.2f}%")

print()
print("Confusion Matrix:")
print(confusion_matrix(y_test, y_pred))

print()
print("Classification Report:")
print(classification_report(y_test, y_pred, zero_division=0))


# -----------------------------------------
# FEATURE IMPORTANCE
# -----------------------------------------

classifier = model.named_steps["classifier"]

coefficients = classifier.coef_[0]

importance = pd.DataFrame({
    "feature": features,
    "coefficient": coefficients,
    "absolute_importance": abs(coefficients)
})

importance = importance.sort_values(
    "absolute_importance",
    ascending=False
)

print()
print("==============================")
print("      FEATURE IMPORTANCE")
print("==============================")

print(importance.to_string(index=False))


# Save feature importance
importance.to_csv(
    "feature_importance.csv",
    index=False
)

print()
print("Saved:")
print("feature_importance.csv")