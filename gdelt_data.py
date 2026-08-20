import requests
import pandas as pd

# GDELT API endpoint
url = "https://api.gdeltproject.org/api/v2/doc/doc"

# Search parameters
params = {
    "query": '("Strait of Hormuz" OR "Red Sea" OR "crude oil" OR petroleum OR tanker OR sanctions) sourcelang:english',
    "mode": "artlist",
    "format": "json",
    "maxrecords": 50,
    "timespan": "7d"
}

print("Requesting GDELT...")

response = requests.get(url, params=params)

print("Status:", response.status_code)

if response.status_code == 200:

    data = response.json()

    articles = data.get("articles", [])

    df = pd.DataFrame(articles)

    print("\nNumber of articles:", len(df))

    print("\nColumns:")
    print(df.columns.tolist())

    print("\nLanguages:")
    print(df["language"].value_counts())

    print("\nFirst 10 titles:")
    print(df["title"].head(10).to_string(index=False))

    # Save dataset
    df.to_csv("gdelt_energy_english.csv", index=False)

    print("\nDataset saved successfully!")
    print("File: gdelt_energy_english.csv")

else:
    print("\nGDELT returned an error:")
    print(response.text)