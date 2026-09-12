import sys
sys.path.insert(0, "src")

from telegramonline.storage import connect
from telegramonline.config import Settings

settings = Settings.from_env()
conn = connect(settings.database_path)

conn.execute("UPDATE channels SET active = 0 WHERE username = 'gorohekhodroe'")
conn.commit()

cur = conn.execute("SELECT id, username, active, joined FROM channels WHERE username = 'gorohekhodroe'")
print("channels row now:", tuple(cur.fetchone()))
