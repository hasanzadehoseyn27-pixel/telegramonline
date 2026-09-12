import sys
import io
sys.path.insert(0, "src")

from telegramonline.storage import connect
from telegramonline.config import Settings

settings = Settings.from_env()
conn = connect(settings.database_path)

with io.open("check_feedback_loop.txt", "w", encoding="utf-8") as f:
    f.write("--- in channels table ---\n")
    cur = conn.execute("SELECT id, username, active, joined, account FROM channels WHERE username = 'gorohekhodroe'")
    rows = cur.fetchall()
    if not rows:
        f.write("پیدا نشد\n")
    for r in rows:
        f.write(str(tuple(r)) + "\n")

    f.write("\n--- in source_groups table ---\n")
    cur = conn.execute("SELECT id, username, active, joined, account FROM source_groups WHERE username = 'gorohekhodroe'")
    rows = cur.fetchall()
    if not rows:
        f.write("پیدا نشد\n")
    for r in rows:
        f.write(str(tuple(r)) + "\n")

print("done, check check_feedback_loop.txt")
