import pandas as pd
import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

print("Loading training data...")

df = pd.read_csv("training_data.csv")

# ------------------------------------------------
# TIME-BASED TEST SPLIT
# ------------------------------------------------

split_index = int(len(df) * 0.8)

test_df = df.iloc[split_index:].copy()

# ------------------------------------------------
# NAIVE BASELINE
# ------------------------------------------------
# Predict tomorrow's risk as today's risk

actual = test_df["tomorrow_risk"]
predicted = test_df["risk_score"]

mae = mean_absolute_error(actual, predicted)
rmse = np.sqrt(mean_squared_error(actual, predicted))
r2 = r2_score(actual, predicted)

print()
print("==============================")
print("       NAIVE BASELINE")
print("==============================")

print("Prediction: tomorrow risk = today's risk")

print()
print(f"MAE  : {mae:.2f}")
print(f"RMSE : {rmse:.2f}")
print(f"R²   : {r2:.4f}")

# ------------------------------------------------
# SHOW PREDICTIONS
# ------------------------------------------------

results = pd.DataFrame({
    "date": test_df["date"],
    "actual_tomorrow_risk": actual,
    "predicted_tomorrow_risk": predicted
})

print()
print("==============================")
print(" ACTUAL vs BASELINE")
print("==============================")

print(results.to_string(index=False))