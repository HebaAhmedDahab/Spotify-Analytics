import os
import requests
from dotenv import load_dotenv
from urllib.parse import urlencode
import webbrowser

load_dotenv()
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")
AUTH_URL = "https://accounts.spotify.com/authorize"
TOKEN_URL = "https://accounts.spotify.com/api/token"
REFRESH_URL = os.getenv("REFRESH_URL")

params = {
    "client_id": CLIENT_ID,
    "response_type": "code",
    "redirect_uri": REDIRECT_URI,
    "scope": "user-read-recently-played",
}
auth_url = f"{AUTH_URL}?{urlencode(params)}"
code = input("Enter Authorization Code: ")
data = {
    "grant_type": "authorization_code",
    "code": code,
    "redirect_uri": REDIRECT_URI,
    "client_id": CLIENT_ID,
    "client_secret": CLIENT_SECRET,
}
response = requests.post(TOKEN_URL, data=data)

def get_access_token():
    data = {
        "grant_type": "refresh_token",
        "refresh_token": REFRESH_URL,
    }
    response = requests.post(
        TOKEN_URL, data=data, auth=(CLIENT_ID, CLIENT_SECRET)
    )
    response.raise_for_status()
    return response.json()["access_token"]
    