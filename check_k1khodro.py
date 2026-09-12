import sys
sys.path.insert(0, "src")

from telegramonline.storage import connect
from telegramonline.config import Settings

settings = Settings.from_env()
conn = connect(settings.database_path)

cur = conn.execute("SELECT id, username, active, joined, account FROM channels WHERE username = 'k1khodro'")
row = cur.fetchone()
print("channel row:", tuple(row) if row else "پیدا نشد")

cur = conn.execute("SELECT id, username, active, joined, account FROM source_groups WHERE username = 'k1khodro'")
row = cur.fetchone()
print("source_group row:", tuple(row) if row else "پیدا نشد")
