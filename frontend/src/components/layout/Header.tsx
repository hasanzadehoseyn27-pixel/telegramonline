import { Bell, Moon, Settings, Sun } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { getAlertEventsCount } from "../../api/alerts.api";
import { formatNumber } from "../../utils/format";
import LiveClock from "../common/LiveClock";

interface Props {
  theme: "dark" | "light";
  onToggleTheme: () => void;
}

export default function Header({ theme, onToggleTheme }: Props) {
  const navigate = useNavigate();
  const { data: alertCount = 0 } = useQuery({
    queryKey: ["alerts", "events-count"],
    queryFn: getAlertEventsCount,
    refetchInterval: 5000,
  });

  return (
    <header className="glass-panel fixed left-0 right-64 top-0 z-20 flex h-20 items-center justify-between gap-3 px-4 max-lg:right-0 max-sm:h-16 lg:px-7">
      <div className="flex items-center gap-2 sm:gap-3">
        <button
          aria-label="تنظیمات و گزارش‌ها"
          title="تنظیمات و گزارش‌ها"
          onClick={() => navigate("/settings")}
          className="grid h-11 w-11 place-items-center rounded-xl bg-white/10 text-white transition hover:-translate-y-0.5 hover:bg-cyan-300 hover:text-slate-950 max-sm:h-10 max-sm:w-10"
        >
          <Settings size={21} />
        </button>
        <button
          aria-label="هشدار قیمت"
          title="هشدار قیمت"
          onClick={() => navigate("/alerts")}
          className="relative grid h-11 w-11 place-items-center rounded-xl bg-white/10 text-white transition hover:-translate-y-0.5 hover:bg-rose-400 hover:text-white max-sm:h-10 max-sm:w-10"
        >
          <Bell
            size={21}
            className={alertCount > 0 ? "animate-[alertShake_1.6s_ease-in-out_infinite]" : ""}
          />
          {alertCount > 0 && (
            <span className="absolute -right-1 -top-1 grid h-6 min-w-6 place-items-center rounded-full bg-rose-500 px-1 text-xs font-black text-white shadow-lg shadow-rose-500/40 animate-pulse">
              {formatNumber(alertCount)}
            </span>
          )}
        </button>
        <button
          aria-label="تغییر حالت شب و روز"
          title="تغییر حالت شب و روز"
          onClick={onToggleTheme}
          className="grid h-11 w-11 place-items-center rounded-xl bg-white/10 text-white transition hover:-translate-y-0.5 hover:bg-white hover:text-slate-950 max-sm:h-10 max-sm:w-10"
        >
          {theme === "dark" ? <Moon size={21} /> : <Sun size={21} />}
        </button>
      </div>

      <div className="min-w-0 flex-1 text-left max-md:hidden">
        <h1 className="truncate text-base font-black lg:text-xl">داشبورد زنده TelegramOnline</h1>
        <p className="mt-1 truncate text-xs text-slate-400 theme-muted">پایش لحظه‌ای آگهی‌های خودرو از کانال‌های تلگرام</p>
      </div>

      <div className="max-sm:hidden">
        <LiveClock compact />
      </div>
    </header>
  );
}
