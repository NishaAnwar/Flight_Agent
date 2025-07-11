
import requests
def authenticate(_: str) -> str:
    url = "https://bookmesky.com/partner/api/auth/token"
    headers = {"Content-Type": "application/json"}
    payload = {
        "username": "bookme-sky",
        "password": "omi@work321"
    }
    r = requests.post(url, json=payload,headers=headers)
    if r.status_code in [200, 201]:
        return r.json().get("Token")
    return " "
