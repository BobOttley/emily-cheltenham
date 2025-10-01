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
        db_pool = ConnectionPool(DATABASE_URL, min_size=1, max_size=10)
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

# FIXED: Correct scope string format (no https://graph.microsoft.com/ prefix for standard scopes)
SCOPES = [
    "offline_access",
    "openid",
    "profile",
    "email",
    "User.Read",
    "Mail.Read",
    "Mail.ReadWrite",
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
                
                # Build child name from first_name and family_surname
                child_name = f"{data.get('first_name', '')} {data.get('family_surname', '')}".strip()
                
                return {
                    "family_id": data.get("family_id"),
                    "child_name": child_name or None,
                    "first_name": data.get("first_name"),
                    "family_surname": data.get("family_surname"),
                    "age_group": data.get("age_group"),
                    "entry_year": data.get("entry_year"),
                    "parent_name": data.get("parent_name"),
                    "parent_email": data.get("parent_email"),
                    "country": data.get("country"),
                    "language": data.get("language", "en"),
                    "form_data": data.get("form_data", {})
                }
    except Exception as e:
        print(f"DB fetch error: {e}")
        return None

# ----------------- Routes -----------------

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
            print(f"Graph API /me response: {me}")  # Debug logging
            
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
                # john.doe@company.com -> John Doe
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
            
            # If we get a 401, token might be invalid
            if r.status_code == 401:
                session.clear()
                return jsonify({"authenticated": False})
            
            # For other errors, return authenticated with fallback user
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
        # Don't log out on error - might be temporary
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
        "prompt": "select_account"  # Force account selection
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
        
        # Process messages into summaries
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
                "bullets": [msg.get("subject", "No subject")]  # Simplified for now
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
    
    # Build the draft message
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
    
    # Create the draft
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
    
    # Get current user info
    user_info = _me(h)
    user_email = user_info.get("mail") or user_info.get("userPrincipalName")
    user_name = user_info.get("displayName", "User")
    
    # Read original message with full details
    r = requests.get(
        f"{GRAPH_URL}/me/messages/{message_id}?$select=*",
        headers=h
    )
    if not r.ok:
        return jsonify({"error": "Could not load message"}), r.status_code
    
    original_msg = r.json()
    
    # Extract all recipients for proper reply
    sender = original_msg.get("from", {}).get("emailAddress", {})
    to_recipients = original_msg.get("toRecipients", [])
    cc_recipients = original_msg.get("ccRecipients", [])
    
    # Determine if user was the sender or recipient
    user_is_sender = sender.get("address", "").lower() == user_email.lower()
    
    # Build reply recipients list
    reply_to_list = []
    reply_cc_list = []
    
    if user_is_sender:
        # User sent the original - reply to original recipients
        reply_to_list = [r["emailAddress"]["address"] for r in to_recipients]
        reply_cc_list = [r["emailAddress"]["address"] for r in cc_recipients]
    else:
        # User received the email - reply to sender and CC others
        reply_to_list = [sender.get("address")]
        # Add other recipients to CC, excluding the user
        for recipient in to_recipients:
            email = recipient["emailAddress"]["address"]
            if email.lower() != user_email.lower() and email not in reply_to_list:
                reply_cc_list.append(email)
        for recipient in cc_recipients:
            email = recipient["emailAddress"]["address"]
            if email.lower() != user_email.lower() and email not in reply_cc_list:
                reply_cc_list.append(email)
    
    # Extract email content and subject
    subject = original_msg.get("subject", "")
    original_text = _extract_plaintext_from_graph_msg(original_msg)
    
    # Get conversation ID to maintain thread
    conversation_id = original_msg.get("conversationId")
    
    # Prepare context for AI
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
    
    # Generate AI reply with proper context
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
    
    # Create reply draft in Outlook (preserves thread)
    r = requests.post(
        f"{GRAPH_URL}/me/messages/{message_id}/createReply",
        headers=h
    )
    if not r.ok:
        return jsonify({"error": "Failed to create reply"}), r.status_code
    
    draft = r.json()
    draft_id = draft.get("id")
    
    # Update draft with AI content and proper recipients
    patch = {
        "body": {
            "contentType": "HTML",
            "content": body_html
        }
    }
    
    # Only update recipients if we need to add CCs
    # (createReply already sets the To field correctly)
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
    
    # Default to self if no attendees
    if not attendees:
        me = _me(h)
        my_mail = me.get("mail") or me.get("userPrincipalName")
        if my_mail:
            attendees = [my_mail]
    
    # Try findMeetingTimes API
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
    
    # Send invitations
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
    """Main chatbot endpoint - handles text and voice questions"""
    data = request.get_json() or {}
    question = data.get("question", "").strip()
    language = data.get("language", "en")
    family_id = data.get("family_id")
    
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
Language: {language}"""
    
    # Add family personalization
    if family_context:
        child_name = family_context.get('child_name', '')
        parent_name = family_context.get('parent_name', '')
        age_group = family_context.get('age_group', '')
        entry_year = family_context.get('entry_year', '')
        
        system_msg += f"""

IMPORTANT CONTEXT:
You are speaking with {parent_name} about their child {child_name}.
- Age group: {age_group}
- Prospective entry: {entry_year}

Welcome them warmly by name and reference their child when relevant.
Example: "Hello {parent_name}! I'd be delighted to help you learn more about Cheltenham College for {child_name}."
"""
    
    # Search knowledge base (if available)
    context_snippets = []
    if len(DOC_EMBEDDINGS) > 0 and len(METADATA) > 0:
        try:
            # Simple keyword search
            query_lower = question.lower()
            for meta in METADATA[:20]:  # Check first 20 docs
                text = meta.get("text", "").lower()
                if any(word in text for word in query_lower.split()):
                    context_snippets.append(meta.get("text", "")[:300])
                    if len(context_snippets) >= 3:
                        break
        except Exception as e:
            print(f"Knowledge search error: {e}")
    
    if context_snippets:
        system_msg += f"\n\nRELEVANT INFORMATION:\n" + "\n".join(context_snippets[:2])
    
    # Call OpenAI
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": question}
            ],
            temperature=0.7,
            max_tokens=300
        )
        
        answer = response.choices[0].message.content
        
        # Return response with suggested follow-up queries
        return jsonify({
            "answer": answer,
            "queries": ["fees", "admissions", "open", "contact", "prospectus"],
            "query_map": {},
            "family_recognized": bool(family_context)
        })
        
    except Exception as e:
        print(f"OpenAI error: {e}")
        return jsonify({
            "answer": "I apologize, but I'm having trouble right now. Please try again in a moment.",
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
    # You can fetch this from a database or return static data
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
# ----------------- Voice/Realtime Routes -----------------
@app.route("/api/knowledge/search", methods=["POST"])
def search_knowledge():
    """Search the school knowledge base"""
    data = request.get_json() or {}
    query = data.get("query", "")
    
    if not query or len(DOC_EMBEDDINGS) == 0:
        return jsonify({"results": [], "message": "No results found"})
    
    # Simple keyword search in metadata
    results = []
    query_lower = query.lower()
    
    for i, meta in enumerate(METADATA):
        text = meta.get("text", "").lower()
        if query_lower in text:
            results.append({
                "text": meta.get("text", "")[:500],  # First 500 chars
                "relevance": text.count(query_lower)
            })
    
    # Sort by relevance
    results.sort(key=lambda x: x["relevance"], reverse=True)
    
    return jsonify({
        "results": results[:5],  # Top 5 results
        "count": len(results)
    })
    
@app.route("/realtime/session", methods=["POST"])
def create_realtime_session():
    """Create OpenAI Realtime API session for voice"""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return jsonify({"error": "OPENAI_API_KEY not set"}), 500

    body = request.get_json(silent=True) or {}
    
    # Get family_id from request
    family_id = body.get("family_id")
    
    # Fetch family context if available
    family_context = None
    if family_id:
        family_context = fetch_family_context(family_id)
        print(f"✅ Voice session for family: {family_id}")
    
    user = get_user_info()
    user_name = user.get("displayName", "User") if user else "User"
    
    model = body.get("model", "gpt-4o-realtime-preview-2024-12-17")
    voice = body.get("voice", "shimmer")
    language = body.get("language", "en")

    # Build instructions with family context
    instructions = f"""You are Emily, the AI assistant for Cheltenham College.
Be warm, helpful, and professional. Use British spelling and expressions.
Keep responses concise and conversational.
Language: {language}

IMPORTANT: When asked to create or send emails:
- You can create DRAFT emails that the user must review and send manually
- Always say you're creating a "draft" not "sending" the email
- Tell the user to check their Outlook drafts folder
- Never claim to have "sent" an email - you can only create drafts"""

    if family_context:
        child_name = family_context.get('child_name', '')
        parent_name = family_context.get('parent_name', '')
        age_group = family_context.get('age_group', '')
        entry_year = family_context.get('entry_year', '')
        
        instructions += f"""

IMPORTANT CONTEXT:
You are speaking with {parent_name} about their child {child_name}.
- Age group: {age_group}
- Prospective entry: {entry_year}

Welcome them warmly by name and reference their child when relevant.
Example: "Hello {parent_name}! I'd be delighted to help you with {child_name}'s journey to Cheltenham College."
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
                        "description": "Create a draft email in Outlook that the user can review and send",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "to": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "Email addresses of recipients"
                                },
                                "subject": {
                                    "type": "string",
                                    "description": "Email subject line"
                                },
                                "body": {
                                    "type": "string",
                                    "description": "HTML body of the email"
                                },
                                "message_id": {
                                    "type": "string",
                                    "description": "ID of message to reply to (for threaded replies)"
                                }
                            },
                            "required": ["subject", "body"]
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
                        "name": "search_knowledge",
                        "description": "Search the school knowledge base for information",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "query": {
                                    "type": "string",
                                    "description": "Search query for the knowledge base"
                                }
                            },
                            "required": ["query"]
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

# ----------------- Family Context Route -----------------

@app.route('/family/<family_id>', methods=['GET'])
def get_family(family_id):
    """Get family context from Cheltenham inquiries database"""
    if not db_pool:
        return jsonify({"ok": False, "error": "Database not configured"}), 503
    
    ctx = fetch_family_context(family_id)
    if not ctx:
        return jsonify({"ok": False, "error": "Family not found in Cheltenham database"}), 404
    
    return jsonify({"ok": True, "family": ctx})

# ----------------- Main -----------------

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    
    # Check if running on Render (production) or locally (development)
    is_render = os.getenv("RENDER") == "true"
    
    print(f"🚀 Emily for Cheltenham College starting on port {port}")
    print(f"📍 OAuth callback URL: {REDIRECT_URI}")
    print(f"📋 Scopes: {SCOPE_STR}")
    
    if is_render:
        # Production on Render - no SSL, bind to 0.0.0.0
        print(f"🌐 Running on Render (production)")
        app.run(
            host="0.0.0.0",  # Required for Render
            port=port,
            debug=False
        )
    else:
        # Local development - use SSL for voice features
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
