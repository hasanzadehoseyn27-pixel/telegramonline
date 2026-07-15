import { motion } from "framer-motion";
import { ExternalLink, Flame, Phone, Search } from "lucide-react";
import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getLiveCheapestVehicles } from "../api/vehicles.api";
import { formatCount, formatDateTime, formatNumber, telegramLink } from "../utils/format";

export default function Cheapest() {
  const [search, setSearch] = useState("");
  const { data = [], isLoading } = useQuery({
    queryKey: ["vehicles", "cheapest-live"],
    queryFn: () => getLiveCheapestVehicles(200),
    refetchInterval: 5000,
  });

  const filtered = useMemo(() => {
    const normalized = search.trim().toLowerCase();
    if (!normalized) {
      return data;
    }

    return data.filter((item) => {
      return [
        item.vehicle_name,
        item.vehicle_key,
        item.color,
        item.channel_username,
        item.year ? String(item.year) : "",
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase()
        .includes(normalized);
    });
  }, [data, search]);

  return (
    <div className="grid h-full min-h-0 grid-rows-[auto_minmax(0,1fr)] gap-4">
      <div className="glass-panel rounded-2xl p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="flex items-center gap-2 text-xl font-black">
              <Flame className="text-cyan-200" />
              کمترین قیمت زنده امروز
            </div>
            <div className="mt-1 text-sm text-slate-400 theme-muted">
              هر کارت ارزان‌ترین آگهی پیدا شده برای همان مدل خودرو در روز جاری است.
            </div>
          </div>
          <div className="flex min-w-0 flex-wrap items-center gap-2 max-sm:w-full">
            <div className="flex h-11 min-w-0 flex-1 items-center gap-2 rounded-xl border border-white/10 bg-slate-950/70 px-3 sm:w-72 sm:flex-none">
              <Search size={17} className="shrink-0 text-slate-500" />
              <input
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                className="min-w-0 flex-1 bg-transparent text-sm outline-none"
                placeholder="جستجوی مدل، رنگ، کانال..."
              />
            </div>
            <div className="rounded-full bg-cyan-300 px-4 py-2 text-sm font-black text-slate-950">
              {formatCount(filtered.length)} مدل
            </div>
          </div>
        </div>
      </div>

      <div className="min-h-0 overflow-y-auto rounded-xl scroll-area">
        {isLoading ? (
          <div className="grid h-full place-items-center text-slate-400">در حال دریافت کمترین قیمت‌ها...</div>
        ) : (
          <div className="grid gap-4 pb-2 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">
            {filtered.map((item, index) => {
              const link = item.telegram_link ?? telegramLink(item.channel_username, item.source_message_id);
              return (
                <motion.a
                  key={`${item.vehicle_key}-${item.id}`}
                  href={link}
                  target="_blank"
                  rel="noreferrer"
                  initial={{ opacity: 0, y: 16 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: Math.min(index * 0.02, 0.28) }}
                  className="glass-panel group rounded-2xl p-4 transition hover:-translate-y-1 hover:border-cyan-300/50"
                  style={{ animation: index < 3 ? "softBlink 2.4s ease-in-out infinite" : undefined }}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="truncate text-xl font-black">{item.vehicle_name ?? "نامشخص"}</div>
                      <div className="mt-2 truncate text-sm text-slate-400 theme-muted">
                        {item.color ?? "رنگ نامشخص"} · {item.year ?? "مدل نامشخص"}
                      </div>
                    </div>
                    <span className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-cyan-300 text-slate-950 transition group-hover:bg-white">
                      <ExternalLink size={18} />
                    </span>
                  </div>

                  <div className="mt-8 text-4xl font-black text-cyan-100">
                    {formatNumber(item.price_million)}
                    <span className="mr-2 text-sm text-slate-400">میلیون</span>
                  </div>

                  <div className="mt-5 grid grid-cols-2 gap-2 text-xs text-slate-300">
                    <div className="rounded-xl bg-white/5 p-3">
                      کارکرد
                      <div className="mt-1 font-bold text-white">
                        {item.mileage_km ? `${formatNumber(item.mileage_km)} km` : "-"}
                      </div>
                    </div>
                    <div className="rounded-xl bg-white/5 p-3">
                      کانال
                      <div className="mt-1 truncate font-bold text-white">
                        {item.channel_username ? `@${item.channel_username}` : "-"}
                      </div>
                    </div>
                  </div>

                  <div className="mt-4 flex items-center justify-between gap-2 text-xs text-slate-400">
                    <span className="truncate">{formatDateTime(item.message_date)}</span>
                    {item.phone && (
                      <span className="flex shrink-0 items-center gap-1">
                        <Phone size={13} />
                        {item.phone}
                      </span>
                    )}
                  </div>
                </motion.a>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
