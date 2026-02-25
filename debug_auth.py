import pytest
import auth
from pathlib import Path

db_file = Path("test_users.db")
auth.USERS_DB = str(db_file)
auth.init_auth_db()
auth.create_user("Test User", "bruteuser", "brute@test.com", "12345", "password123", status="approved")

for i in range(1, 7):
    try:
         auth.authenticate_user("bruteuser", "wrong_pass")
    except auth.InvalidCredentialsError as e:
         print(f"Attempt {i}: {e}")
         
    with auth._db_conn() as conn:
         row = conn.execute("SELECT attempts FROM login_attempts WHERE login='bruteuser'").fetchone()
         print(f"DB attempts after {i}: {row}")

db_file.unlink()
