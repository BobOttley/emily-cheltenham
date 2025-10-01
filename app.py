# emily_cheltenham_enhanced.py
# Enhanced Emily for Cheltenham College with Microsoft 365 Email Integration

import os
import ssl
import time
import json
import requests
import pickle
import subprocess
from pathlib import Path
from datetime import datetime, timedelta, timezone
from urllib.parse import quote
from typing import Optional, Dict, Any, List

from flask import Flask, redirect, request, session, jsonify, render_template
from flask_cors import CORS
from dotenv import load_dotenv
from openai import OpenAI
from bs4 import BeautifulSoup

# Load environment variables
load_dotenv()

# Initialize OpenAI client
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Microsoft app settings
CLIENT_ID = os.getenv("MS_CLIENT_ID")
CLIENT_SECRET = os.getenv("MS_CLIENT_SECRET")
REDIRECT_URI = os.getenv("MS_REDIRECT_URI", "https://localhost:5000/auth/callback")
TENANT = os.getenv("MS_TENANT", "common")
FLASK_SECRET = os.getenv("FLASK_SECRET", "dev-only-change-me-in-production")

if not CLIENT_ID or not CLIENT_SECRET:
    raise RuntimeError("Set MS_CLIENT_ID and MS_CLIENT_SECRET in .env")

# Microsoft OAuth endpoints
AUTH_URL = f"https://login.microsoftonline.com/{TENANT}/oauth2/v2.0/authorize"
TOKEN_URL = f"https://login.microsoftonline.com/{TENANT}/oauth2/v2.0/token"
GRAPH_URL = "https://graph.microsoft.com/v1.0"

# Corrected scopes (no URL prefix for standard scopes)
SCOPES = [
    "offline_access",
    "openid",
    "profile",
    "email",
    "User.Read",
    "Mail.Read",
    "Mail.ReadWrite",
    "Mail.Send",
    "Calendars.ReadWrite",
    "MailboxSettings.Read",
    "Contacts.ReadWrite"
]
SCOPE_STR = " ".join(SCOPES)

# Initialize Flask app
app = Flask(__name__, static_folder='static', static_url_path='/static', template_folder='templates')
app.secret_key = FLASK_SECRET

# Configure session for HTTPS
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'None'
app.config['SESSION_COOKIE_NAME'] = 'emily_cheltenham_session'

CORS(app, supports_credentials=True)

# Load Cheltenham College knowledge base (if available)
EMBEDDINGS_PATH = os.path.join(os.path.dirname(__file__), "doc_embeddings.pkl")
METADATA_PATH = os.path.join(os.path.dirname(__file__), "metadata.pkl")

try:
    with open(EMBEDDINGS_PATH, 'rb') as f:
        DOC_EMBEDDINGS = pickle.load(f)
    with open(METADATA_PATH, 'rb') as f:
        METADATA = pickle.load(f)
    print(f"✅ Loaded {len(DOC_EMBEDDINGS)} knowledge base embeddings")
except Exception as e:
    print(f"⚠️ Could not load embeddings: {e}")
    DOC_EMBEDDINGS = []
    METADATA = []

# ----------------- SSL Certificate Management -----------------

def create_self_signed_cert():
    """Create a self-signed certificate for development"""
    cert_dir = Path("certs")
    cert_dir.mkdir(exist_ok=True)
    
    cert_file = cert_dir / "cert.pem"
    key_file = cert_dir / "key.pem"
    
    if cert_file.exists() and key_file.exists():
        try:
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            context.load_cert_chain(str(cert_file), str(key_file))
            print(f"✅ Using existing certificate: {cert_file}")
            return str(cert_file), str(key_file)
        except Exception as e:
            print(f"⚠️ Existing certificate invalid: {e}")
            cert_file.unlink(missing_ok=True)
            key_file.unlink(missing_ok=True)
    
    try:
        print("🔐 Generating new self-signed certificate...")
        result = subprocess.run([
            'openssl', 'req', '-x509', '-newkey', 'rsa:2048',
            '-keyout', str(key_file),
            '-out', str(cert_file),
            '-days', '365',
            '-nodes',
            '-subj', '/C=GB/ST=England/L=Cheltenham/O=CheltenhamCollege/CN=localhost'
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ Created self-signed certificate: {cert_file}")
            return str(cert_file), str(key_file)
        else:
            print(f"❌ OpenSSL error: {result.stderr}")
            return None, None
    except FileNotFoundError:
        print("❌ OpenSSL not found. Please install OpenSSL.")
        return None, None
    except Exception as e:
        print(f"❌ Could not create certificate: {e}")
        return None, None

# ----------------- Token Management -----------------

def _now():
    return int(time.time())

def _save_tokens(tok: dict):
    session["access_token"] = tok.get("access_token")
    session["refresh_token"] = tok.get("refresh_token")
    session["expires_at"] = _now() + int(tok.get("expires_in", 3599))

def _need_refresh() -> bool:
    return not session.get("access_token") or (_now() >= int(session.get("expires_at", 0)) - 60)

def _refresh_tokens_if_needed():
    """Refresh tokens if needed"""
    if not _need_refresh():
        return True
    
    rt = session.get("refresh_token")
    if not rt:
        print("No refresh token available")
        return False
    
    try:
        data = {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "grant_type": "refresh_token",
            "refresh_token": rt,
            "redirect_uri": REDIRECT_URI,
            "scope": SCOPE_STR
        }
        resp = requests.post(TOKEN_URL, data=data, timeout=10)
        
        if resp.ok:
            token_data = resp.json()
            _save_tokens(token_data)
            print("Tokens refreshed successfully")
            return True
        else:
            print(f"Token refresh failed: {resp.status_code} - {resp.text}")
            session.pop("access_token", None)
            session.pop("refresh_token", None)
            session.pop("expires_at", None)
            return False
            
    except Exception as e:
        print(f"Error refreshing tokens: {e}")
        return False

def _auth_headers():
    _refresh_tokens_if_needed()
    at = session.get("access_token")
    if not at:
        return None
    return {"Authorization": f"Bearer {at}", "Content-Type": "application/json"}

def _me(headers):
    """Get user info"""
    try:
        r = requests.get(f"{GRAPH_URL}/me", headers=headers, timeout=10)
        if r.ok:
            return r.json()
        else:
            print(f"Graph API /me error: {r.status_code} - {r.text}")
            return {"error": r.text}
    except Exception as e:
        print(f"Error in _me: {e}")
        return {"error": str(e)}

def get_user_info():
    """Get current user information"""
    headers = _auth_headers()
    if not headers:
        return None
    return _me(headers)

def _extract_plaintext_from_email(msg: dict) -> str:
    """Extract plain text from HTML email content"""
    body = (msg or {}).get("body", {})
    content = body.get("content") or ""
    content_type = (body.get("contentType") or "text").lower()
    
    if content_type == "html":
        soup = BeautifulSoup(content, 'html.parser')
        for script in soup(["script", "style"]):
            script.decompose()
        text = soup.get_text()
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)
        return text[:2000]
    return content.strip()[:2000]

# ----------------- Authentication Routes -----------------

@app.route("/")
def home():
    """Main dashboard"""
    if "access_token" not in session:
        return redirect("/login")
    
    user = get_user_info()
    if not user or "error" in user:
        session.clear()
        return redirect("/login")
    
    return render_template("index.html", user=user)

@app.route("/api/status")
def api_status():
    """Check authentication status"""
    if "access_token" not in session:
        return jsonify({"authenticated": False})
    
    _refresh_tokens_if_needed()
    
    if "access_token" not in session:
        return jsonify({"authenticated": False})
    
    h = _auth_headers()
    if not h:
        return jsonify({"authenticated": False})
    
    try:
        r = requests.get(f"{GRAPH_URL}/me", headers=h, timeout=10)
        
        if r.ok:
            me = r.json()
            display_name = (
                me.get("displayName") or 
                me.get("givenName") or 
                ""
            )
            email = (
                me.get("mail") or 
                me.get("userPrincipalName") or 
                ""
            )
            
            if not display_name and email:
                email_name = email.split('@')[0]
                display_name = ' '.join(
                    word.capitalize() 
                    for word in email_name.replace('.', ' ').replace('_', ' ').split()
                )
            
            if not display_name:
                display_name = "User"
            
            return jsonify({
                "authenticated": True,
                "user": {
                    "name": display_name,
                    "email": email,
                    "id": me.get("id", "")
                }
            })
        else:
            if r.status_code == 401:
                session.clear()
                return jsonify({"authenticated": False})
            
            return jsonify({
                "authenticated": True,
                "user": {"name": "User", "email": "", "id": ""}
            })
            
    except Exception as e:
        print(f"Error getting user info: {e}")
        return jsonify({
            "authenticated": True,
            "user": {"name": "User", "email": "", "id": ""}
        })

@app.route("/login")
def login():
    """Initiate OAuth flow"""
    params = {
        "client_id": CLIENT_ID,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "response_mode": "query",
        "scope": SCOPE_STR,
        "prompt": "select_account"
    }
    q = "&".join([f"{k}={quote(v)}" for k, v in params.items()])
    auth_url = f"{AUTH_URL}?{q}"
    print(f"Redirecting to: {auth_url}")
    return redirect(auth_url)

@app.route("/auth/callback")
def callback():
    """Handle OAuth callback"""
    code = request.args.get("code")
    error = request.args.get("error")
    
    if error:
        print(f"OAuth error: {error}")
        return f"Authentication error: {error}", 400
    
    if not code:
        return "Missing authorization code", 400
    
    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPE_STR
    }
    
    try:
        tok_response = requests.post(TOKEN_URL, data=data, timeout=10)
        tok = tok_response.json()
        
        if "access_token" not in tok:
            print(f"Token error: {tok}")
            return jsonify(tok), 400
            
        _save_tokens(tok)
        print("Tokens saved successfully")
        return redirect("/")
        
    except Exception as e:
        print(f"Token exchange error: {e}")
        return f"Token exchange failed: {e}", 500

@app.route("/logout", methods=["POST"])
def logout():
    """Sign out user"""
    session.clear()
    return jsonify({"success": True})

# ----------------- Email Routes -----------------

@app.route("/api/emails/inbox", methods=["GET"])
def get_inbox():
    """Get inbox messages with summaries"""
    h = _auth_headers()
    if not h:
        return jsonify({"error": "Not authenticated"}), 401
    
    top = request.args.get("top", "20")
    url = f"{GRAPH_URL}/me/mailFolders/Inbox/messages?$top={top}&$orderby=receivedDateTime desc"
    
    try:
        r = requests.get(url, headers=h, timeout=10)
        
        if not r.ok:
            return jsonify({"error": "Failed to fetch emails"}), r.status_code
        
        messages = r.json().get("value", [])
        summaries = []
        
        for msg in messages:
            from_address = "unknown"
            if msg.get("from"):
                from_address = msg["from"].get("emailAddress", {}).get("address", "unknown")
            
            summaries.append({
                "id": msg.get("id"),
                "subject": msg.get("subject", "No subject"),
                "from": from_address,
                "received": msg.get("receivedDateTime", ""),
                "isRead": msg.get("isRead", False),
                "hasAttachments": msg.get("hasAttachments", False)
            })
        
        return jsonify({"summaries": summaries, "total": len(summaries)})
        
    except Exception as e:
        print(f"Inbox error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/emails/draft", methods=["POST"])
def create_email_draft():
    """Create a new email draft in Outlook or send immediately"""
    h = _auth_headers()
    if not h:
        return jsonify({"error": "Not authenticated"}), 401
    
    data = request.get_json() or {}
    send_immediately = data.get("send", False)  # Check if user wants to send
    
    message_data = {
        "subject": data.get("subject", "Draft Email" if not send_immediately else "Email"),
        "body": {
            "contentType": "HTML",
            "content": data.get("body", "<p>Email content</p>")
        },
        "toRecipients": [
            {"emailAddress": {"address": email}} 
            for email in (data.get("to", []) if isinstance(data.get("to"), list) else [data.get("to")] if data.get("to") else [])
        ]
    }
    
    # Add CC recipients if provided
    if data.get("cc"):
        message_data["ccRecipients"] = [
            {"emailAddress": {"address": email}}
            for email in (data.get("cc", []) if isinstance(data.get("cc"), list) else [data.get("cc")])
        ]
    
    if send_immediately:
        # Send email immediately
        payload = {"message": message_data, "saveToSentItems": "true"}
        r = requests.post(
            f"{GRAPH_URL}/me/sendMail",
            headers=h,
            data=json.dumps(payload)
        )
        
        if not r.ok:
            print(f"Failed to send email: {r.status_code} - {r.text}")
            return jsonify({"error": "Failed to send email"}), r.status_code
        
        # sendMail returns 202 with no body
        return jsonify({
            "success": True,
            "sent": True,
            "subject": message_data.get("subject"),
            "message": "Email sent successfully"
        })
    else:
        # Create draft
        message_data["isDraft"] = True
        r = requests.post(f"{GRAPH_URL}/me/messages", headers=h, data=json.dumps(message_data))
        
        if not r.ok:
            print(f"Failed to create draft: {r.status_code} - {r.text}")
            return jsonify({"error": "Failed to create draft"}), r.status_code
        
        created_draft = r.json()
        
        return jsonify({
            "success": True,
            "sent": False,
            "draftId": created_draft.get("id"),
            "subject": created_draft.get("subject"),
            "message": "Draft created successfully in Outlook - check your Drafts folder"
        })

@app.route("/api/emails/<message_id>/reply-draft", methods=["POST"])
def create_reply_draft(message_id):
    """Create AI-powered draft reply"""
    h = _auth_headers()
    if not h:
        return jsonify({"error": "Not authenticated"}), 401
    
    user_info = _me(h)
    user_email = user_info.get("mail") or user_info.get("userPrincipalName")
    user_name = user_info.get("displayName", "User")
    
    # Get original message
    r = requests.get(f"{GRAPH_URL}/me/messages/{message_id}", headers=h)
    if not r.ok:
        return jsonify({"error": "Could not load message"}), r.status_code
    
    original_msg = r.json()
    sender = original_msg.get("from", {}).get("emailAddress", {})
    subject = original_msg.get("subject", "")
    original_text = _extract_plaintext_from_email(original_msg)
    
    # Generate AI reply
    system_msg = f"""You are Emily, an AI assistant for Cheltenham College helping {user_name} draft email replies.

IMPORTANT:
- Write the reply as if you are {user_name}, not as Emily
- Use British spelling and professional tone
- Format as HTML for Outlook (use <p>, <ul>, <strong> tags)
- Sign as "{user_name}" and add "(Draft - Please Review)" after signature"""
    
    user_msg = f"""
Original email from: {sender.get('name', sender.get('address'))}
Subject: {subject}

Original message:
{original_text[:1500]}

Please write a professional reply FROM {user_name}."""

    try:
        resp = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg}
            ],
            temperature=0.3,
            max_tokens=500
        )
        body_html = resp.choices[0].message.content or "<p>Draft prepared.</p>"
    except Exception as e:
        return jsonify({"error": f"OpenAI error: {e}"}), 500
    
    # Create reply draft
    r = requests.post(f"{GRAPH_URL}/me/messages/{message_id}/createReply", headers=h)
    if not r.ok:
        return jsonify({"error": "Failed to create reply"}), r.status_code
    
    draft = r.json()
    draft_id = draft.get("id")
    
    # Update with AI content
    patch = {
        "body": {
            "contentType": "HTML",
            "content": body_html
        }
    }
    
    r2 = requests.patch(f"{GRAPH_URL}/me/messages/{draft_id}", headers=h, data=json.dumps(patch))
    
    if not r2.ok:
        return jsonify({"error": "Failed to update draft"}), r2.status_code
    
    return jsonify({
        "success": True,
        "draftId": draft_id,
        "message": "Reply draft created successfully"
    })

# ----------------- Calendar Routes -----------------

@app.route("/api/calendar/today", methods=["GET"])
def calendar_today():
    """Get today's calendar events"""
    h = _auth_headers()
    if not h:
        return jsonify({"error": "Not authenticated"}), 401
    
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow = today + timedelta(days=1)
    
    filter_str = f"start/dateTime ge '{today.isoformat()}Z' and start/dateTime lt '{tomorrow.isoformat()}Z'"
    url = f"{GRAPH_URL}/me/events?$filter={quote(filter_str)}&$orderby=start/dateTime"
    
    r = requests.get(url, headers=h)
    
    if not r.ok:
        return jsonify({"events": [], "count": 0, "summary": "Unable to load calendar"})
    
    events = r.json().get("value", [])
    
    return jsonify({
        "date": today.strftime("%A, %d %B %Y"),
        "count": len(events),
        "events": events,
        "summary": f"You have {len(events)} meeting{'s' if len(events) != 1 else ''} today"
    })

@app.route("/api/meetings/create", methods=["POST"])
def create_meeting():
    """Create Teams meeting"""
    h = _auth_headers()
    if not h:
        return jsonify({"error": "Not authenticated"}), 401
    
    j = request.get_json() or {}
    
    subject = j.get("subject", "Meeting")
    attendees = j.get("attendees", [])
    start = j.get("start")
    end = j.get("end")
    tz = j.get("timeZone", "Europe/London")
    body_html = j.get("bodyHtml", "<p>Meeting agenda</p>")
    
    if not attendees or not start or not end:
        return jsonify({"error": "attendees, start, end required"}), 400
    
    event = {
        "subject": subject,
        "body": {"contentType": "HTML", "content": body_html},
        "start": {"dateTime": start, "timeZone": tz},
        "end": {"dateTime": end, "timeZone": tz},
        "attendees": [
            {"emailAddress": {"address": a}, "type": "required"} for a in attendees
        ],
        "isOnlineMeeting": True,
        "onlineMeetingProvider": "teamsForBusiness"
    }
    
    r = requests.post(f"{GRAPH_URL}/me/events", headers=h, data=json.dumps(event))
    
    if not r.ok:
        return jsonify({"error": r.text}), r.status_code
    
    created = r.json()
    
    return jsonify({
        "success": True,
        "eventId": created.get("id"),
        "joinUrl": (created.get("onlineMeeting") or {}).get("joinUrl"),
        "subject": created.get("subject")
    })

# ----------------- Contact Routes -----------------

@app.route('/api/contacts/create', methods=['POST'])
def create_contact():
    """Create contact in Outlook"""
    h = _auth_headers()
    if not h:
        return jsonify({'error': 'Not authenticated'}), 401
    
    data = request.get_json() or {}
    
    contact_data = {
        "givenName": data.get('firstName', ''),
        "surname": data.get('lastName', ''),
        "emailAddresses": [],
        "businessPhones": [],
        "companyName": data.get('company', ''),
        "jobTitle": data.get('jobTitle', '')
    }
    
    if data.get('email'):
        contact_data["emailAddresses"] = [{
            "address": data.get('email'),
            "name": f"{data.get('firstName', '')} {data.get('lastName', '')}".strip()
        }]
    
    if data.get('phone'):
        contact_data["businessPhones"] = [data.get('phone')]
    
    try:
        response = requests.post(
            f'{GRAPH_URL}/me/contacts',
            headers=h,
            data=json.dumps(contact_data)
        )
        
        if response.ok:
            created_contact = response.json()
            return jsonify({
                'success': True,
                'contactId': created_contact.get('id'),
                'displayName': created_contact.get('displayName')
            })
        else:
            return jsonify({'error': 'Failed to create contact'}), response.status_code
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ----------------- Knowledge Base Search -----------------

@app.route("/api/knowledge/search", methods=["POST"])
def search_knowledge():
    """Search Cheltenham College knowledge base"""
    data = request.get_json() or {}
    query = data.get("query", "")
    
    if not query or len(METADATA) == 0:
        return jsonify({"results": [], "message": "No results found"})
    
    results = []
    query_lower = query.lower()
    
    for meta in METADATA:
        text = meta.get("text", "").lower()
        if query_lower in text:
            results.append({
                "text": meta.get("text", "")[:500],
                "relevance": text.count(query_lower)
            })
    
    results.sort(key=lambda x: x["relevance"], reverse=True)
    
    return jsonify({
        "results": results[:5],
        "count": len(results)
    })

# ----------------- Admissions Inquiry Routes -----------------

@app.route("/api/admissions/inquiry", methods=["POST"])
def send_admissions_inquiry():
    """Send an inquiry to admissions from a prospective parent/student"""
    h = _auth_headers()
    if not h:
        return jsonify({"error": "Not authenticated"}), 401
    
    data = request.get_json() or {}
    
    inquirer_name = data.get("inquirer_name", "Prospective Parent/Student")
    inquirer_email = data.get("inquirer_email", "")
    inquiry_topic = data.get("inquiry_topic", "General Inquiry")
    inquiry_details = data.get("inquiry_details", "")
    phone_number = data.get("phone_number", "Not provided")
    
    if not inquirer_email:
        return jsonify({
            "success": False,
            "error": "Inquirer email is required to send the inquiry"
        }), 400
    
    # Get the admissions email from environment or use default
    admissions_email = os.getenv("ADMISSIONS_EMAIL", "admissions@cheltenham.org")
    
    # Create professional email to admissions team
    email_body = f"""<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <h2 style="color: #003087;">Cheltenham College Enquiry</h2>
    
    <p>Dear Admissions Team,</p>
    
    <p>I am writing to enquire about {inquiry_topic.lower()}.</p>
    
    <div style="background-color: #f9f9f9; padding: 15px; border-left: 4px solid #003087; margin: 20px 0;">
        {inquiry_details}
    </div>
    
    <p>My contact details are:</p>
    <ul style="list-style: none; padding-left: 0;">
        <li><strong>Name:</strong> {inquirer_name}</li>
        <li><strong>Email:</strong> {inquirer_email}</li>
        <li><strong>Phone:</strong> {phone_number}</li>
    </ul>
    
    <p>I look forward to hearing from you.</p>
    
    <p>Kind regards,<br>{inquirer_name}</p>
    
    <hr style="border: none; border-top: 1px solid #ddd; margin: 30px 0;">
    
    <p style="font-size: 11px; color: #666;">
        <em>This enquiry was facilitated by Emily, the Cheltenham College virtual assistant.</em>
    </p>
</body>
</html>"""
    
    # Send email to admissions AND CC the inquirer
    message_data = {
        "subject": f"Enquiry: {inquiry_topic}",
        "body": {
            "contentType": "HTML",
            "content": email_body
        },
        "toRecipients": [
            {"emailAddress": {"address": admissions_email}}
        ],
        "ccRecipients": [
            {"emailAddress": {"address": inquirer_email, "name": inquirer_name}}
        ]
    }
    
    payload = {"message": message_data, "saveToSentItems": "true"}
    r = requests.post(
        f"{GRAPH_URL}/me/sendMail",
        headers=h,
        data=json.dumps(payload)
    )
    
    if not r.ok:
        print(f"Failed to send admissions inquiry: {r.status_code} - {r.text}")
        return jsonify({
            "success": False,
            "error": "Failed to send inquiry to admissions"
        }), r.status_code
    
    return jsonify({
        "success": True,
        "message": f"I've sent your enquiry to {admissions_email} and copied you at {inquirer_email}. The admissions team will be in touch soon.",
        "admissions_email": admissions_email,
        "cc_email": inquirer_email
    })

@app.route("/api/admissions/check", methods=["POST"])
def check_admissions_query():
    """Check if query is admissions-related and return admissions email"""
    # This is a simple endpoint that returns admissions contact info
    admissions_email = os.getenv("ADMISSIONS_EMAIL", "admissions@cheltenham.org")
    
    return jsonify({
        "is_admissions_query": True,
        "admissions_email": admissions_email,
        "message": "I can help connect you with our admissions team!"
    })

# ----------------- Voice Assistant (OpenAI Realtime) -----------------

@app.route("/realtime/session", methods=["POST"])
def create_realtime_session():
    """Create OpenAI Realtime API session for voice"""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return jsonify({"error": "OPENAI_API_KEY not set"}), 500

    body = request.get_json() or {}
    
    user = get_user_info()
    user_name = user.get("displayName", "User") if user else "User"
    
    model = body.get("model", "gpt-4o-realtime-preview-2024-12-17")
    voice = body.get("voice", "shimmer")

    instructions = f"""You are Emily, the administrative assistant for Cheltenham College.
You're helping {user_name} with administrative tasks.
Be warm, professional, and helpful. Use British spelling and expressions.

IMPORTANT - Email Handling:
- You can CREATE DRAFTS or SEND emails based on what the user asks
- Listen carefully to their words:
  * "draft an email" / "create a draft" → create draft only (send=false)
  * "send an email" / "email them" → send immediately (send=true)
- When creating a DRAFT, tell user: "I've created a draft in your Outlook Drafts folder for you to review"
- When SENDING, confirm: "I've sent that email to [recipient]"
- If unsure whether they want to send or draft, ask: "Would you like me to send this or save it as a draft?"

CRITICAL - Admissions & Enquiry Handling:
- ONLY offer to email admissions if user explicitly says: "contact admissions", "email admissions", "put me in touch", or "I want to enquire"
- DO NOT trigger on casual mentions of: "prospectus", "fees", "tours" - instead provide information or direct to website
- If they want to enquire, say: "I can help you get in touch with our admissions team. May I have your email address so I can copy you on the message?"
- ALWAYS CC the inquirer on any email to admissions
- For general questions, provide helpful information and say: "For personalised information, you can visit cheltenham.org/admissions or I can connect you with our team."

Keep responses concise and conversational."""

    try:
        response = requests.post(
            "https://api.openai.com/v1/realtime/sessions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": model,
                "voice": voice,
                "instructions": instructions,
                "input_audio_format": "pcm16",
                "output_audio_format": "pcm16",
                "input_audio_transcription": {"model": "whisper-1"},
                "turn_detection": {
                    "type": "server_vad",
                    "threshold": 0.5,
                    "prefix_padding_ms": 300,
                    "silence_duration_ms": 200
                },
                "tools": [
                    {
                        "type": "function",
                        "name": "create_mail_draft",
                        "description": "Create a draft email in Outlook or send an email immediately. Use send=true to send, send=false to create draft.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "to": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "Recipient email addresses"
                                },
                                "subject": {"type": "string", "description": "Email subject line"},
                                "body": {"type": "string", "description": "HTML body of the email"},
                                "send": {
                                    "type": "boolean",
                                    "description": "If true, send immediately. If false, save as draft. Listen to user's words: 'send' means true, 'draft' means false."
                                }
                            },
                            "required": ["subject", "body", "send"]
                        }
                    },
                    {
                        "type": "function",
                        "name": "search_knowledge",
                        "description": "Search Cheltenham College knowledge base",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "query": {"type": "string"}
                            },
                            "required": ["query"]
                        }
                    },
                    {
                        "type": "function",
                        "name": "get_inbox_summary",
                        "description": "Get inbox summary",
                        "parameters": {"type": "object", "properties": {}}
                    },
                    {
                        "type": "function",
                        "name": "create_contact",
                        "description": "Create a contact",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "firstName": {"type": "string"},
                                "lastName": {"type": "string"},
                                "email": {"type": "string"}
                            },
                            "required": ["firstName", "email"]
                        }
                    },
                    {
                        "type": "function",
                        "name": "offer_admissions_contact",
                        "description": "ONLY use when user explicitly says they want to 'contact admissions', 'enquire', 'get in touch', or 'speak to someone'. Do NOT use for casual mentions of fees/tours/prospectus.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "inquiry_topic": {
                                    "type": "string",
                                    "description": "What they want to enquire about"
                                }
                            },
                            "required": ["inquiry_topic"]
                        }
                    },
                    {
                        "type": "function",
                        "name": "send_admissions_inquiry",
                        "description": "Send enquiry to admissions. MUST include inquirer_email to CC them on the message. Only use after user confirms they want to enquire.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "inquirer_name": {"type": "string"},
                                "inquirer_email": {
                                    "type": "string",
                                    "description": "REQUIRED - user's email to CC them on the message"
                                }, 
                                "inquiry_topic": {"type": "string"},
                                "inquiry_details": {"type": "string"},
                                "phone_number": {"type": "string"}
                            },
                            "required": ["inquirer_name", "inquirer_email", "inquiry_topic", "inquiry_details"]
                        }
                    }
                ]
            },
            timeout=30
        )
        
        if response.ok:
            session_data = response.json()
            return jsonify({
                "token": session_data.get("client_secret", {}).get("value"),
                "session": session_data,
                "model": model,
                "voice": voice
            })
        else:
            print(f"OpenAI API error: {response.status_code} - {response.text}")
            return jsonify({"error": "Failed to create session"}), 500
            
    except Exception as e:
        print(f"Realtime session error: {e}")
        return jsonify({"error": str(e)}), 500

# ----------------- Main -----------------

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_ENV") == "development"
    
    print(f"🚀 Emily Admin for Cheltenham College starting on port {port}")
    print(f"🔗 OAuth callback URL: {REDIRECT_URI}")
    
    # Use provided certificates or create new ones
    cert_file = "cert.pem"
    key_file = "key.pem"
    
    if not (Path(cert_file).exists() and Path(key_file).exists()):
        cert_file, key_file = create_self_signed_cert()
    
    if cert_file and key_file:
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ssl_context.load_cert_chain(cert_file, key_file)
        
        print(f"🔒 Running with HTTPS on https://localhost:{port}")
        print("⚠️ Browser will warn about certificate - click 'Advanced' > 'Proceed'")
        
        app.run(
            host="localhost",
            port=port,
            debug=debug,
            ssl_context=ssl_context
        )
    else:
        print("⚠️ Running HTTP only - voice features may not work")
        app.run(host="localhost", port=port, debug=debug)
