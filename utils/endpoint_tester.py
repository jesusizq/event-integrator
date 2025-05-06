import requests
import json

port = 8080
base_url = f"http://localhost:{port}/v1"

def check_health():
    print("Testing health...")
    url = f"{base_url}/health/"
    res = requests.get(url)
    return res.json()

if __name__ == "__main__":
    response = check_health()
    status = response["status"]
    print(f"Health check: {status}")

