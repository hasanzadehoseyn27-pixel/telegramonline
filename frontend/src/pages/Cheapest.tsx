import { motion } from "framer-motion";
import { ChevronLeft, ChevronRight, ExternalLink, Flame, Phone, Search } from "lucide-react";
import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getLiveCheapestVehicles } from "../api/vehicles.api";
import { formatCount, formatDateTime, formatNumber, telegramLink } from "../utils/format";

const PAGE_SIZE = 24;
// وقتی جستجو فعاله، به‌جای فقط همون صفحه، یه بچ بزرگ‌تر می‌گیریم تا جستجو
// روی همه‌ی مدل‌های امروز کار کنه، نه فقط صفحه‌ی جاری.
const SEARCH_BATCH_SIZE = 200;

export default function Cheapest() {
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(0);
  const isSearching = search.trim().length > 0;

  const { data, isLoading } = useQuery({
    queryKey: ["vehicles", "cheapest-live", isSearching ? "search" : page],
    queryFn: () =>
      isSearching
        ? getLiveCheapestVehicles(SEARCH_BATCH_SIZE, 0)
        : getLiveCheapestVehicles(PAGE_SIZE, page * PAGE_SIZE),
    refetchInterval: 5000,
  });

  const items = data?.items ?? [];
  const total = data?.total ?? 0;
  const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE));

  const filtered = useMemo(() => {
    const normalized = search.trim().toLowerCase();
    if (!normalized) {
      return items;
    }

    return items.filter((item) => {
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
  }, [items, search]);

  return (
    <div className="grid h-full min-h-0 grid-rows-[auto_minmax(0,1fr)_auto] gap-4">
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
                onChange={(event) => {
                  setSearch(event.target.value);
                  setPage(0);
                }}
                className="min-w-0 flex-1 bg-transparent text-sm outline-none"
                placeholder="جستجوی مدل، رنگ، کانال..."
              />
            </div>
            <div className="rounded-full bg-cyan-300 px-4 py-2 text-sm font-black text-slate-950">
              {isSearching
                ? `${formatCount(filtered.length)} نتیجه`
                : `${formatCount(items.length)} از ${formatCount(total)} مدل`}
            </div>
          </div>
        </div>
      </div>

      <div className="min-h-0 overflow-y-auto rounded-xl scroll-area">
        {isLoading ? (
          <div className="grid h-full place-items-center text-slate-400">در حال دریافت کمترین قیمت‌ها...</div>
        ) : filtered.length === 0 ? (
          <div className="grid h-full place-items-center text-slate-400">موردی پیدا نشد</div>
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
                      <div className="mt-2 flex flex-wrap items-center gap-x-2 gap-y-1 truncate text-sm text-slate-400 theme-muted">
                        <span>
                          {item.color ?? "رنگ نامشخص"} · {item.year ?? "مدل نامشخص"}
                        </span>
                        <span className="rounded-full bg-white/10 px-2 py-0.5 text-[11px] font-bold text-cyan-100">
                          از {formatCount(item.ad_count)} آگهی
                        </span>
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

      {!isSearching && total > PAGE_SIZE && (
        <div className="glass-panel flex items-center justify-between gap-3 rounded-2xl p-3">
          <button
            type="button"
            onClick={() => setPage((p) => Math.max(0, p - 1))}
            disabled={page === 0}
            className="flex items-center gap-1 rounded-xl bg-white/10 px-3 py-2 text-sm font-bold transition hover:bg-white hover:text-slate-950 disabled:opacity-40 disabled:hover:bg-white/10 disabled:hover:text-inherit"
          >
            <ChevronRight size={16} />
            قبلی
          </button>
          <div className="text-sm text-slate-400">
            صفحه {formatCount(page + 1)} از {formatCount(pageCount)}
          </div>
          <button
            type="button"
            onClick={() => setPage((p) => Math.min(pageCount - 1, p + 1))}
            disabled={page >= pageCount - 1}
            className="flex items-center gap-1 rounded-xl bg-white/10 px-3 py-2 text-sm font-bold transition hover:bg-white hover:text-slate-950 disabled:opacity-40 disabled:hover:bg-white/10 disabled:hover:text-inherit"
          >
            بعدی
            <ChevronLeft size={16} />
          </button>
        </div>
      )}
    </div>
  );
}
