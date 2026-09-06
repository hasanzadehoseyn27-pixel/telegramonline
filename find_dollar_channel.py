import sys
import io
sys.path.insert(0, "src")

from telegramonline.storage import connect
from telegramonline.config import Settings

settings = Settings.from_env()
conn = connect(settings.database_path)

with io.open("dollar_channel.txt", "w", encoding="utf-8") as f:
    f.write("--- channels table (all rows containing قیمت) ---\n")
    cur = conn.execute("SELECT id, chat_id, chat_name, is_active FROM channels WHERE chat_name LIKE '%قیمت%'")
    rows = cur.fetchall()
    if not rows:
        f.write("چیزی پیدا نشد\n")
    for r in rows:
        f.write(str(tuple(r)) + "\n")

    f.write("\n--- source_groups table (all rows containing قیمت) ---\n")
    try:
        cur = conn.execute("SELECT * FROM source_groups WHERE chat_name LIKE '%قیمت%'")
        rows = cur.fetchall()
        if not rows:
            f.write("چیزی پیدا نشد\n")
        for r in rows:
            f.write(str(tuple(r)) + "\n")
    except Exception as e:
        f.write(f"خطا: {e}\n")

    f.write("\n--- channels table (last 20 rows, to see recent additions) ---\n")
    cur = conn.execute("SELECT id, chat_id, chat_name, is_active FROM channels ORDER BY id DESC LIMIT 20")
    for r in cur.fetchall():
        f.write(str(tuple(r)) + "\n")

print("done, check dollar_channel.txt")
