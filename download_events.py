import requests

date = "20260820"

url = f"https://data.gdeltproject.org/events/{date}.export.CSV.zip"
filename = f"{date}.export.CSV.zip"

print("Downloading:")
print(url)

try:
    response = requests.get(
        url,
        timeout=60
    )

    print("Status:", response.status_code)

    if response.status_code == 200:

        with open(filename, "wb") as f:
            f.write(response.content)

        print("\nDownload successful!")
        print("Saved as:", filename)

    else:

        print("\nDownload failed.")
        print(response.text[:500])

except requests.exceptions.Timeout:

    print("\nThe connection to GDELT timed out.")
    print("Try opening the URL directly in your browser.")

except requests.exceptions.RequestException as e:

    print("\nConnection error:")
    print(e)