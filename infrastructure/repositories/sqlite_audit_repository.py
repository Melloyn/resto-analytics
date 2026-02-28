import sqlite3
import json
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
import os
import logging
from enum import Enum

log = logging.getLogger(__name__)

class AuditAction(str, Enum):
    LOGIN_SUCCESS = "LOGIN_SUCCESS"
    LOGIN_FAIL = "LOGIN_FAIL"
    LOGIN_BLOCKED = "LOGIN_BLOCKED"
    LOGOUT = "LOGOUT"
    RBAC_DENIED = "RBAC_DENIED"
    USER_CREATE = "USER_CREATE"
    USER_ROLE_CHANGE = "USER_ROLE_CHANGE"
    USER_STATUS_CHANGE = "USER_STATUS_CHANGE"
    USER_DELETE = "USER_DELETE"
    CATEGORY_UPDATE = "CATEGORY_UPDATE"
    CATEGORY_DELETE = "CATEGORY_DELETE"
    YANDEX_SYNC_DOWNLOAD = "YANDEX_SYNC_DOWNLOAD"
    YANDEX_SYNC_UPLOAD = "YANDEX_SYNC_UPLOAD"
    SYSTEM_ERROR = "SYSTEM_ERROR"

ALLOWED_METADATA_KEYS = {
    "reason", "attempts", "cooldown", "new_status", "new_role", 
    "new_cat", "error_message", "old_role", "deleted_cat",
    "target_action", "role", "status"
}

class SQLiteAuditRepository:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def _conn(self):
        return sqlite3.connect(self.db_path)

    def log_action(
        self,
        action: Any,
        target_type: str,
        actor_user_id: Optional[int] = None,
        actor_role: Optional[str] = None,
        target_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        result: str = "success"
    ):
        """Logs an action to the audit repository. Metadata is JSON serialized and constrained."""
        try:
            meta_str = None
            if metadata is not None:
                safe_meta = {}
                for k, v in metadata.items():
                    if k in ALLOWED_METADATA_KEYS and "password" not in str(v).lower() and "token" not in str(v).lower():
                        safe_meta[k] = v
                try:
                    meta_str = json.dumps(safe_meta)
                    if len(meta_str) > 2000:
                        safe_meta["truncated"] = True
                        meta_str = json.dumps(safe_meta)[:2000]
                except (TypeError, ValueError):
                    meta_str = "{\"error\": \"unserializable\"}"

            # Truncate strings to prevent db inflation
            ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            action_val = action.value if hasattr(action, "value") else str(action)[:50]
            if not action_val: action_val = "UNKNOWN"
            
            target_type = str(target_type)[:50] if target_type else "UNKNOWN"
            actor_role = str(actor_role)[:20] if actor_role is not None else None
            target_id = str(target_id)[:100] if target_id is not None else None
            ip_address = str(ip_address)[:45] if ip_address is not None else None
            result = str(result)[:20] if result else "unknown"

            with self._conn() as conn:
                conn.execute("""
                    INSERT INTO audit_log 
                    (ts, actor_user_id, actor_role, action, target_type, target_id, metadata_json, ip_address, result) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (ts, actor_user_id, actor_role, action_val, target_type, target_id, meta_str, ip_address, result))
                conn.commit()
        except Exception as e:
            # Audit failures must not crash the main application
            log.error(f"Audit log failed for action {action}: {e}", exc_info=True)

    def get_logs(self, limit: int = 100, action_filter: Optional[str] = None, user_filter: Optional[str] = None) -> List[Tuple]:
        """Fetches the most recent audit logs for the admin view."""
        try:
            with self._conn() as conn:
                query = """
                    SELECT 
                        a.id, a.ts, 
                        COALESCE(u.login, a.actor_user_id, 'SYSTEM'), 
                        a.actor_role, a.action, a.target_type, a.target_id, 
                        a.metadata_json, a.ip_address, a.result
                    FROM audit_log a
                    LEFT JOIN users u ON a.actor_user_id = u.id
                    WHERE 1=1
                """
                params = []
                if action_filter and action_filter != "Все":
                    query += " AND a.action = ?"
                    params.append(action_filter)
                if user_filter and user_filter != "Все":
                    query += " AND (u.login LIKE ? OR a.actor_user_id = ?)"
                    params.append(f"%{user_filter}%")
                    try:
                        params.append(int(user_filter))
                    except ValueError:
                        params.append(-1)
                
                query += " ORDER BY a.ts DESC LIMIT ?"
                params.append(limit)
                
                return conn.execute(query, tuple(params)).fetchall()
        except Exception as e:
            log.error(f"Failed to fetch audit logs: {e}", exc_info=True)
            return []
