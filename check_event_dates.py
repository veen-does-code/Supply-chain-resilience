import pandas as pd

filename = "20260820.export.CSV.zip"

print("Reading GDELT event dates...")

df = pd.read_csv(
    filename,
    sep="\t",
    header=None,
    usecols=[0, 1],
    names=["GLOBALEVENTID", "SQLDATE"],
    compression="zip",
    low_memory=False
)

print("\nNumber of events:", len(df))

print("\nUnique SQLDATE values:")
print(df["SQLDATE"].value_counts().sort_index().to_string())

print("\nMinimum SQLDATE:", df["SQLDATE"].min())
print("Maximum SQLDATE:", df["SQLDATE"].max())