import logging
import os
import re
import sqlite3
import time
import requests
import uuid
from urllib.parse import urljoin

logger = logging.getLogger("simplifiapi")

SIMPLIFI_ENDPOINT = "https://services.quicken.com"


def _token_cache_path():
    path = os.environ.get("SIMPLIFI_TOKEN_FILE")
    if path:
        return os.path.expanduser(path)
    # Project root (parent of simplifiapi package dir), so token lives next to README
    pkg_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(os.path.dirname(pkg_dir), "token")


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

# Apple epoch (2001-01-01) for chat.db date comparison
_APPLE_EPOCH_SEC = 978307200


def _get_verification_code_from_imessage(wait_seconds=0):
    """
    Read a recent 2FA-style code from macOS iMessage (chat.db).
    Looks at incoming messages from the last 5 minutes for 4–8 digit codes.
    If wait_seconds > 0, polls for up to that many seconds for a new message.
    Returns the code string or None.
    """
    db_path = os.path.expanduser("~/Library/Messages/chat.db")
    if not os.path.exists(db_path):
        logger.debug("iMessage chat.db not found at %s", db_path)
        return None

    # Quicken SMS format: "Your Quicken verification code is 471367"
    quicken_pattern = re.compile(
        r"verification code is\s+(\d{4,8})", re.IGNORECASE
    )
    # Fallback: any 6-digit or 4–8 digit code
    code_pattern = re.compile(r"\b(\d{6})\b|(\d{4,8})\b")

    def extract_code(text):
        if not text or not isinstance(text, str):
            return None
        # Prefer Quicken format first
        m = quicken_pattern.search(text)
        if m:
            return m.group(1)
        # Then 6-digit, then any 4–8 digit
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
            # message.date: nanoseconds since 2001-01-01 on newer macOS
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
            # Support both nanosecond and second precision
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
    cutoff_apple_sec = now_apple_sec - 300  # 5 minutes

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
        cutoff_apple_sec = now_apple_sec - 120  # last 2 min when polling
        code = fetch_recent_codes(cutoff_apple_sec)
        if code:
            return code

    return None


class Client():

    def __init__(self):
        self.session = requests.Session()

    def get_token(self, email, password):
        # Step 1: Oauth authorize
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
        r = self.session.post(
            url="https://services.quicken.com/oauth/authorize", json=body)
        data = r.json()
        status = data.get("status")
        if (status == "MFA code sent"):
            mfaChannel = data.get("mfaChannel")
            logger.warning("MFA Channel: {}".format(mfaChannel))
            mfaCode = _get_verification_code_from_imessage(wait_seconds=90)
            if not mfaCode:
                mfaCode = input("MFA Code (or paste from iMessage): ")
            else:
                logger.warning("Using verification code from iMessage.")
            body["mfaChannel"] = mfaChannel
            body["mfaCode"] = mfaCode
            r = requests.post(
                url="https://services.quicken.com/oauth/authorize", json=body)
            r.raise_for_status()
            data = r.json()
            status = data.get("status")
            if (status != "User passed MFA"):
                logger.error("Login failed.")
                logger.error(r.json())
                return
        code = r.json().get("code")

        # Step 2: Get token
        r = self.session.post(url="https://services.quicken.com/oauth/token",
                              json={
                                  "clientId": "acme_web",
                                  "clientSecret": "BCDCxXwdWYcj@bK6",
                                  "grantType": "authorization_code",
                                  "code": code,
                                  "redirectUri": "https://app.simplifimoney.com/login"
                              })
        r.raise_for_status()
        token = r.json().get("accessToken")

        logger.warn("Retrieved token {}".format(token))
        save_cached_token(token)

        return token

    def verify_token(self, token) -> bool:
        headers = {"Authorization": "Bearer {}".format(token)}

        r = self.session.get(url="https://services.quicken.com/userprofiles/me",
                             headers=headers)
        if (r.status_code != 200):
            logger.error("Error code: {}".format(r.status_code))
            logger.error(r.json())
            return False
        data = r.json()
        userId = data.get("id")
        logger.warn("User {} logged in.".format(userId))

        # Update session
        self.session.headers.update(headers)

        return True

    def _unpaginate(self, path: str, **kargs):
        nextLink = path
        data = []
        while nextLink:
            logger.warn("Fetching {}".format(nextLink))
            r = self.session.get(url=urljoin(
                SIMPLIFI_ENDPOINT, nextLink), **kargs)
            r.raise_for_status()
            data.extend(r.json()["resources"])
            nextLink = r.json().get("metaData").get("nextLink")
        return data

    def get_datasets(self, limit: int = 1000):
        return self._unpaginate(path="/datasets",
                                params={
                                    "limit": limit,
                                })

    def get_accounts(self, datasetId: str):
        return self._unpaginate(path="/accounts",
                                headers={
                                     "Qcs-Dataset-Id": datasetId,
                                },
                                params={
                                    "limit": 1000,
                                })

    def get_transactions(self, datasetId: str):
        return self._unpaginate(path="/transactions",
                                headers={
                                     "Qcs-Dataset-Id": datasetId,
                                },
                                params={
                                    "limit": 1000,
                                })

    def get_tags(self, datasetId: str):
        return self._unpaginate(path="/tags",
                                headers={
                                     "Qcs-Dataset-Id": datasetId,
                                },
                                params={
                                    "limit": 1000,
                                })

    def get_categories(self, datasetId: str):
        return self._unpaginate(path="/categories",
                                headers={
                                     "Qcs-Dataset-Id": datasetId,
                                },
                                params={
                                    "limit": 1000,
                                })
