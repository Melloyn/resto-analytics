from infrastructure.repositories.sqlite_user_repository import SQLiteUserRepository
from infrastructure.repositories.sqlite_audit_repository import SQLiteAuditRepository, AuditAction
from infrastructure.storage.yandex_disk_storage import YandexDiskStorage
import hashlib
import hmac
import secrets
import os
import streamlit as st
from datetime import datetime, timedelta
import base64
import logging

log = logging.getLogger(__name__)

class UserAlreadyExistsError(Exception):
    pass

class InvalidCredentialsError(Exception):
    pass

USERS_DB = "users.db"
YANDEX_USERS_PATH = "RestoAnalytic/config/users.db"
PASSWORD_ITERATIONS = 200_000
SESSION_TTL_HOURS = int(os.getenv("SESSION_TTL_HOURS", 12))

def _mask_identifier(identifier: str) -> str:
    if not identifier: return "***"
    if "@" in identifier:
        parts = identifier.split("@")
        name = parts[0]
        return f"{name[:2]}***@{parts[1]}" if len(name) > 2 else f"***@{parts[1]}"
    return f"{identifier[:2]}***" if len(identifier) > 2 else "***"

def get_secret(key):
    try:
        return st.secrets.get(key)
    except FileNotFoundError:
        return None

_user_repo = None
_storage_provider = None
_audit_repo = None

def get_user_repo() -> SQLiteUserRepository:
    global _user_repo
    if _user_repo is None or _user_repo.db_path != USERS_DB:
        _user_repo = SQLiteUserRepository(USERS_DB)
    return _user_repo

def get_audit_repo() -> SQLiteAuditRepository:
    global _audit_repo
    if _audit_repo is None or _audit_repo.db_path != USERS_DB:
        _audit_repo = SQLiteAuditRepository(USERS_DB)
    return _audit_repo

def get_storage_provider() -> YandexDiskStorage:
    global _storage_provider
    if _storage_provider is None:
        _storage_provider = YandexDiskStorage()
    return _storage_provider

def sync_users_from_yandex(token, remote_path=YANDEX_USERS_PATH, force=False):
    return get_storage_provider().download_file(remote_path, USERS_DB, token, force=force)

def sync_users_to_yandex(token, remote_path=YANDEX_USERS_PATH):
    # SAFETY GUARD: Prevent wiping a populated cloud DB with a fresh 1-user local DB.
    try:
        users = get_all_users()
        local_size = os.path.getsize(USERS_DB) if os.path.exists(USERS_DB) else 0
        if len(users) <= 1:
            remote_info = get_storage_provider().get_file_info(remote_path, token)
            if remote_info:
                remote_size = remote_info.get("size", 0)
                # If remote file is larger by more than minor metadata bytes, it likely has more users
                if remote_size > local_size + 1024:
                    log.error(
                        f"🚨 DB SAFETY GUARD ALARM: Aborting upload! "
                        f"Local DB has only {len(users)} user(s) ({local_size} bytes), "
                        f"but Cloud DB is larger ({remote_size} bytes). Prevents wiping data!"
                    )
                    return False
    except Exception as e:
        log.warning(f"⚠️ DB Safety guard check encountered an issue: {e}")

    return get_storage_provider().upload_file(USERS_DB, remote_path, token)

@st.cache_resource
def get_runtime_sessions():
    # token -> user_id (in-memory, resets on server reboot)
    return {}

def init_auth_db():
    get_user_repo().init_auth_db()

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
        # Fallback to admin password in extreme cases
        secret = get_secret("ADMIN_PASSWORD") or os.getenv("ADMIN_PASSWORD")
    if not secret:
        # DO NOT allow empty secrets in production
        st.error("🚨 КРИТИЧЕСКАЯ ОШИБКА БЕЗОПАСНОСТИ: В `secrets.toml` не задан `SESSION_SECRET` или `ADMIN_PASSWORD`.")
        st.stop()
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
    login = login.strip().lower()
    email = email.strip().lower()
    salt_hex, pw_hash = _make_password(password)
    created_at = datetime.utcnow().isoformat()
    success, err = get_user_repo().create_user(
        full_name, login, email, phone, salt_hex, pw_hash, role, status, created_at
    )
    if not success and err == "integrity_error":
        log.warning(f"Auth: Attempt to create duplicate user: {_mask_identifier(email)}")
        raise UserAlreadyExistsError("User with this login or email already exists")
    
    get_audit_repo().log_action(
        action=AuditAction.USER_CREATE,
        target_type="user",
        target_id=login,
        metadata={"role": role, "status": status}
    )
    
    token = get_secret("YANDEX_TOKEN") or os.getenv("YANDEX_TOKEN")
    if token:
        sync_users_to_yandex(token)

def authenticate_user(login, password):
    login = login.strip().lower()
    now_iso = datetime.utcnow().isoformat()
    now_ts = datetime.utcnow().timestamp()

    repo = get_user_repo()
    
    # 1. Check Rate Limits (Brute-Force protection)
    limit_dict = repo.get_login_attempts(login)
    if limit_dict:
        attempts = limit_dict["attempts"]
        last_attempt_str = limit_dict["last_attempt"]
        try:
            last_attempt_time = datetime.fromisoformat(last_attempt_str).timestamp()
            # Exponential backoff base 5 minutes
            cooldown_seconds = 300 * (2 ** max(0, attempts - 5))
            if attempts >= 5 and (now_ts - last_attempt_time) < cooldown_seconds:
                remaining = int(cooldown_seconds - (now_ts - last_attempt_time))
                log.warning(f"Auth: Blocked login attempt for {_mask_identifier(login)}. Attempts: {attempts}. Cooldown: {remaining}s")
                get_audit_repo().log_action(
                    action=AuditAction.LOGIN_BLOCKED,
                    target_type="system",
                    target_id=login,
                    result="fail",
                    metadata={"reason": "brute_force_block", "attempts": attempts, "cooldown": remaining}
                )
                raise InvalidCredentialsError(f"⚠️ Слишком много попыток входа. Попробуйте через {remaining} секунд.")
            elif attempts >= 5 and (now_ts - last_attempt_time) >= cooldown_seconds:
                # Reset if cooled down
                repo.reset_login_attempts(login)
        except ValueError:
            pass

    # 2. Lookup User
    user = repo.get_user_by_login(login)

    if not user:
        _record_failed_attempt(login, now_iso)
        log.warning(f"Auth: Failed login attempt (user not found) for {_mask_identifier(login)}")
        get_audit_repo().log_action(AuditAction.LOGIN_FAIL, "system", target_id=login, result="fail", metadata={"reason": "user_not_found"})
        raise InvalidCredentialsError("Неверный логин или пароль.")
    
    # 3. Verify Pass
    if not _verify_password(password, user["password_salt"], user["password_hash"]):
        _record_failed_attempt(login, now_iso)
        log.warning(f"Auth: Failed login attempt (invalid password) for {_mask_identifier(login)}")
        get_audit_repo().log_action(AuditAction.LOGIN_FAIL, "system", target_id=login, result="fail", metadata={"reason": "invalid_password"})
        raise InvalidCredentialsError("Неверный логин или пароль.")
        
    # 4. Filter Status
    if user["status"] != "approved":
         log.warning(f"Auth: Login attempt by unapproved user {_mask_identifier(login)}")
         get_audit_repo().log_action(AuditAction.LOGIN_FAIL, "system", target_id=login, result="deny", metadata={"reason": "unapproved"})
         raise InvalidCredentialsError("Ваш аккаунт пока не одобрен администратором.")
         
    # 5. Success -> Reset attempts
    repo.delete_login_attempts(login)
    log.info(f"Auth: Successful login for {_mask_identifier(login)}")
    ip_addr = None
    try:
        ip_addr = st.context.headers.get("x-forwarded-for") or st.context.headers.get("x-real-ip")
        if ip_addr: ip_addr = ip_addr.split(",")[0].strip()
    except Exception:
        pass
        
    get_audit_repo().log_action(
        AuditAction.LOGIN_SUCCESS, "system", 
        actor_user_id=user["id"], 
        actor_role=user["role"], 
        target_id=login, 
        result="success",
        ip_address=ip_addr
    )

    return user

def _record_failed_attempt(login, attempt_time):
     get_user_repo().record_failed_attempt(login, attempt_time)

def get_pending_users():
    return get_user_repo().get_pending_users()

def get_all_users():
    return get_user_repo().get_all_users()

def get_user_by_id(user_id):
    return get_user_repo().get_user_by_id(user_id)

def create_runtime_session(user_id, user_agent=None):
    now_iso = datetime.utcnow().isoformat()
    expires_at = datetime.utcnow() + timedelta(hours=SESSION_TTL_HOURS)
    expires_iso = expires_at.isoformat()
    exp_ts = int(expires_at.timestamp())
    token = _sign_payload(f"{user_id}:{exp_ts}")
    ua_hash = _hash_user_agent(user_agent)
    get_user_repo().create_session(token, user_id, expires_iso, now_iso, ua_hash)

    # Keep in-memory mirror for quick access inside same process.
    sessions = get_runtime_sessions()
    sessions[token] = {"user_id": user_id, "expires_at": expires_iso, "ua_hash": ua_hash}
    return token

def resolve_runtime_session(token, user_agent=None):
    now = datetime.utcnow()
    repo = get_user_repo()
    row = repo.get_session(token)

    if not row:
        # Try stateless token if DB session not found (survives server restarts)
        user_id = _unsign_token(token)
        if user_id is None:
            return None
        expires_iso = (datetime.utcnow() + timedelta(hours=SESSION_TTL_HOURS)).isoformat()
        ua_hash = _hash_user_agent(user_agent)
        repo.create_session(token, user_id, expires_iso, now.isoformat(), ua_hash)
        return user_id

    user_id, expires_raw, expected_ua_hash = row
    try:
        expires_at = datetime.fromisoformat(expires_raw)
    except ValueError:
        repo.delete_session(token)
        return None

    if now > expires_at:
        repo.delete_session(token)
        return None

    repo.update_session_last_seen(token, now.isoformat())

    # Backward compatibility / in-memory mirror.
    sessions = get_runtime_sessions()
    sessions[token] = {"user_id": user_id, "expires_at": expires_raw, "ua_hash": _hash_user_agent(user_agent)}
    return user_id

def drop_runtime_session(token):
    get_user_repo().delete_session(token)

    sessions = get_runtime_sessions()
    sessions.pop(token, None)

def update_user_status(user_id, status):
    get_user_repo().update_user_status(user_id, status)
    
    try:
        current_admin = st.session_state.auth_user
        admin_id = current_admin.id if current_admin else None
        admin_role = current_admin.role if current_admin else None
    except Exception:
        admin_id, admin_role = None, None
        
    get_audit_repo().log_action(
        action=AuditAction.USER_STATUS_CHANGE,
        target_type="user",
        target_id=str(user_id),
        actor_user_id=st.session_state.auth_user.id if st.session_state.get("auth_user") else None,
        actor_role=st.session_state.auth_user.role if st.session_state.get("auth_user") else None,
        metadata={"new_status": str(status)}
    )
    
    token = get_secret("YANDEX_TOKEN") or os.getenv("YANDEX_TOKEN")
    if token:
        sync_users_to_yandex(token)

def update_user_role(user_id, role):
    get_user_repo().update_user_role(user_id, role)
    
    try:
        current_admin = st.session_state.auth_user
        admin_id = current_admin.id if current_admin else None
        admin_role = current_admin.role if current_admin else None
    except Exception:
        admin_id, admin_role = None, None
        
    get_audit_repo().log_action(
        action=AuditAction.USER_ROLE_CHANGE,
        target_type="user",
        target_id=str(user_id),
        actor_user_id=st.session_state.auth_user.id if st.session_state.get("auth_user") else None,
        actor_role=st.session_state.auth_user.role if st.session_state.get("auth_user") else None,
        metadata={"new_role": role}
    )
    
    token = get_secret("YANDEX_TOKEN") or os.getenv("YANDEX_TOKEN")
    if token:
        sync_users_to_yandex(token)

def bootstrap_admin():
    admin_login = get_secret("ADMIN_LOGIN") or os.getenv("ADMIN_LOGIN")
    admin_password = get_secret("ADMIN_PASSWORD") or os.getenv("ADMIN_PASSWORD")
    if not admin_login or not admin_password:
        return

    if get_user_repo().check_admin_exists(admin_login):
        return

    admin_name = get_secret("ADMIN_NAME") or os.getenv("ADMIN_NAME") or "Администратор"
    admin_email = get_secret("ADMIN_EMAIL") or os.getenv("ADMIN_EMAIL") or f"{admin_login}@local"
    admin_phone = get_secret("ADMIN_PHONE") or os.getenv("ADMIN_PHONE") or "+70000000000"
    try:
        create_user(admin_name, admin_login, admin_email, admin_phone, admin_password, role="admin", status="approved")
    except UserAlreadyExistsError:
        pass # Already exists
