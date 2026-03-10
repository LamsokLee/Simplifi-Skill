"""
Authentication for Quicken Simplifi: token cache, MFA (iMessage), get_token, verify_token.
"""

import logging
import os
import re
import sqlite3
import time
import uuid

logger = logging.getLogger("simplifiapi")

# Apple epoch (2001-01-01) for chat.db date comparison
_APPLE_EPOCH_SEC = 978307200


def _token_cache_path():
    path = os.environ.get("SIMPLIFI_TOKEN_FILE")
    if path:
        return os.path.expanduser(path)
    # Repo root: simplifiapi/login/auth.py -> parent of simplifiapi = repo root
    this_file = os.path.abspath(__file__)
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(this_file)))
    return os.path.join(repo_root, "token")


def load_cached_token():
    """Load token from cache file if present. Returns None if missing or unreadable."""
    path = _token_cache_path()
    try:
        if os.path.isfile(path):
            with open(path, "r") as f:
                return f.read().strip() or None
    except OSError as e:
        logger.debug("Could not read token cache %s: %s", path, e)
    return None


def save_cached_token(token):
    """Save token to cache file after successful login (e.g. SMS/MFA)."""
    path = _token_cache_path()
    try:
        with open(path, "w") as f:
            f.write(token)
        os.chmod(path, 0o600)
        logger.warn("Cached token to %s", path)
    except OSError as e:
        logger.warning("Could not cache token to %s: %s", path, e)


def _get_verification_code_from_imessage(wait_seconds=0):
    """
    Read a recent 2FA-style code from macOS iMessage (chat.db).
    If wait_seconds > 0, polls for up to that many seconds.
    Returns the code string or None.
    """
    db_path = os.path.expanduser("~/Library/Messages/chat.db")
    if not os.path.exists(db_path):
        logger.debug("iMessage chat.db not found at %s", db_path)
        return None

    quicken_pattern = re.compile(
        r"verification code is\s+(\d{4,8})", re.IGNORECASE
    )
    code_pattern = re.compile(r"\b(\d{6})\b|(\d{4,8})\b")

    def extract_code(text):
        if not text or not isinstance(text, str):
            return None
        m = quicken_pattern.search(text)
        if m:
            return m.group(1)
        for m in code_pattern.finditer(text):
            six, other = m.group(1), m.group(2)
            if six:
                return six
            if other:
                return other
        return None

    def fetch_recent_codes(cutoff_apple_sec):
        try:
            conn = sqlite3.connect(
                "file:{}?mode=ro".format(db_path), uri=True, timeout=5
            )
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute(
                """
                SELECT text, date FROM message
                WHERE is_from_me = 0 AND (text IS NOT NULL AND text != '')
                ORDER BY date DESC
                LIMIT 50
                """
            )
            rows = cur.fetchall()
            conn.close()
        except (sqlite3.Error, OSError) as e:
            logger.debug("Could not read iMessage DB: %s", e)
            return None

        for row in rows:
            text = row["text"]
            date_val = row["date"]
            if date_val is None:
                continue
            try:
                date_ns = int(date_val)
            except (TypeError, ValueError):
                continue
            if date_ns > 1e15:
                date_apple_sec = date_ns / 1e9
            else:
                date_apple_sec = float(date_ns)
            if date_apple_sec < cutoff_apple_sec:
                continue
            code = extract_code(text)
            if code:
                return code
        return None

    now_apple_sec = time.time() - _APPLE_EPOCH_SEC
    cutoff_apple_sec = now_apple_sec - 300
    code = fetch_recent_codes(cutoff_apple_sec)
    if code:
        return code
    if wait_seconds <= 0:
        return None

    logger.warning("Waiting up to %s seconds for 2FA code from iMessage...", wait_seconds)
    deadline = time.time() + wait_seconds
    while time.time() < deadline:
        time.sleep(3)
        now_apple_sec = time.time() - _APPLE_EPOCH_SEC
        cutoff_apple_sec = now_apple_sec - 120
        code = fetch_recent_codes(cutoff_apple_sec)
        if code:
            return code
    return None


def get_token(session, email, password):
    """
    Perform OAuth login (with MFA if required). Uses session for HTTP.
    Returns access token string or None on failure.
    """
    body = {
        "clientId": "acme_web",
        "mfaChannel": None,
        "mfaCode": None,
        "password": password,
        "redirectUri": "https://app.simplifimoney.com/login",
        "responseType": "code",
        "threatMetrixRequestId": None,
        "threatMetrixSessionId": str(uuid.uuid4()),
        "username": email,
    }
    r = session.post(
        url="https://services.quicken.com/oauth/authorize", json=body
    )
    data = r.json()
    status = data.get("status")
    if status == "MFA code sent":
        mfaChannel = data.get("mfaChannel")
        logger.warning("MFA Channel: %s", mfaChannel)
        mfaCode = _get_verification_code_from_imessage(wait_seconds=90)
        if not mfaCode:
            mfaCode = input("MFA Code (or paste from iMessage): ")
        else:
            logger.warning("Using verification code from iMessage.")
        body["mfaChannel"] = mfaChannel
        body["mfaCode"] = mfaCode
        r = session.post(
            url="https://services.quicken.com/oauth/authorize", json=body
        )
        r.raise_for_status()
        data = r.json()
        status = data.get("status")
        if status != "User passed MFA":
            logger.error("Login failed.")
            logger.error(r.json())
            return None
    code = r.json().get("code")
    if not code:
        return None

    r = session.post(
        url="https://services.quicken.com/oauth/token",
        json={
            "clientId": "acme_web",
            "clientSecret": "BCDCxXwdWYcj@bK6",
            "grantType": "authorization_code",
            "code": code,
            "redirectUri": "https://app.simplifimoney.com/login",
        },
    )
    r.raise_for_status()
    token = r.json().get("accessToken")
    logger.warn("Retrieved token %s", token)
    save_cached_token(token)
    return token


def verify_token(session, token) -> bool:
    """Verify token and set session Authorization header. Returns True if valid."""
    headers = {"Authorization": "Bearer {}".format(token)}
    r = session.get(
        url="https://services.quicken.com/userprofiles/me", headers=headers
    )
    if r.status_code != 200:
        logger.error("Error code: %s", r.status_code)
        logger.error(r.json())
        return False
    data = r.json()
    userId = data.get("id")
    logger.warn("User %s logged in.", userId)
    session.headers.update(headers)
    return True
