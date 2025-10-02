# emily_admin_app.py - Emily Admin (Microsoft 365 Helper) - FIXED VERSION
# Combines working features from both apps

import os
import ssl
import time
import json
import requests
import re
import pickle
import uuid
import numpy as np
import subprocess
from pathlib import Path
from datetime import datetime, timedelta, timezone
from urllib.parse import quote
from typing import Optional, Dict, Any, List, Tuple

from flask import Flask, redirect, request, session, jsonify, render_template, make_response, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
from openai import OpenAI
from bs4 import BeautifulSoup
import psycopg
from psycopg_pool import ConnectionPool

# Load environment variables
ENV_PATH = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(dotenv_path=ENV_PATH)

# Initialize OpenAI client
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Database connection for Cheltenham College inquiries
DATABASE_URL = os.getenv("DATABASE_URL")
db_pool = None

if DATABASE_URL:
    try:
        db_pool = ConnectionPool(
            DATABASE_URL, 
            min_size=2, 
            max_size=20,
            timeout=60.0
        )
        print("✅ Database connection pool created for Cheltenham inquiries")
    except Exception as e:
        print(f"⚠️ Database connection failed: {e}")
        db_pool = None
else:
    print("⚠️ DATABASE_URL not set - family context features disabled")

# Microsoft app settings
CLIENT_ID = os.getenv("MS_CLIENT_ID")
CLIENT_SECRET = os.getenv("MS_CLIENT_SECRET")
REDIRECT_URI = os.getenv("MS_REDIRECT_URI", "https://emily-cheltenham.onrender.com/auth/callback")
TENANT = os.getenv("MS_TENANT", "common")
FLASK_SECRET = os.getenv("FLASK_SECRET", "dev-only-change-me-in-production")

if not CLIENT_ID or not CLIENT_SECRET:
    raise RuntimeError("Set MS_CLIENT_ID and MS_CLIENT_SECRET in .env")

# Microsoft OAuth endpoints
AUTH_URL = f"https://login.microsoftonline.com/{TENANT}/oauth2/v2.0/authorize"
TOKEN_URL = f"https://login.microsoftonline.com/{TENANT}/oauth2/v2.0/token"
GRAPH_URL = "https://graph.microsoft.com/v1.0"

# Cheltenham College admissions email
ADMISSIONS_EMAIL = "bob.ottley@bsmart-ai.com"  # Change to actual email

# FIXED: Correct scope string format (no https://graph.microsoft.com/ prefix for standard scopes)
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
    "MailboxSettings.Read"
]
# Build the proper scope string
SCOPE_STR = " ".join(SCOPES)

# Initialize Flask app
app = Flask(__name__, static_folder='static', static_url_path='/static')
app.secret_key = FLASK_SECRET

# Configure session
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'None'
app.config['SESSION_COOKIE_NAME'] = 'emily_session'

CORS(app, supports_credentials=True)

# Load school knowledge base embeddings (if available)
EMBEDDINGS_PATH = os.path.join(os.path.dirname(__file__), "kb_chunks", "doc_embeddings.pkl")
METADATA_PATH = os.path.join(os.path.dirname(__file__), "kb_chunks", "metadata.pkl")
try:
    with open(EMBEDDINGS_PATH, 'rb') as f:
        DOC_EMBEDDINGS = pickle.load(f)
    with open(METADATA_PATH, 'rb') as f:
        METADATA = pickle.load(f)
    print(f"✅ Loaded {len(DOC_EMBEDDINGS)} knowledge base embeddings")
except Exception as e:
    print(f"⚠️ Could not load embeddings: {e}")
    DOC_EMBEDDINGS = np.array([])
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
            '-subj', '/C=GB/ST=England/L=London/O=EmilyAdmin/CN=localhost'
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

# ----------------- Helper Functions -----------------

def _now(): 
    return int(time.time())

def _save_tokens(tok: dict):
    session["access_token"] = tok.get("access_token")
    session["refresh_token"] = tok.get("refresh_token")
    session["expires_at"] = _now() + int(tok.get("expires_in", 3599))

def _need_refresh() -> bool:
    return not session.get("access_token") or (_now() >= int(session.get("expires_at", 0)) - 60)

def _refresh_tokens_if_needed():
    """Refresh tokens if needed with better error handling"""
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
            # Clear invalid tokens
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
    """Get user info with better error handling"""
    try:
        r = requests.get(f"{GRAPH_URL}/me", headers=headers, timeout=10)
        
        if r.ok:
            user_data = r.json()
            print(f"Graph API /me response: {user_data}")
            return user_data
        else:
            print(f"Graph API /me error: {r.status_code} - {r.text}")
            return {"error": r.text}
            
    except requests.exceptions.RequestException as e:
        print(f"Request exception in _me: {e}")
        return {"error": str(e)}
    except Exception as e:
        print(f"Unexpected error in _me: {e}")
        return {"error": str(e)}

def get_user_info():
    """Get current user information"""
    headers = _auth_headers()
    if not headers:
        return None
    return _me(headers)

def _extract_plaintext_from_graph_msg(msg: dict) -> str:
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

def fetch_family_context(family_id: str) -> Optional[Dict[str, Any]]:
    """Fetch family context from Cheltenham College inquiries database"""
    if not db_pool:
        return None
    
    sql = """
    SELECT
      id AS family_id,
      first_name,
      family_surname,
      parent_name,
      parent_email,
      age_group,
      entry_year,
      country,
      language,
      form_data
    FROM public.inquiries
    WHERE id = %s AND school = 'cheltenham'
    LIMIT 1;
    """
    
    try:
        with db_pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (family_id,))
                row = cur.fetchone()
                if not row:
                    return None
                
                cols = [d.name for d in cur.description]
                data = dict(zip(cols, row))
                
                first_name = (data.get('first_name') or '').strip()
                family_surname_full = (data.get('family_surname') or '').strip()
                surname_only = family_surname_full.replace('the ', '').replace('The ', '').replace(' Family', '').replace(' family', '').strip()
                child_name = f"{first_name} {surname_only}".strip() if first_name and surname_only else first_name or surname_only or None
                
                # CRITICAL: Extract ALL inquiry form data from form_data JSONB
                form_data = data.get("form_data", {}) or {}
                
                return {
                    "family_id": data.get("family_id"),
                    "child_name": child_name,
                    "first_name": first_name,
                    "family_surname": family_surname_full,
                    "surname_only": surname_only,
                    "age_group": data.get("age_group"),
                    "entry_year": data.get("entry_year"),
                    "parent_name": data.get("parent_name"),
                    "parent_email": data.get("parent_email"),
                    "country": data.get("country"),
                    "language": data.get("language", "en"),
                    # Extract inquiry form fields from form_data JSONB
                    "stage": form_data.get("stage", ""),
                    "gender": form_data.get("gender", ""),
                    "boarding_preference": form_data.get("boardingPreference", ""),
                    "academic_interests": form_data.get("academicInterests", []),
                    "activities": form_data.get("activities", []),
                    "specific_sports": form_data.get("specificSports", []),
                    "university_aspirations": form_data.get("universityAspirations", ""),
                    "priorities": form_data.get("priorities", {}),
                    "additional_info": form_data.get("additionalInfo", "")
                }
    except Exception as e:
        print(f"DB fetch error: {e}")
        return None

# ----------------- Routes -----------------

@app.route("/")
def home():
    """API status endpoint"""
    return jsonify({
        "status": "online",
        "service": "Emily Voice Assistant",
        "version": "1.0"
    })

@app.route("/api/status")
def api_status():
    """Check authentication status - FIXED version"""
    if "access_token" not in session:
        return jsonify({"authenticated": False})
    
    # Refresh tokens if needed
    _refresh_tokens_if_needed()
    
    # Check again after refresh
    if "access_token" not in session:
        return jsonify({"authenticated": False})
    
    # Get headers
    h = _auth_headers()
    if not h:
        return jsonify({"authenticated": False})
    
    # Get user info from Microsoft Graph
    try:
        r = requests.get(f"{GRAPH_URL}/me", headers=h, timeout=10)
        
        if r.ok:
            me = r.json()
            print(f"Graph API /me response: {me}")
            
            # Extract user details with multiple fallbacks
            display_name = (
                me.get("displayName") or 
                me.get("givenName") or 
                me.get("preferredName") or
                ""
            )
            
            # Try to get email from multiple fields
            email = (
                me.get("mail") or 
                me.get("userPrincipalName") or 
                me.get("otherMails", [None])[0] if me.get("otherMails") else None or
                ""
            )
            
            user_id = me.get("id") or ""
            
            # If no display name but we have an email, create one from email
            if not display_name and email:
                email_name = email.split('@')[0]
                display_name = ' '.join(
                    word.capitalize() 
                    for word in email_name.replace('.', ' ').replace('_', ' ').replace('-', ' ').split()
                )
            
            # If we have givenName and surname, combine them
            if not display_name and (me.get("givenName") or me.get("surname")):
                parts = []
                if me.get("givenName"):
                    parts.append(me.get("givenName"))
                if me.get("surname"):
                    parts.append(me.get("surname"))
                display_name = " ".join(parts)
            
            # Final fallback
            if not display_name:
                display_name = "User"
            
            return jsonify({
                "authenticated": True,
                "user": {
                    "name": display_name,
                    "email": email,
                    "id": user_id
                }
            })
            
        else:
            print(f"Graph API error: {r.status_code} - {r.text}")
            
            if r.status_code == 401:
                session.clear()
                return jsonify({"authenticated": False})
            
            return jsonify({
                "authenticated": True,
                "user": {
                    "name": "User",
                    "email": "",
                    "id": ""
                }
            })
            
    except Exception as e:
        print(f"Error getting user info: {e}")
        return jsonify({
            "authenticated": True,
            "user": {
                "name": "User", 
                "email": "",
                "id": ""
            }
        })

@app.route("/debug/session")
def debug_session():
    """Debug endpoint to check session and token status"""
    return jsonify({
        "has_access_token": "access_token" in session,
        "has_refresh_token": "refresh_token" in session,
        "expires_at": session.get("expires_at"),
        "current_time": _now(),
        "needs_refresh": _need_refresh(),
        "session_keys": list(session.keys()) if session else []
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
        print(f"OAuth error: {error} - {request.args.get('error_description')}")
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
    """Get inbox messages"""
    h = _auth_headers()
    if not h:
        return jsonify({"error": "Not authenticated"}), 401
    
    top = request.args.get("top", "20")
    url = f"{GRAPH_URL}/me/mailFolders/Inbox/messages?$top={top}&$orderby=receivedDateTime desc"
    
    try:
        r = requests.get(url, headers=h, timeout=10)
        
        if not r.ok:
            print(f"Inbox fetch error: {r.status_code} - {r.text}")
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
                "hasAttachments": msg.get("hasAttachments", False),
                "bullets": [msg.get("subject", "No subject")]
            })
        
        return jsonify({"summaries": summaries, "total": len(summaries)})
        
    except Exception as e:
        print(f"Inbox error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/emails/draft", methods=["POST"])
def create_email_draft():
    """Create a new email draft in Outlook"""
    h = _auth_headers()
    if not h:
        return jsonify({"error": "Not authenticated"}), 401
    
    data = request.get_json() or {}
    
    draft = {
        "subject": data.get("subject", "Draft Email"),
        "body": {
            "contentType": "HTML",
            "content": data.get("body", data.get("html", "<p>Draft email content</p>"))
        },
        "toRecipients": [
            {"emailAddress": {"address": email}} 
            for email in (data.get("to", []) if isinstance(data.get("to"), list) else [data.get("to")] if data.get("to") else [])
        ],
        "isDraft": True
    }
    
    r = requests.post(f"{GRAPH_URL}/me/messages", headers=h, data=json.dumps(draft))
    
    if not r.ok:
        print(f"Failed to create draft: {r.status_code} - {r.text}")
        return jsonify({"error": "Failed to create draft"}), r.status_code
    
    created_draft = r.json()
    
    return jsonify({
        "success": True,
        "draftId": created_draft.get("id"),
        "subject": created_draft.get("subject"),
        "message": "Draft created successfully in Outlook"
    })

@app.route("/api/emails/<message_id>/draft", methods=["POST"])
def create_reply_draft_ai(message_id):
    """Create AI-powered draft reply that preserves email thread"""
    h = _auth_headers()
    if not h:
        return jsonify({"error": "Not authenticated"}), 401
    
    user_info = _me(h)
    user_email = user_info.get("mail") or user_info.get("userPrincipalName")
    user_name = user_info.get("displayName", "User")
    
    r = requests.get(
        f"{GRAPH_URL}/me/messages/{message_id}?$select=*",
        headers=h
    )
    if not r.ok:
        return jsonify({"error": "Could not load message"}), r.status_code
    
    original_msg = r.json()
    
    sender = original_msg.get("from", {}).get("emailAddress", {})
    to_recipients = original_msg.get("toRecipients", [])
    cc_recipients = original_msg.get("ccRecipients", [])
    
    user_is_sender = sender.get("address", "").lower() == user_email.lower()
    
    reply_to_list = []
    reply_cc_list = []
    
    if user_is_sender:
        reply_to_list = [r["emailAddress"]["address"] for r in to_recipients]
        reply_cc_list = [r["emailAddress"]["address"] for r in cc_recipients]
    else:
        reply_to_list = [sender.get("address")]
        for recipient in to_recipients:
            email = recipient["emailAddress"]["address"]
            if email.lower() != user_email.lower() and email not in reply_to_list:
                reply_cc_list.append(email)
        for recipient in cc_recipients:
            email = recipient["emailAddress"]["address"]
            if email.lower() != user_email.lower() and email not in reply_cc_list:
                reply_cc_list.append(email)
    
    subject = original_msg.get("subject", "")
    original_text = _extract_plaintext_from_graph_msg(original_msg)
    
    conversation_id = original_msg.get("conversationId")
    
    email_context = {
        "user_name": user_name,
        "user_email": user_email,
        "user_is_sender": user_is_sender,
        "original_sender": sender.get("name", sender.get("address")),
        "original_sender_email": sender.get("address"),
        "reply_to": reply_to_list,
        "cc_list": reply_cc_list,
        "subject": subject,
        "conversation_id": conversation_id
    }
    
    system_msg = f"""You are Emily, an AI assistant helping {user_name} draft email replies.
    
    IMPORTANT CONTEXT:
    - The user ({user_name}, {user_email}) is asking you to draft a reply FROM THEM
    - You are NOT the recipient of the email
    - You are helping {user_name} write their reply
    - Write the reply as if you are {user_name}, not as Emily
    - Only sign as "{user_name}" or leave unsigned for them to sign
    - Add "(Draft - Please Review)" after the signature
    
    Use British spelling, be professional and warm.
    Format as HTML suitable for Outlook (use <p>, <ul>, <strong> tags)."""
    
    user_msg = f"""
Original email was {'sent by' if user_is_sender else 'from'}: {email_context['original_sender']} ({email_context['original_sender_email']})
Subject: {subject}
This will reply to: {', '.join(reply_to_list)}
CC: {', '.join(reply_cc_list) if reply_cc_list else 'None'}

Original message:
{original_text[:1500]}

Please write a suitable reply FROM {user_name}. 
Remember: You are helping {user_name} draft THEIR reply, not replying as Emily."""

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
    
    r = requests.post(
        f"{GRAPH_URL}/me/messages/{message_id}/createReply",
        headers=h
    )
    if not r.ok:
        return jsonify({"error": "Failed to create reply"}), r.status_code
    
    draft = r.json()
    draft_id = draft.get("id")
    
    patch = {
        "body": {
            "contentType": "HTML",
            "content": body_html
        }
    }
    
    if reply_cc_list:
        patch["ccRecipients"] = [
            {"emailAddress": {"address": email}}
            for email in reply_cc_list
        ]
    
    r2 = requests.patch(
        f"{GRAPH_URL}/me/messages/{draft_id}",
        headers=h,
        data=json.dumps(patch)
    )
    
    if not r2.ok:
        return jsonify({"error": "Failed to update draft"}), r2.status_code
    
    return jsonify({
        "success": True,
        "draftId": draft_id,
        "message": "Reply draft created successfully",
        "threadPreserved": True,
        "replyTo": reply_to_list,
        "cc": reply_cc_list
    })

@app.route("/api/emails/send", methods=["POST"])
def send_email():
    """Send an email immediately (no draft)"""
    h = _auth_headers()
    if not h:
        return jsonify({"error": "Not authenticated"}), 401
    
    data = request.get_json() or {}
    
    # Build the email message
    email = {
        "message": {
            "subject": data.get("subject", "Email from Emily"),
            "body": {
                "contentType": "HTML",
                "content": data.get("body", data.get("html", "<p>Email content</p>"))
            },
            "toRecipients": [
                {"emailAddress": {"address": email}} 
                for email in (data.get("to", []) if isinstance(data.get("to"), list) else [data.get("to")] if data.get("to") else [])
            ]
        },
        "saveToSentItems": True
    }
    
    # Add CC if provided
    if data.get("cc"):
        cc_list = data.get("cc") if isinstance(data.get("cc"), list) else [data.get("cc")]
        email["message"]["ccRecipients"] = [
            {"emailAddress": {"address": cc}} for cc in cc_list
        ]
    
    # Send the email
    r = requests.post(f"{GRAPH_URL}/me/sendMail", headers=h, data=json.dumps(email))
    
    if not r.ok:
        print(f"Failed to send email: {r.status_code} - {r.text}")
        return jsonify({"error": "Failed to send email", "details": r.text}), r.status_code
    
    return jsonify({
        "success": True,
        "message": f"Email sent to {', '.join(data.get('to', []))}"
    })
# ----------------- Calendar/Meeting Routes -----------------

@app.route("/api/calendar/daily-brief", methods=["GET"])
def daily_brief():
    """Get daily agenda"""
    h = _auth_headers()
    if not h:
        return jsonify({"error": "Not authenticated"}), 401
    
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow = today + timedelta(days=1)
    
    filter_str = f"start/dateTime ge '{today.isoformat()}Z' and start/dateTime lt '{tomorrow.isoformat()}Z'"
    url = f"{GRAPH_URL}/me/events?$filter={quote(filter_str)}&$orderby=start/dateTime"
    
    r = requests.get(url, headers=h)
    
    if not r.ok:
        return jsonify({
            "date": today.strftime("%A, %d %B %Y"),
            "eventCount": 0,
            "events": [],
            "summary": "Unable to load calendar."
        })
    
    events = r.json().get("value", [])
    
    return jsonify({
        "date": today.strftime("%A, %d %B %Y"),
        "eventCount": len(events),
        "events": events,
        "summary": f"You have {len(events)} meetings today."
    })

@app.route("/api/meetings/find", methods=["POST"])
def find_meeting_times():
    """Find available meeting times"""
    h = _auth_headers()
    if not h:
        return jsonify({"error": "Not authenticated"}), 401
    
    j = request.get_json(silent=True) or {}
    attendees = j.get("attendees", [])
    duration = int(j.get("durationMinutes", 30))
    start = j.get("timeWindowStart")
    end = j.get("timeWindowEnd")
    
    if not start or not end:
        return jsonify({"error": "timeWindowStart and timeWindowEnd required"}), 400
    
    if not attendees:
        me = _me(h)
        my_mail = me.get("mail") or me.get("userPrincipalName")
        if my_mail:
            attendees = [my_mail]
    
    body = {
        "attendees": [
            {"type": "required", "emailAddress": {"address": a}} for a in attendees
        ],
        "timeConstraint": {
            "timeslots": [{
                "start": {"dateTime": start, "timeZone": "UTC"},
                "end": {"dateTime": end, "timeZone": "UTC"}
            }]
        },
        "meetingDuration": f"PT{duration}M",
        "returnSuggestionReasons": True,
        "minimumAttendeePercentage": 100
    }
    
    r = requests.post(f"{GRAPH_URL}/me/findMeetingTimes", headers=h, data=json.dumps(body))
    
    if r.ok:
        data = r.json()
        suggestions = data.get("meetingTimeSuggestions", [])
        return jsonify({"success": True, "suggestions": suggestions})
    
    return jsonify({"error": "Could not find meeting times"}), r.status_code

@app.route("/api/meetings/create", methods=["POST"])
def create_meeting():
    """Create Teams meeting with invites"""
    h = _auth_headers()
    if not h:
        return jsonify({"error": "Not authenticated"}), 401
    
    j = request.get_json(silent=True) or {}
    
    subject = j.get("subject", "Meeting")
    attendees = j.get("attendees", [])
    start = j.get("start")
    end = j.get("end")
    tz = j.get("timeZone", "Europe/London")
    body_html = j.get("bodyHtml", "<p>Meeting agenda</p>")
    teams = j.get("teams", True)
    
    if not attendees or not start or not end:
        return jsonify({"error": "attendees, start, end required"}), 400
    
    event = {
        "subject": subject,
        "body": {"contentType": "HTML", "content": body_html},
        "start": {"dateTime": start, "timeZone": tz},
        "end": {"dateTime": end, "timeZone": tz},
        "attendees": [
            {"emailAddress": {"address": a}, "type": "required"} for a in attendees
        ]
    }
    
    if teams:
        event["isOnlineMeeting"] = True
        event["onlineMeetingProvider"] = "teamsForBusiness"
    
    r = requests.post(
        f"{GRAPH_URL}/me/events?sendInvitations=true",
        headers=h,
        data=json.dumps(event)
    )
    
    if not r.ok:
        return jsonify({"error": r.text}), r.status_code
    
    created = r.json()
    join_url = (created.get("onlineMeeting") or {}).get("joinUrl")
    
    return jsonify({
        "success": True,
        "eventId": created.get("id"),
        "joinUrl": join_url,
        "subject": created.get("subject")
    })

@app.route("/embed")
def embed():
    """Serve Emily chatbot for iframe embedding in prospectus"""
    return send_from_directory('.', 'index.html')

@app.route("/ask", methods=["POST"])
def ask():
    """Main chatbot endpoint - handles text and voice questions WITH PERSONALIZED WELCOME"""
    data = request.get_json() or {}
    question = data.get("question", "").strip()
    language = data.get("language", "en")
    family_id = data.get("family_id")
    
    # CRITICAL: Handle text-based personalized welcome message
    if question == "__WELCOME__":
        if family_id:
            family_context = fetch_family_context(family_id)
            if family_context:
                child_name = family_context.get('child_name', '').strip()
                family_surname_full = family_context.get('family_surname', '').strip()
                parent_name = family_context.get('parent_name', '').strip()
                
                # Build personalized welcome
                if child_name and family_surname_full:
                    welcome_msg = f"On behalf of Cheltenham College and the admissions team, I'd like to extend a warm welcome to {child_name} and {family_surname_full}. How may I assist you today?"
                elif child_name:
                    welcome_msg = f"On behalf of Cheltenham College and the admissions team, I'd like to extend a warm welcome to {child_name}. How may I assist you today?"
                elif parent_name:
                    welcome_msg = f"On behalf of Cheltenham College and the admissions team, I'd like to extend a warm welcome to {parent_name}. How may I assist you today?"
                else:
                    welcome_msg = "On behalf of Cheltenham College and the admissions team, I'd like to extend you a warm welcome. How may I assist you today?"
                
                return jsonify({
                    "answer": welcome_msg,
                    "queries": ["fees", "admissions", "open days", "contact", "prospectus"],
                    "query_map": {}
                })
        
        # Generic welcome if no family context
        return jsonify({
            "answer": "Hi there! Ask me anything about Cheltenham College.",
            "queries": ["fees", "admissions", "open days", "contact", "prospectus"],
            "query_map": {}
        })
    
    if not question:
        return jsonify({
            "answer": "Please ask a question.",
            "queries": ["fees", "admissions", "contact"],
            "query_map": {}
        })
    
    # Fetch family context from Cheltenham database
    family_context = None
    if family_id:
        family_context = fetch_family_context(family_id)
        print(f"✅ Loaded context for family: {family_id}")
    
    # Build personalized system prompt
    system_msg = f"""You are Emily, the AI assistant for Cheltenham College.
Be warm, helpful, and professional. Use British spelling.
Keep responses concise (2-3 sentences max).
Language: {language}

CRITICAL BEHAVIOR:
- Be proactive - don't just answer, guide the conversation
- After every answer, suggest a related follow-up based on their child's specific interests
- Connect your answers to what you know about their child
- End most responses with "Would you like to know about..." or "I can also tell you about..."
- Make parents feel you understand their child's unique profile
"""
    
    # Add family personalization WITH ALL INQUIRY DATA
    if family_context:
        child_name = family_context.get('child_name', '')
        parent_name = family_context.get('parent_name', '')
        age_group = family_context.get('age_group', '')
        entry_year = family_context.get('entry_year', '')
        
        # Get inquiry form details
        specific_sports = family_context.get('specific_sports', [])
        academic_interests = family_context.get('academic_interests', [])
        activities = family_context.get('activities', [])
        university_aspirations = family_context.get('university_aspirations', '')
        boarding_preference = family_context.get('boarding_preference', '')
        priorities = family_context.get('priorities', {})
        
        system_msg += f"""

FAMILY PROFILE - YOU MUST USE THIS INFORMATION IN EVERY RESPONSE:
Parent: {parent_name}
Child: {child_name}
Age group: {age_group}
Entry year: {entry_year}
Boarding: {boarding_preference}

{child_name}'S SPECIFIC INTERESTS (USE THESE IN YOUR ANSWERS):"""
        
        if specific_sports:
            sports_list = ', '.join(specific_sports)
            system_msg += f"\nSPORTS (in order of preference): {sports_list}"
            system_msg += f"\n  → ALWAYS mention {specific_sports[0]} when discussing sports/facilities"
        
        if academic_interests:
            academics_list = ', '.join(academic_interests)
            system_msg += f"\nACADEMIC INTERESTS: {academics_list}"
            system_msg += f"\n  → Connect any academic answer to these subjects"
        
        if activities:
            activities_list = ', '.join(activities)
            system_msg += f"\nEXTRA-CURRICULAR: {activities_list}"
            system_msg += f"\n  → Mention relevant clubs/societies"
        
        if university_aspirations:
            system_msg += f"\nUNIVERSITY GOAL: {university_aspirations}"
            system_msg += f"\n  → Emphasize Oxbridge preparation and track record"
        
        if priorities:
            system_msg += f"\n\nFAMILY PRIORITIES:"
            if priorities.get('academic', 0) == 3:
                system_msg += f"\n  → Academic excellence is TOP priority"
            if priorities.get('sports', 0) == 3:
                system_msg += f"\n  → Sports development is TOP priority"
            if priorities.get('pastoral', 0) == 3:
                system_msg += f"\n  → Pastoral care is TOP priority"
        
        system_msg += f"""

MANDATORY BEHAVIOR - YOU MUST DO THIS:
1. ALWAYS mention {child_name} by name in your response
2. ALWAYS connect your answer to their specific sports ({specific_sports[0] if specific_sports else 'interests'})
3. ALWAYS reference their {university_aspirations if university_aspirations else 'university goals'}
4. END every response with a personalized follow-up like:
   "Given {child_name}'s interest in {specific_sports[0] if specific_sports else 'X'}, would you like to hear about..."

EXAMPLE OF WHAT YOU MUST DO:
Question: "What are your sports facilities?"
BAD: "We have excellent sports facilities including rugby pitches and golf courses."
GOOD: "Given {child_name}'s passion for {specific_sports[0] if specific_sports else 'Golf'}, you'll love our facilities - we have [specific details about {specific_sports[0] if specific_sports else 'that sport'}]. Since {child_name} also enjoys {specific_sports[1] if len(specific_sports) > 1 else 'Rugby'}, I should mention [details]. With ambitions for {university_aspirations or 'university'}, combining elite sport with academics is key here. Would you like to know how our {specific_sports[0] if specific_sports else 'sports'} programme supports university applications?"

Make EVERY response this personal and specific to {child_name}.
"""
    
    # Search knowledge base (if available)
    context_snippets = []
    if len(DOC_EMBEDDINGS) > 0 and len(METADATA) > 0:
        try:
            query_lower = question.lower()
            for meta in METADATA[:20]:
                text = meta.get("text", "").lower()
                if any(word in text for word in query_lower.split()):
                    context_snippets.append(meta.get("text", "")[:300])
                    if len(context_snippets) >= 3:
                        break
        except Exception as e:
            print(f"Knowledge search error: {e}")
    
    if context_snippets:
        system_msg += f"\n\nRELEVANT INFORMATION:\n" + "\n".join(context_snippets[:2])
    print(f"🔍 FULL SYSTEM PROMPT:")
    print(system_msg)
    print(f"🔍 FAMILY CONTEXT DATA:")
    print(json.dumps(family_context, indent=2))
    # Call OpenAI
    try:
        print(f"🔍 SENDING TO OPENAI - First 1000 chars of prompt:")
        print(system_msg[:1000])
        
        # Define email tool
        tools = [{
            "type": "function",
            "function": {
                "name": "send_enquiry_email",
                "description": "Send enquiry to Cheltenham admissions when user wants to book tour or contact admissions",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "user_name": {"type": "string"},
                        "user_email": {"type": "string"},
                        "user_phone": {"type": "string"},
                        "message": {"type": "string"}
                    },
                    "required": ["user_name", "user_email", "user_phone", "message"]
                }
            }
        }]

        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": question}
            ],
            tools=tools,
            tool_choice="auto",
            temperature=0.7,
            max_tokens=300
        )

        message = response.choices[0].message

        # Handle function call if Emily wants to send email
        if message.tool_calls:
            tool_call = message.tool_calls[0]
            args = json.loads(tool_call.function.arguments)
            
            # Send email via Microsoft Graph
            h = _auth_headers()
            if h:
                email_result = requests.post(
                    f"{GRAPH_URL}/me/sendMail",
                    headers=h,
                    data=json.dumps({
                        "message": {
                            "subject": f"Enquiry from {args['user_name']}",
                            "body": {
                                "contentType": "HTML",
                                "content": f"<p><strong>Name:</strong> {args['user_name']}<br><strong>Email:</strong> {args['user_email']}<br><strong>Phone:</strong> {args['user_phone']}</p><p>{args['message']}</p>"
                            },
                            "toRecipients": [{"emailAddress": {"address": ADMISSIONS_EMAIL}}],
                            "ccRecipients": [{"emailAddress": {"address": args['user_email']}}]
                        },
                        "saveToSentItems": True
                    })
                )
                result = "sent" if email_result.ok else "failed"
            else:
                result = "not authenticated"
            
            # Get Emily's response after sending
            response = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": question},
                    message,
                    {"role": "tool", "tool_call_id": tool_call.id, "content": f"Email {result}"}
                ],
                temperature=0.7,
                max_tokens=300
            )
            answer = response.choices[0].message.content
        else:
            answer = message.content
        
        # Generate context-aware follow-up questions based on inquiry data
        suggested_queries = []
        
        if family_context:
            specific_sports = family_context.get('specific_sports', [])
            academic_interests = family_context.get('academic_interests', [])
            activities = family_context.get('activities', [])
            university_aspirations = family_context.get('university_aspirations', '')
            boarding_preference = family_context.get('boarding_preference', '')
            stage = family_context.get('stage', '')
            
            # Sport-specific questions
            if specific_sports and len(specific_sports) > 0:
                top_sport = specific_sports[0]
                suggested_queries.append(f"Tell me about {top_sport} at Cheltenham")
                if len(specific_sports) > 1:
                    suggested_queries.append(f"What about {specific_sports[1]}?")
            
            # Academic questions based on interests
            if 'sciences' in academic_interests:
                suggested_queries.append("What science facilities do you have?")
            if 'languages' in academic_interests:
                suggested_queries.append("Which languages can my child study?")
            if 'humanities' in academic_interests:
                suggested_queries.append("Tell me about your humanities teaching")
            if 'arts' in academic_interests:
                suggested_queries.append("What creative arts opportunities are there?")
            
            # University-specific questions
            if university_aspirations:
                if 'Oxford' in university_aspirations or 'Cambridge' in university_aspirations:
                    suggested_queries.append("What Oxbridge preparation do you offer?")
                elif 'Russell Group' in university_aspirations:
                    suggested_queries.append("What are your university destinations?")
                elif 'International' in university_aspirations:
                    suggested_queries.append("Do you help with US university applications?")
            
            # Activity-based questions
            if 'music' in activities:
                suggested_queries.append("What music ensembles can students join?")
            if 'leadership' in activities:
                suggested_queries.append("What leadership opportunities exist?")
            if 'ccf' in activities:
                suggested_queries.append("Tell me about the CCF programme")
            if 'drama' in activities:
                suggested_queries.append("What drama productions do you stage?")
            
            # Boarding-specific questions
            if boarding_preference == 'Full Boarding':
                suggested_queries.append("What's boarding life like?")
                suggested_queries.append("What do boarders do at weekends?")
            elif boarding_preference == 'Day':
                suggested_queries.append("What time does the school day run?")
                suggested_queries.append("Can day students join evening activities?")
            elif boarding_preference == 'Considering Both':
                suggested_queries.append("What's the difference between boarding and day?")
            
            # Stage-specific questions
            if stage == 'Upper':
                suggested_queries.append("What A-Level subjects do you offer?")
                suggested_queries.append("How does Sixth Form work?")
            elif stage == 'Lower':
                suggested_queries.append("What's Third Form like?")
                suggested_queries.append("How do you support 13-year-olds?")
        
        # Always include some core questions as fallbacks
        core_queries = ["admissions process", "fees and scholarships", "arrange a visit", "contact admissions"]
        
        # Combine: prioritize personalized questions, then add core ones
        if not suggested_queries:
            suggested_queries = core_queries
        else:
            suggested_queries = suggested_queries[:4]
            remaining_slots = 5 - len(suggested_queries)
            suggested_queries.extend(core_queries[:remaining_slots])
        
        # Ensure we have exactly 5 suggestions
        suggested_queries = list(dict.fromkeys(suggested_queries))[:5]
        
        return jsonify({
            "answer": answer,
            "queries": suggested_queries,
            "query_map": {},
            "family_recognized": bool(family_context)
        })
        
    except Exception as e:
        print(f"OpenAI error: {e}")
        return jsonify({
            "answer": "I apologise, but I'm having trouble right now. Please try again in a moment.",
            "queries": ["fees", "admissions", "contact"]
        })

@app.route("/realtime/tool/get_family_context", methods=["POST"])
def get_family_context_tool():
    """Tool endpoint for voice assistant to get family context"""
    data = request.get_json() or {}
    family_id = data.get("family_id")
    
    if not family_id:
        return jsonify({"error": "No family_id provided"}), 400
    
    family_context = fetch_family_context(family_id)
    
    if not family_context:
        return jsonify({"error": "Family not found"}), 404
    
    return jsonify({
        "ok": True,
        "parent_name": family_context.get("parent_name"),
        "child_name": family_context.get("child_name"),
        "age_group": family_context.get("age_group"),
        "entry_year": family_context.get("entry_year"),
        "language": family_context.get("language", "en")
    })

@app.route("/realtime/tool/get_open_days", methods=["POST"])
def get_open_days_tool():
    """Tool endpoint for open days information"""
    return jsonify({
        "ok": True,
        "events": [
            {
                "date": "2025-03-15",
                "type": "Open Morning",
                "time": "9:00 AM"
            },
            {
                "date": "2025-05-10",
                "type": "Open Day",
                "time": "10:00 AM"
            }
        ]
    })

@app.route("/api/knowledge/search", methods=["POST"])
def search_knowledge():
    """Search the school knowledge base"""
    data = request.get_json() or {}
    query = data.get("query", "")
    
    if not query or len(DOC_EMBEDDINGS) == 0:
        return jsonify({"results": [], "message": "No results found"})
    
    results = []
    query_lower = query.lower()
    
    for i, meta in enumerate(METADATA):
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
    
@app.route("/realtime/session", methods=["POST"])
def create_realtime_session():
    """Create OpenAI Realtime API session for voice WITH EMAIL SENDING"""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return jsonify({"error": "OPENAI_API_KEY not set"}), 500

    body = request.get_json(silent=True) or {}
    
    family_id = body.get("family_id")
    
    # Fetch family context if available
    family_context = None
    if family_id:
        family_context = fetch_family_context(family_id)
        print(f"✅ Voice session for family: {family_id}")
        if family_context:
            print(f"✅ Family context loaded: {json.dumps(family_context, indent=2)}")
    
    user = get_user_info()
    user_name = user.get("displayName", "User") if user else "User"
    
    model = body.get("model", "gpt-4o-realtime-preview-2024-12-17")
    voice = body.get("voice", "shimmer")
    language = body.get("language", "en")

    instructions = f"""You are Emily, the AI assistant for Cheltenham College.
Be warm, helpful, and professional. Use British spelling and expressions.
Keep responses concise and conversational.
Language: {language}

CRITICAL EMAIL INSTRUCTIONS:
- When sending emails about tours, admissions, or enquiries:
  1. ALWAYS send TO: bob.ottley@bsmart-ai.com
  2. ALWAYS ask the user: "What's your email address and best contact number so I can include them in the enquiry?"
  3. Wait for their response before sending
  4. Include their contact details in the email body
  5. CC the user at their email address
  6. After sending, confirm: "I've sent the enquiry to our admissions team and copied you at [their-email]"

- Use the create_mail_draft function to send emails
- Never say "draft" - you are SENDING emails immediately
"""

    # Add family context to instructions if available
    if family_context:
        child_name = family_context.get('child_name', '').strip()
        family_surname_full = family_context.get('family_surname', '').strip()
        parent_name = family_context.get('parent_name', '').strip()
        age_group = family_context.get('age_group', '')
        entry_year = family_context.get('entry_year', '')
        
        specific_sports = family_context.get('specific_sports', [])
        academic_interests = family_context.get('academic_interests', [])
        activities = family_context.get('activities', [])
        university_aspirations = family_context.get('university_aspirations', '')
        boarding_preference = family_context.get('boarding_preference', '')
        priorities = family_context.get('priorities', {})
        additional_info = family_context.get('additional_info', '')
        
        # Build personalized greeting
        if child_name and family_surname_full:
            greeting = f"On behalf of Cheltenham College and the admissions team, I would like to extend a warm welcome to {child_name} and {family_surname_full}. How may I assist you today?"
        elif child_name:
            greeting = f"On behalf of Cheltenham College and the admissions team, I would like to extend a warm welcome to {child_name}. How may I assist you today?"
        elif parent_name:
            greeting = f"On behalf of Cheltenham College and the admissions team, I would like to extend a warm welcome to {parent_name}. How may I assist you today?"
        else:
            greeting = "On behalf of Cheltenham College and the admissions team, I would like to extend you a warm welcome. How may I assist you today?"
        
        instructions += f"""

CRITICAL FAMILY CONTEXT - USE IN EVERY RESPONSE:
Parent: {parent_name}
Child: {child_name}
Age group: {age_group}
Entry year: {entry_year}
Boarding preference: {boarding_preference}

{child_name}'S SPECIFIC INTERESTS (REFERENCE IN ALL ANSWERS):"""
        
        if specific_sports:
            sports_list = ', '.join(specific_sports)
            instructions += f"\nSPORTS: {sports_list}"
            instructions += f"\n  → Always mention {specific_sports[0]} when discussing sports"
        
        if academic_interests:
            academics_list = ', '.join(academic_interests)
            instructions += f"\nACADEMIC INTERESTS: {academics_list}"
        
        if activities:
            activities_list = ', '.join(activities)
            instructions += f"\nEXTRA-CURRICULAR: {activities_list}"
        
        if university_aspirations:
            instructions += f"\nUNIVERSITY GOAL: {university_aspirations}"
        
        if priorities:
            instructions += f"\n\nFAMILY PRIORITIES:"
            if priorities.get('academic', 0) >= 3:
                instructions += f"\n  → Academic excellence is TOP priority"
            if priorities.get('sports', 0) >= 3:
                instructions += f"\n  → Sports development is TOP priority"
            if priorities.get('pastoral', 0) >= 3:
                instructions += f"\n  → Pastoral care is TOP priority"
        
        if additional_info:
            instructions += f"\n\nADDITIONAL CONTEXT: {additional_info}"
        
        instructions += f"""

MANDATORY BEHAVIOR:
1. Always mention {child_name} by name
2. Connect answers to their sports ({specific_sports[0] if specific_sports else 'interests'})
3. Reference their {university_aspirations if university_aspirations else 'university goals'}

FIRST MESSAGE: When responding to "Hello", say: '{greeting}'

Make EVERY response personal to {child_name}.
"""

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
                        "description": "Send an email to Cheltenham College admissions team at admissions@cheltenham.ac.uk. The user's email and contact number should be included in the body and the user should be CC'd.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "to": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "Always use ['admissions@cheltenham.ac.uk']"
                                },
                                "cc": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "User's email address to CC them"
                                },
                                "subject": {
                                    "type": "string",
                                    "description": "Email subject line"
                                },
                                "body": {
                                    "type": "string",
                                    "description": "Email body - MUST include the user's contact number and email address"
                                }
                            },
                            "required": ["to", "subject", "body"]
                        }
                    },
                    {
                        "type": "function",
                        "name": "get_inbox_summary",
                        "description": "Get a summary of recent emails in the inbox",
                        "parameters": {
                            "type": "object",
                            "properties": {}
                        }
                    },
                    {
                        "type": "function",
                        "name": "find_meeting_slots",
                        "description": "Find available meeting slots",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "attendees": {
                                    "type": "array",
                                    "items": {"type": "string"}
                                },
                                "durationMinutes": {"type": "integer"}
                            }
                        }
                    },
                    {
                        "type": "function",
                        "name": "create_teams_meeting",
                        "description": "Create a Teams meeting and send invites",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "subject": {"type": "string"},
                                "attendees": {
                                    "type": "array",
                                    "items": {"type": "string"}
                                },
                                "start": {"type": "string"},
                                "end": {"type": "string"},
                                "bodyHtml": {"type": "string"}
                            },
                            "required": ["subject", "attendees", "start", "end"]
                        }
                    },
                    {
                        "type": "function",
                        "name": "create_contact",
                        "description": "Create a new contact in Outlook address book",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "firstName": {"type": "string"},
                                "lastName": {"type": "string"},
                                "email": {"type": "string"},
                                "phone": {"type": "string"},
                                "company": {"type": "string"},
                                "jobTitle": {"type": "string"}
                            },
                            "required": ["firstName", "email"]
                        }
                    },
                    {
                        "type": "function",
                        "name": "get_family_context",
                        "description": "Get information about a prospective family",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "family_id": {"type": "string"}
                            }
                        }
                    },
                    {
                        "type": "function",
                        "name": "get_open_days",
                        "description": "Get upcoming open days and events",
                        "parameters": {
                            "type": "object",
                            "properties": {}
                        }
                    },
                    {
                        "type": "function",
                        "name": "kb_search",
                        "description": "Search the school knowledge base for information",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "query": {
                                    "type": "string",
                                    "description": "Search query"
                                }
                            },
                            "required": ["query"]
                        }
                    },
                    {
                        "type": "function",
                        "name": "book_tour",
                        "description": "Request to book a school tour",
                        "parameters": {
                            "type": "object",
                            "properties": {}
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

@app.route('/family/<family_id>', methods=['GET'])
def get_family(family_id):
    """Get family context from Cheltenham inquiries database"""
    if not db_pool:
        return jsonify({"ok": False, "error": "Database not configured"}), 503
    
    ctx = fetch_family_context(family_id)
    if not ctx:
        return jsonify({"ok": False, "error": "Family not found in Cheltenham database"}), 404
    
    return jsonify({"ok": True, "family": ctx})

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    
    is_render = os.getenv("RENDER") == "true"
    
    print(f"🚀 Emily for Cheltenham College starting on port {port}")
    print(f"📍 OAuth callback URL: {REDIRECT_URI}")
    print(f"📋 Scopes: {SCOPE_STR}")
    
    if is_render:
        print(f"🌐 Running on Render (production)")
        app.run(
            host="0.0.0.0",
            port=port,
            debug=False
        )
    else:
        debug = os.getenv("FLASK_ENV") == "development"
        cert_file, key_file = create_self_signed_cert()
        
        if cert_file and key_file:
            ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            ssl_context.load_cert_chain(cert_file, key_file)
            
            print(f"🔒 Running locally with HTTPS on https://localhost:{port}")
            print("⚠️ Browser will warn about certificate - click 'Advanced' > 'Proceed to localhost'")
            
            app.run(
                host="localhost",
                port=port,
                debug=debug,
                ssl_context=ssl_context
            )
        else:
            print("⚠️ Failed to create SSL certificate. Voice features will not work.")
            print(f"🔌 Running HTTP only on http://localhost:{port}")
            app.run(
                host="localhost",
                port=port,
                debug=debug
            )
