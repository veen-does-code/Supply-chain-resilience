import requests
from datetime import datetime, timedelta
import os
import time


# ==========================================
# SETTINGS
# ==========================================

START_DATE = datetime(2026, 8, 1)
END_DATE = datetime(2026, 8, 20)

BASE_URL = "https://data.gdeltproject.org/events/"


# ==========================================
# DOWNLOAD FILES
# ==========================================

current_date = START_DATE

while current_date <= END_DATE:

    date_string = current_date.strftime("%Y%m%d")

    filename = f"{date_string}.export.CSV.zip"

    url = BASE_URL + filename

    print("\nDownloading:")
    print(url)

    # Don't download if already present
    if os.path.exists(filename):

        print("Already exists. Skipping.")

    else:

        try:

            response = requests.get(
                url,
                timeout=60
            )

            print("Status:", response.status_code)

            if response.status_code == 200:

                with open(filename, "wb") as f:
                    f.write(response.content)

                print("Download successful!")
                print("Saved as:", filename)

            else:

                print("Download failed.")

        except requests.exceptions.RequestException as e:

            print("Connection error:")
            print(e)

    # Wait before next request
    time.sleep(2)

    current_date += timedelta(days=1)


print("\n================================")
print("DOWNLOAD COMPLETE")
print("================================")