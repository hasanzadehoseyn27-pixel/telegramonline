import sys
import io
sys.path.insert(0, "src")

from telegramonline.storage import connect
from telegramonline.config import Settings

settings = Settings.from_env()
conn = connect(settings.database_path)

with io.open("account2_channels.txt", "w", encoding="utf-8") as f:
    f.write("--- channels joined via account 2 ---\n")
    cur = conn.execute("SELECT username, title, joined, added_at FROM channels WHERE account = 2")
    rows = cur.fetchall()
    if not rows:
        f.write("هیچی پیدا نشد\n")
    for r in rows:
        f.write(str(tuple(r)) + "\n")

    f.write("\n--- source_groups joined via account 2 ---\n")
    cur = conn.execute("SELECT username, title, joined, added_at FROM source_groups WHERE account = 2")
    rows = cur.fetchall()
    if not rows:
        f.write("هیچی پیدا نشد\n")
    for r in rows:
        f.write(str(tuple(r)) + "\n")

print("done, check account2_channels.txt")
