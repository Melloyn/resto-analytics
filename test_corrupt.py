import sqlite3
import os

with open('corrupted.db', 'wb') as f:
    f.write(b"--boundary\r\nContent-Disposition: form-data; name=\"file\"; filename=\"users.db\"\r\n\r\nSQLite format 3\0")

try:
    conn = sqlite3.connect('corrupted.db')
    conn.execute("CREATE TABLE IF NOT EXISTS test (id INTEGER)")
    print("Success")
except Exception as e:
    print(f"Error: {e}")
