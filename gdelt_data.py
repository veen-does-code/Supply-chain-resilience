import requests
import pandas as pd

url = "https://api.gdeltproject.org/api/v2/doc/doc"

params = {
    "query": '"Strait of Hormuz"',
    "mode": "artlist",
    "format": "json",
    "maxrecords": 75,
    "timespan": "7d"
}

response = requests.get(url, params=params)

data = response.json()

print(data)