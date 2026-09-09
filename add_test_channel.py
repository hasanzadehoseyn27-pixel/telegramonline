import sys
sys.path.insert(0, "src")

from telegramonline.storage import connect, add_channel
from telegramonline.config import Settings

settings = Settings.from_env()
conn = connect(settings.database_path)

channel_id = add_channel(conn, "carsell2022", title=None)
if channel_id is None:
    print("این کانال از قبل تو دیتابیس بود (تکراری).")
else:
    print(f"✅ کانال با id={channel_id} اضافه شد. تا ۳۰ ثانیه دیگه Collector خودش join می‌کنه.")
