import datetime

print(datetime.datetime.utcnow().isoformat())
try:
    datetime.datetime.fromisoformat("2025-02-25T09:28:44.123456")
    print("fromisoformat ok")
except Exception as e:
    print(e)
