import sqlite3
import hashlib
import hmac
import secrets
import os
import streamlit as st
from datetime import datetime, timedelta
import base64

USERS_DB = "users.db"
PASSWORD_ITERATIONS = 200_000
SESSION_TTL_DAYS = 30

def get_secret(key):
    try:
        return st.secrets.get(key)
    except FileNotFoundError:
        return None

def _db_conn():
    return sqlite3.connect(USERS_DB)

@st.cache_resource
def get_runtime_sessions():
    # token -> user_id (in-memory, resets on server reboot)
    return {}

def init_auth_db():
    with _db_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                login TEXT NOT NULL UNIQUE,
                email TEXT NOT NULL UNIQUE,
                phone TEXT NOT NULL,
                password_salt TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user',
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                expires_at TEXT NOT NULL,
                created_at TEXT NOT NULL,
                last_seen_at TEXT NOT NULL,
                ua_hash TEXT
            )
        """)
        conn.commit()

def _hash_password(password, salt_hex):
    salt = bytes.fromhex(salt_hex)
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PASSWORD_ITERATIONS).hex()

def _make_password(password):
    salt_hex = os.urandom(16).hex()
    return salt_hex, _hash_password(password, salt_hex)

def _verify_password(password, salt_hex, expected_hash):
    candidate = _hash_password(password, salt_hex)
    return hmac.compare_digest(candidate, expected_hash)

def _hash_user_agent(user_agent):
    if not user_agent:
        return None
    return hashlib.sha256(user_agent.encode("utf-8")).hexdigest()

def _get_session_secret():
    secret = get_secret("SESSION_SECRET") or os.getenv("SESSION_SECRET")
    if not secret:
        secret = get_secret("ADMIN_PASSWORD") or os.getenv("ADMIN_PASSWORD")
    if not secret:
        secret = "resto-analytics-dev"
    return secret.encode("utf-8")

def _encode_b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")

def _decode_b64(data: str) -> bytes:
    pad = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + pad)

def _sign_payload(payload: str) -> str:
    sig = hmac.new(_get_session_secret(), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{_encode_b64(payload.encode('utf-8'))}.{sig}"

def _unsign_token(token: str):
    try:
        b64_payload, sig = token.split(".", 1)
        payload = _decode_b64(b64_payload).decode("utf-8")
        expected = hmac.new(_get_session_secret(), payload.encode("utf-8"), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, sig):
            return None
        user_id_str, exp_str = payload.split(":", 1)
        exp_ts = int(exp_str)
        if int(datetime.utcnow().timestamp()) > exp_ts:
            return None
        return int(user_id_str)
    except Exception:
        return None

def create_user(full_name, login, email, phone, password, role="user", status="pending"):
    salt_hex, pw_hash = _make_password(password)
    created_at = datetime.utcnow().isoformat()
    with _db_conn() as conn:
        conn.execute(
            """
            INSERT INTO users (full_name, login, email, phone, password_salt, password_hash, role, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (full_name, login, email, phone, salt_hex, pw_hash, role, status, created_at),
        )
        conn.commit()

def authenticate_user(login, password):
    with _db_conn() as conn:
        row = conn.execute(
            """
            SELECT id, full_name, login, email, phone, password_salt, password_hash, role, status
            FROM users
            WHERE login = ?
            """,
            (login.strip(),),
        ).fetchone()
    if not row:
        return None, "Неверный логин или пароль."

    user = {
        "id": row[0], "full_name": row[1], "login": row[2], "email": row[3], "phone": row[4],
        "password_salt": row[5], "password_hash": row[6], "role": row[7], "status": row[8]
    }
    if not _verify_password(password, user["password_salt"], user["password_hash"]):
        return None, "Неверный логин или пароль."
    if user["status"] != "approved":
        return None, "Ваш аккаунт пока не одобрен администратором."
    return user, None

def get_pending_users():
    with _db_conn() as conn:
        rows = conn.execute(
            """
            SELECT id, full_name, login, email, phone, created_at
            FROM users
            WHERE status = 'pending'
            ORDER BY created_at ASC
            """
        ).fetchall()
    return rows

def get_all_users():
    with _db_conn() as conn:
        rows = conn.execute(
            """
            SELECT id, full_name, login, email, phone, role, status, created_at
            FROM users
            ORDER BY created_at DESC
            """
        ).fetchall()
    return rows

def get_user_by_id(user_id):
    with _db_conn() as conn:
        row = conn.execute(
            """
            SELECT id, full_name, login, email, phone, role, status
            FROM users
            WHERE id = ?
            """,
            (user_id,),
        ).fetchone()
    return row

def create_runtime_session(user_id, user_agent=None):
    now_iso = datetime.utcnow().isoformat()
    expires_at = datetime.utcnow() + timedelta(days=SESSION_TTL_DAYS)
    expires_iso = expires_at.isoformat()
    exp_ts = int(expires_at.timestamp())
    token = _sign_payload(f"{user_id}:{exp_ts}")
    ua_hash = _hash_user_agent(user_agent)
    with _db_conn() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO sessions (token, user_id, expires_at, created_at, last_seen_at, ua_hash)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (token, user_id, expires_iso, now_iso, now_iso, ua_hash),
        )
        conn.commit()

    # Keep in-memory mirror for quick access inside same process.
    sessions = get_runtime_sessions()
    sessions[token] = {"user_id": user_id, "expires_at": expires_iso, "ua_hash": ua_hash}
    return token

def resolve_runtime_session(token, user_agent=None):
    now = datetime.utcnow()
    with _db_conn() as conn:
        row = conn.execute(
            """
            SELECT user_id, expires_at, ua_hash
            FROM sessions
            WHERE token = ?
            """,
            (token,),
        ).fetchone()

        if not row:
            # Try stateless token if DB session not found (survives server restarts)
            user_id = _unsign_token(token)
            if user_id is None:
                return None
            expires_iso = (datetime.utcnow() + timedelta(days=SESSION_TTL_DAYS)).isoformat()
            ua_hash = _hash_user_agent(user_agent)
            conn.execute(
                """
                INSERT OR REPLACE INTO sessions (token, user_id, expires_at, created_at, last_seen_at, ua_hash)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (token, user_id, expires_iso, now.isoformat(), now.isoformat(), ua_hash),
            )
            conn.commit()
            return user_id

        user_id, expires_raw, expected_ua_hash = row
        try:
            expires_at = datetime.fromisoformat(expires_raw)
        except ValueError:
            conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
            conn.commit()
            return None

        if now > expires_at:
            conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
            conn.commit()
            return None

        conn.execute(
            "UPDATE sessions SET last_seen_at = ? WHERE token = ?",
            (now.isoformat(), token),
        )
        conn.commit()

    # Backward compatibility / in-memory mirror.
    sessions = get_runtime_sessions()
    sessions[token] = {"user_id": user_id, "expires_at": expires_raw, "ua_hash": _hash_user_agent(user_agent)}
    return user_id

def drop_runtime_session(token):
    with _db_conn() as conn:
        conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
        conn.commit()

    sessions = get_runtime_sessions()
    sessions.pop(token, None)

def update_user_status(user_id, status):
    with _db_conn() as conn:
        conn.execute("UPDATE users SET status = ? WHERE id = ?", (status, user_id))
        conn.commit()

def update_user_role(user_id, role):
    with _db_conn() as conn:
        conn.execute("UPDATE users SET role = ? WHERE id = ?", (role, user_id))
        conn.commit()

def bootstrap_admin():
    admin_login = get_secret("ADMIN_LOGIN") or os.getenv("ADMIN_LOGIN")
    admin_password = get_secret("ADMIN_PASSWORD") or os.getenv("ADMIN_PASSWORD")
    if not admin_login or not admin_password:
        return

    with _db_conn() as conn:
        existing = conn.execute("SELECT id FROM users WHERE login = ?", (admin_login,)).fetchone()
    if existing:
        return

    admin_name = get_secret("ADMIN_NAME") or os.getenv("ADMIN_NAME") or "Администратор"
    admin_email = get_secret("ADMIN_EMAIL") or os.getenv("ADMIN_EMAIL") or f"{admin_login}@local"
    admin_phone = get_secret("ADMIN_PHONE") or os.getenv("ADMIN_PHONE") or "+70000000000"
    try:
        create_user(admin_name, admin_login, admin_email, admin_phone, admin_password, role="admin", status="approved")
    except sqlite3.IntegrityError:
        pass # Already exists
