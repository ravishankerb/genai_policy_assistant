#!/usr/bin/env python3
"""
Auto OAuth client for Azure AD that captures the OAuth code and calls /query with ID token.
"""

import requests
import json
import webbrowser
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import os

from dotenv import load_dotenv

load_dotenv()
CLIENT_ID = os.getenv("CLIENT_ID")
TENANT_ID = os.getenv("TENANT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")

# Base API server (your application)
API_BASE_URL = "http://localhost:8000"

def start_callback_server(port, auth_code_holder, server_done_event):
    class CallbackHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            parsed = urlparse(self.path)
            if parsed.path == "/auth/callback":
                query = parse_qs(parsed.query)
                if "code" in query:
                    auth_code_holder["code"] = query["code"][0]
                    self.send_response(200)
                    self.send_header("Content-type", "text/html")
                    self.end_headers()
                    self.wfile.write(b"""
                        <html>
                            <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
                                <h1 style="color: green;"> Authentication Successful!</h1>
                                <p>You can close this window and return to the application.</p>
                            </body>
                        </html>
                    """)
                    server_done_event.set()
                else:
                    self.send_response(400)
                    self.end_headers()
            else:
                self.send_response(404)
                self.end_headers()

        def log_message(self, format, *args):
            return  # suppress default logging

    server = HTTPServer(('localhost', port), CallbackHandler)
    server.serve_forever()

def exchange_code_for_tokens(auth_code):
    token_url = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
   
    data = {
        "grant_type": "authorization_code",
        "client_id": CLIENT_ID,
        "scope": "openid profile email User.Read",
        "code": auth_code,
        "redirect_uri": f"http://localhost:8001/auth/callback",
        "client_secret": CLIENT_SECRET  # only for confidential apps
    }
    resp = requests.post(token_url, data=data)
    if resp.status_code == 200:
        return resp.json()
    else:
        print(f"❌ Token exchange failed: {resp.status_code} {resp.text}")
        return None

def call_query_api(id_token, question="What are the password requirements?"):
    url = f"{API_BASE_URL}/query"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {id_token}"
    }
    data = {"question": question}
    resp = requests.post(url, headers=headers, json=data)
    if resp.status_code == 200:
        try:
            print("✅ Query response:")
            print(json.dumps(resp.json(), indent=2))
        except ValueError:
            print("⚠️ Response is not valid JSON:")
            print(resp.text)
    else:
        print(f"❌ Query failed ({resp.status_code}): {resp.text}")

def test_auto_oauth_flow():
    print("🔐 Testing Auto OAuth Flow with Automatic Code Capture")
    print("="*60)

    # Step 1: Get OAuth login URL from API /login
    r = requests.get(f"{API_BASE_URL}/login", allow_redirects=False)
    if r.status_code not in [302, 307]:
        print(f"❌ Failed to get login URL. Status: {r.status_code}")
        return
    login_url = r.headers.get("Location")
    print(f"✅ Original OAuth URL: {login_url}")

    # Step 2: Replace redirect_uri to use localhost:8001
    parsed = urlparse(login_url)
    query_params = parse_qs(parsed.query)
    callback_port = 8001
    query_params["redirect_uri"] = [f"http://localhost:{callback_port}/auth/callback"]
    new_query = urlencode(query_params, doseq=True)
    updated_url = urlunparse((
        parsed.scheme,
        parsed.netloc,
        parsed.path,
        parsed.params,
        new_query,
        parsed.fragment
    ))
    print(f"📌 Updated OAuth URL: {updated_url}")

    # Step 3: Start callback server
    auth_code_holder = {}
    server_done_event = threading.Event()
    server_thread = threading.Thread(target=start_callback_server, args=(callback_port, auth_code_holder, server_done_event))
    server_thread.daemon = True
    server_thread.start()
    print(f"✅ Callback server started at http://localhost:{callback_port}/auth/callback")

    # Step 4: Open browser for authentication
    print("🌐 Opening browser for authentication...")
    webbrowser.open(updated_url)

    # Step 5: Wait for code
    print("⏳ Waiting for OAuth callback...")
    if server_done_event.wait(timeout=300):
        auth_code = auth_code_holder.get("code")
        print(f"🎉 OAuth code captured: {auth_code[:50]}...")
    else:
        print("❌ Timeout waiting for OAuth callback")
        return

    # Step 6: Exchange code for tokens
    tokens = exchange_code_for_tokens(auth_code)
    if not tokens:
        return

    id_token = tokens.get("id_token")
    if not id_token:
        print("❌ No id_token returned")
        return

    print(f"\n5. Using REAL ID token: {id_token[:20]}...")

    # Step 7: Call /query with ID token
    call_query_api(id_token)

if __name__ == "__main__":
    test_auto_oauth_flow()
