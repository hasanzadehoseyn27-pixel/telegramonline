import sys
sys.path.insert(0, "src")

from telegramonline.storage import connect
from telegramonline.config import Settings

settings = Settings.from_env()
conn = connect(settings.database_path)
cur = conn.execute(
    "SELECT id, username, title, active, joined, join_attempts, account FROM channels WHERE username = 'carsell2022'"
)
row = cur.fetchone()
if row is None:
    print("پیدا نشد!")
else:
    print(tuple(row))
