import pandas as pd

df = pd.read_csv("gdelt_energy_english.csv")

print("Number of articles:", len(df))

print("\nColumns:")
print(df.columns.tolist())

print("\nLanguages:")
print(df["language"].value_counts())

print("\nSource countries:")
print(df["sourcecountry"].value_counts())

print("\nNews sources:")
print(df["domain"].value_counts().head(20))

print("\n\nArticle titles:")
print(df["title"].to_string(index=False))

print("\n\nMissing values:")
print(df.isnull().sum())