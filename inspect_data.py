import pandas as pd

# Load the GDELT dataset
df = pd.read_csv("gdelt_hormuz_news.csv")

# -----------------------------
# 1. Basic information
# -----------------------------

print("Number of articles:", len(df))

print("\nNumber of columns:", len(df.columns))

print("\nColumn names:")
print(df.columns.tolist())


# -----------------------------
# 2. First 5 articles
# -----------------------------

print("\n\nFirst 5 articles:")
print(df.head())


# -----------------------------
# 3. Article titles
# -----------------------------

print("\n\nArticle titles:")
print(df["title"].to_string(index=False))


# -----------------------------
# 4. Languages
# -----------------------------

print("\n\nLanguages:")
print(df["language"].value_counts())


# -----------------------------
# 5. Source countries
# -----------------------------

print("\n\nSource countries:")
print(df["sourcecountry"].value_counts())


# -----------------------------
# 6. News domains
# -----------------------------

print("\n\nNews sources:")
print(df["domain"].value_counts().head(20))


# -----------------------------
# 7. Missing values
# -----------------------------

print("\n\nMissing values:")
print(df.isnull().sum())