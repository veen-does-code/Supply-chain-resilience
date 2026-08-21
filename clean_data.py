import pandas as pd

# Load GDELT dataset
df = pd.read_csv("gdelt_energy_english.csv")

print("Original number of articles:", len(df))

# --------------------------------------------------
# 1. Keep only the columns we currently need
# --------------------------------------------------

df = df[
    [
        "url",
        "title",
        "seendate",
        "domain",
        "language",
        "sourcecountry"
    ]
]

# --------------------------------------------------
# 2. Remove duplicate articles
# --------------------------------------------------

df = df.drop_duplicates(subset=["url"])

print("After removing duplicate URLs:", len(df))

# --------------------------------------------------
# 3. Remove duplicate titles
# --------------------------------------------------

df = df.drop_duplicates(subset=["title"])

print("After removing duplicate titles:", len(df))

# --------------------------------------------------
# 4. Remove rows with missing values
# --------------------------------------------------

df = df.dropna(subset=["title"])

# --------------------------------------------------
# 5. Reset index
# --------------------------------------------------

df = df.reset_index(drop=True)

# --------------------------------------------------
# 6. Show cleaned dataset
# --------------------------------------------------

print("\nCleaned dataset:")
print(df.head(10))

print("\nNumber of articles after cleaning:", len(df))

# --------------------------------------------------
# 7. Save cleaned dataset
# --------------------------------------------------

df.to_csv("gdelt_energy_clean.csv", index=False)

print("\nClean dataset saved as:")
print("gdelt_energy_clean.csv")