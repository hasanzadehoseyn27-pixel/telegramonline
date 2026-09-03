import sys
import io
sys.path.insert(0, "src")

from telegramonline.storage import connect
from telegramonline.config import Settings
from telegramonline.carx_bridge import collect_today_rows

settings = Settings.from_env()
conn = connect(settings.database_path)
rows = collect_today_rows(conn)

matches = [
    r for r in rows
    if "رانا" in (r.get("raw_text") or "") and "پانا" in (r.get("raw_text") or "")
]

with io.open("today_rana_pana.txt", "w", encoding="utf-8") as f:
    f.write(f"today's total rows: {len(rows)}\n")
    f.write(f"rana+pana matches: {len(matches)}\n\n")
    for r in matches[:10]:
        f.write(str((r.get("vehicle_name"), r.get("trim"))) + "\n")
print("done, check today_rana_pana.txt")
