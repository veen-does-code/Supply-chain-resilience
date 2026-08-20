import requests
import pandas as pd

# GDELT API endpoint
url = "https://api.gdeltproject.org/api/v2/doc/doc"

# Search parameters
params = {
    "query": '"Strait of Hormuz"',
    "mode": "artlist",
    "format": "json",
    "maxrecords": 50,
    "timespan": "7d"
}

print("Requesting GDELT...")

# Send request
response = requests.get(url, params=params)

print("Status:", response.status_code)

# Check if request was successful
if response.status_code == 200:

    # Convert JSON response into Python dictionary
    data = response.json()

    # Get the articles
    articles = data.get("articles", [])

    # Convert articles into a Pandas DataFrame
    df = pd.DataFrame(articles)

    print("\nNumber of articles:", len(df))

    # Display column names
    print("\nColumn names:")
    print(df.columns.tolist())

    # Display data types
    print("\nData types:")
    print(df.dtypes)

    # Display first 5 article titles
    print("\nFirst 5 titles:")
    if "title" in df.columns:
        print(df["title"].head().to_string(index=False))

    # Display first 5 rows
    print("\nFirst 5 rows:")
    print(df.head())

    # Save dataset
    df.to_csv("gdelt_hormuz_news.csv", index=False)

    print("\nDataset saved successfully!")
    print("File: gdelt_hormuz_news.csv")

else:

    # Handle errors
    print("\nGDELT returned an error:")
    print(response.text)