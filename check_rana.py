import sys
sys.path.insert(0, "src")

from telegramonline.storage import connect
from telegramonline.config import Settings

settings = Settings.from_env()
conn = connect(settings.database_path)
cur = conn.execute(
    "SELECT vehicle_name, trim, raw_text FROM ads "
    "WHERE (vehicle_name LIKE '%رانا%' OR trim LIKE '%رانا%' OR raw_text LIKE '%رانا%') "
    "ORDER BY id DESC LIMIT 15"
)
for row in cur.fetchall():
    print(repr(row))
