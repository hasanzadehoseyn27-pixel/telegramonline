// جمع‌کننده‌ی روبیکا با PM2:
//   pm2 start ecosystem.rubika.config.js
module.exports = {
  apps: [
    {
      name: "rubika-collector",
      cwd: __dirname,
      script: "venv/Scripts/python.exe",
      args: "-m telegramonline.rubika.collector",
      interpreter: "none",
      autorestart: true,
      watch: false,
      max_restarts: 50,
      restart_delay: 5000,
      env: {
        PYTHONPATH: "src",
        PYTHONUNBUFFERED: "1",
        // کنسول ویندوز زیر PM2 گاهی cp1252 است و چاپ فارسی برنامه را می‌اندازد
        PYTHONUTF8: "1",
        PYTHONIOENCODING: "utf-8"
      }
    }
  ]
};
