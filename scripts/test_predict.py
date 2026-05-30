
import requests
import json

url = "http://127.0.0.1:8000/api/predict"
payload = {
    "team": ["Toxapex", "Blissey", "Corviknight", "Clodsire", "Dondozo", "Alomomola"]
}

response = requests.post(url, json=payload)
print(json.dumps(response.json(), indent=2))
