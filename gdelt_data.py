import requests
import pandas as pd
import time

url = "https://api.gdeltproject.org/api/v2/doc/doc"

params = {
    "query": '"Strait of Hormuz"',
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

    print("\nColumn names:")
    print(df.columns.tolist())

    print("\nData types:")
    print(df.dtypes)

    print("\nFirst 5 titles:")
    print(df["title"].to_string(index=False))

    print("\nNumber of articles:", len(df))
    print("\nColumns:")
    print(df.columns.tolist())

    print("\nFirst 5 articles:")
    print(df.head())

    df.to_csv("gdelt_hormuz_news.csv", index=False)

    print("\nDataset saved successfully!")

elif response.status_code == 429:

    print("\nGDELT rate limit reached.")
    print("Wait at least 5 seconds before trying again.")

else:

    print("\nGDELT returned an error:")
    print(response.text)