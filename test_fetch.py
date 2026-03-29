import json
import urllib.request

url = "https://archive.org/download/causaganha-catalog/completed-items.json"
req = urllib.request.Request(url)
with urllib.request.urlopen(req) as response:
    data = json.loads(response.read().decode())

for date, info in data.get("completed_items", {}).items():
    if "tribunais_coletados" in info:
        print(f"Found in {date}")
        break
else:
    print("Not found")
