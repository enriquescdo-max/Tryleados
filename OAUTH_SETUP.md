# LeadOS OAuth Setup Guide
## Google, Microsoft & Apple Sign-In — Step by Step

---

## How it works (overview)

When a user clicks "Continue with Google", they are redirected to Google's login page.
After they approve, Google sends a `code` back to your backend callback URL.
Your backend exchanges that code for an access token, gets the user's profile,
creates (or finds) their account, and redirects to the app with a session token.

The frontend never sees API secrets — everything sensitive stays on your server.

---

## 1. Google Sign-In

### Step 1 — Create a Google Cloud project
1. Go to https://console.cloud.google.com
2. Click "New Project" — name it "LeadOS"
3. Select the project

### Step 2 — Enable the OAuth API
1. Go to APIs & Services → Credentials
2. Click "Configure Consent Screen" → External → Fill in app name "LeadOS", your email
3. Add scopes: `email`, `profile`, `openid`
4. Add yourself as a test user

### Step 3 — Create OAuth credentials
1. Credentials → Create Credentials → OAuth 2.0 Client ID
2. Application type: **Web application**
3. Authorized redirect URIs — add:
   - `http://localhost:8000/auth/google/callback` (local dev)
   - `https://yourdomain.com/auth/google/callback` (production)
4. Copy the **Client ID** and **Client Secret**

### Step 4 — Add to .env
```
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-your-secret
```

---

## 2. Microsoft Sign-In

### Step 1 — Register an app in Azure
1. Go to https://portal.azure.com
2. Search for "App registrations" → New registration
3. Name: "LeadOS"
4. Supported account types: **Accounts in any organizational directory and personal Microsoft accounts**
5. Redirect URI: Web → `https://yourdomain.com/auth/microsoft/callback`

### Step 2 — Get your credentials
1. After creation, copy the **Application (client) ID** from the Overview page
2. Go to Certificates & secrets → New client secret → Copy the **Value**

### Step 3 — Add to .env
```
MICROSOFT_CLIENT_ID=your-application-client-id
MICROSOFT_CLIENT_SECRET=your-client-secret-value
MICROSOFT_TENANT_ID=common
```

---

## 3. Apple Sign-In

Apple requires the most setup but gives access to 1B+ iPhone users.

### Step 1 — Apple Developer account
- You need an Apple Developer account ($99/year) at https://developer.apple.com

### Step 2 — Register a Services ID (this is your OAuth "client")
1. Certificates, Identifiers & Profiles → Identifiers → + (Add new)
2. Select **Services IDs** → Continue
3. Description: "LeadOS"
4. Identifier: `com.yourcompany.leadOS` (reverse domain format)
5. Enable "Sign in with Apple" → Configure
6. Primary App ID: select your main app bundle (or create one)
7. Domains: `yourdomain.com`
8. Return URLs: `https://yourdomain.com/auth/apple/callback`

### Step 3 — Create a private key
1. Keys → + (Add new)
2. Name: "LeadOS Sign In Key"
3. Enable "Sign in with Apple" → Configure → Select your app
4. Download the `.p8` private key file (download it once — can't re-download)
5. Note your **Key ID**

### Step 4 — Add to .env
```
APPLE_SERVICE_ID=com.yourcompany.leadOS
APPLE_TEAM_ID=YOUR10CHARID
APPLE_KEY_ID=YOUR10CHARKEY
APPLE_PRIVATE_KEY_PATH=/path/to/AuthKey_XXXXXXXXXX.p8
```

---

## 4. Backend callback routes to add

Add these 3 routes to `leadOS/api/server.py` (the OAuth callback handlers):

```python
from authlib.integrations.starlette_client import OAuth
from starlette.requests import Request
import os

oauth = OAuth()

# Register providers
oauth.register('google',
    client_id=os.getenv('GOOGLE_CLIENT_ID'),
    client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'},
)

oauth.register('microsoft',
    client_id=os.getenv('MICROSOFT_CLIENT_ID'),
    client_secret=os.getenv('MICROSOFT_CLIENT_SECRET'),
    server_metadata_url=f'https://login.microsoftonline.com/{os.getenv("MICROSOFT_TENANT_ID","common")}/v2.0/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'},
)

# Google callback
@app.get('/auth/google/callback')
async def google_callback(request: Request):
    token = await oauth.google.authorize_access_token(request)
    user_info = token.get('userinfo')
    session_token = _create_session({
        'id': f"google_{user_info['sub']}",
        'email': user_info['email'],
        'name': user_info.get('name', user_info['email']),
        'role': 'user',
    })
    from fastapi.responses import RedirectResponse
    return RedirectResponse(
        url=f"/leadOS-login.html?provider=google&token={session_token}"
            f"&email={user_info['email']}&name={user_info.get('name','')}"
    )

# Microsoft callback  
@app.get('/auth/microsoft/callback')
async def microsoft_callback(request: Request):
    token = await oauth.microsoft.authorize_access_token(request)
    user_info = token.get('userinfo') or {}
    email = user_info.get('email') or user_info.get('preferred_username', '')
    session_token = _create_session({
        'id': f"msft_{user_info.get('oid', email)}",
        'email': email,
        'name': user_info.get('name', email),
        'role': 'user',
    })
    from fastapi.responses import RedirectResponse
    return RedirectResponse(
        url=f"/leadOS-login.html?provider=microsoft&token={session_token}&email={email}"
    )
```

### Install the OAuth library
```bash
pip install authlib httpx
```

---

## 5. Inject client IDs into the frontend

The frontend reads `window.__GOOGLE_CLIENT_ID__` etc. In production, inject
these via a template tag in your FastAPI server:

```python
@app.get('/leadOS-login.html')
async def serve_login():
    with open('leadOS-login.html') as f:
        content = f.read()
    # Inject client IDs so the frontend can build the OAuth URLs
    content = content.replace(
        '</head>',
        f'<script>'
        f'window.__GOOGLE_CLIENT_ID__ = "{os.getenv("GOOGLE_CLIENT_ID","")}";\n'
        f'window.__MICROSOFT_CLIENT_ID__ = "{os.getenv("MICROSOFT_CLIENT_ID","")}";\n'
        f'window.__APPLE_SERVICE_ID__ = "{os.getenv("APPLE_SERVICE_ID","")}";\n'
        f'</script></head>'
    )
    from fastapi.responses import HTMLResponse
    return HTMLResponse(content)
```

---

## 6. Test checklist

- [ ] Google: click button → Google login page opens → approve → redirects to dashboard
- [ ] Microsoft: click button → Microsoft login page opens → approve → redirects to dashboard
- [ ] Apple: click button → Apple login page opens → approve → redirects to dashboard
- [ ] Email/password still works
- [ ] Demo login still works
- [ ] In MOCK_MODE, all three simulate instantly without any credentials

---

## Quick start — just want Google first?

That's the most common path. Just:
1. Set up Google (Step 1 above) — 15 minutes
2. Add `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` to `.env`
3. Add the Google callback route to `server.py`
4. Microsoft and Apple buttons show the setup notice until you add their credentials

---

*LeadOS OAuth Setup Guide — v1.0*
