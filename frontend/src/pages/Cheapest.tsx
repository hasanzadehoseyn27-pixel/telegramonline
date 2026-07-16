import { AnimatePresence, motion } from "framer-motion";
import { ChevronLeft, ChevronRight, ExternalLink, Flame, Phone, Search, X } from "lucide-react";
import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getAdsForModel, getLiveCheapestVehicles } from "../api/vehicles.api";
import { formatCount, formatDateTime, formatNumber, telegramLink } from "../utils/format";

const PAGE_SIZE = 24;
// وقتی جستجو فعاله، به‌جای فقط همون صفحه، یه بچ بزرگ‌تر می‌گیریم تا جستجو
// روی همه‌ی مدل‌های امروز کار کنه، نه فقط صفحه‌ی جاری.
const SEARCH_BATCH_SIZE = 200;

function VehicleAdsModal({
  vehicleKey,
  vehicleName,
  day,
  onClose,
}: {
  vehicleKey: string;
  vehicleName: string;
  day: "today" | "yesterday";
  onClose: () => void;
}) {
  const { data: ads = [], isLoading } = useQuery({
    queryKey: ["vehicles", "for-model", vehicleKey, day],
    queryFn: () => getAdsForModel(vehicleKey, day),
  });

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-50 grid place-items-center bg-slate-950/78 p-4 backdrop-blur-md"
        onClick={onClose}
      >
        <motion.div
          initial={{ opacity: 0, y: 18, scale: 0.96 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 18, scale: 0.96 }}
          onClick={(event) => event.stopPropagation()}
          className="glass-panel flex max-h-[86vh] w-full max-w-2xl flex-col overflow-hidden rounded-xl"
        >
          <div className="flex items-center justify-between gap-3 border-b border-white/10 p-4">
            <div>
              <div className="font-black">{vehicleName}</div>
              <div className="mt-1 text-xs text-slate-400">
                همه‌ی آگهی‌های پیداشده، از کمترین تا بیشترین قیمت — روی هرکدوم بزن تا بره تلگرام
              </div>
            </div>
            <button
              onClick={onClose}
              className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-white/10 hover:bg-white/20"
            >
              <X size={17} />
            </button>
          </div>

          <div className="min-h-0 flex-1 overflow-y-auto scroll-area">
            {isLoading ? (
              <div className="grid h-40 place-items-center text-slate-400">در حال دریافت...</div>
            ) : ads.length === 0 ? (
              <div className="grid h-40 place-items-center text-slate-400">آگهی‌ای پیدا نشد</div>
            ) : (
              <div className="divide-y divide-white/10">
                {ads.map((ad, index) => {
                  const link = ad.telegram_link ?? telegramLink(ad.channel_username, ad.source_message_id);
                  return (
                    <a
                      key={ad.id}
                      href={link ?? undefined}
                      target="_blank"
                      rel="noreferrer"
                      className="flex items-center justify-between gap-3 px-4 py-3 transition hover:bg-white/5"
                    >
                      <div className="flex items-center gap-3 min-w-0">
                        <span className="grid h-7 w-7 shrink-0 place-items-center rounded-full bg-white/10 text-xs font-black text-slate-300">
                          {index + 1}
                        </span>
                        <div className="min-w-0">
                          <div className="truncate text-sm font-bold">
                            {ad.color ?? "رنگ نامشخص"} · {ad.year ?? "مدل نامشخص"}
                          </div>
                          <div className="mt-0.5 truncate text-xs text-slate-400">
                            {ad.channel_username ? `@${ad.channel_username}` : "-"} · {formatDateTime(ad.message_date)}
                          </div>
                        </div>
                      </div>
                      <div className="flex shrink-0 items-center gap-2">
                        <span className="text-base font-black text-cyan-100">
                          {formatNumber(ad.price_million)} <span className="text-xs text-slate-400">میلیون</span>
                        </span>
                        <ExternalLink size={15} className="text-slate-500" />
                      </div>
                    </a>
                  );
                })}
              </div>
            )}
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}

export default function Cheapest() {
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(0);
  const [day, setDay] = useState<"today" | "yesterday">("today");
  const [selected, setSelected] = useState<{ key: string; name: string }>();
  const isSearching = search.trim().length > 0;

  const { data, isLoading } = useQuery({
    queryKey: ["vehicles", "cheapest-live", day, isSearching ? "search" : page],
    queryFn: () =>
      isSearching
        ? getLiveCheapestVehicles(SEARCH_BATCH_SIZE, 0, day)
        : getLiveCheapestVehicles(PAGE_SIZE, page * PAGE_SIZE, day),
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
              روی هر کارت بزن تا لیست کامل قیمت‌های پیداشده‌ی همون مدل، از کمترین تا بیشترین، باز بشه.
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
            <div className="flex h-11 shrink-0 overflow-hidden rounded-xl bg-white/10 text-sm font-black">
              <button
                onClick={() => {
                  setDay("today");
                  setPage(0);
                }}
                className={["h-full px-4 transition", day === "today" ? "bg-white text-slate-950" : "hover:bg-white/20"].join(" ")}
              >
                امروز
              </button>
              <button
                onClick={() => {
                  setDay("yesterday");
                  setPage(0);
                }}
                className={["h-full px-4 transition", day === "yesterday" ? "bg-white text-slate-950" : "hover:bg-white/20"].join(" ")}
              >
                دیروز
              </button>
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
              return (
                <motion.button
                  key={`${item.vehicle_key}-${item.id}`}
                  type="button"
                  onClick={() =>
                    setSelected({ key: item.vehicle_key ?? "", name: item.vehicle_name ?? "نامشخص" })
                  }
                  initial={{ opacity: 0, y: 16 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: Math.min(index * 0.02, 0.28) }}
                  className="glass-panel group rounded-2xl p-4 text-right transition hover:-translate-y-1 hover:border-cyan-300/50"
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
                </motion.button>
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

      {selected && (
        <VehicleAdsModal vehicleKey={selected.key} vehicleName={selected.name} day={day} onClose={() => setSelected(undefined)} />
      )}
    </div>
  );
}
