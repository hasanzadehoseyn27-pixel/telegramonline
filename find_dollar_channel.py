import sys
import io
sys.path.insert(0, "src")

from telegramonline.storage import connect
from telegramonline.config import Settings

settings = Settings.from_env()
conn = connect(settings.database_path)
cur = conn.execute(
    "SELECT id, chat_id, chat_name, is_active FROM channels WHERE chat_name LIKE '%دلار%' OR chat_name LIKE '%لحظه%'"
)
rows = cur.fetchall()

with io.open("dollar_channel.txt", "w", encoding="utf-8") as f:
    if not rows:
        f.write("چیزی پیدا نشد\n")
    for r in rows:
        f.write(str(tuple(r)) + "\n")
print("done, check dollar_channel.txt")
