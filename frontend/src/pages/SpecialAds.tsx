import { ExternalLink, Plus, Search, Sparkles, Trash2 } from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import {
  addWatchedVehicle,
  getSpecialAds,
  getWatchedVehicles,
  removeWatchedVehicle,
} from "../api/watchedVehicles.api";
import { CURATED_VEHICLES } from "../data/curatedVehicles";
import AdDetailModal from "../components/modal/AdDetailModal";
import { formatCount, formatDateTime, formatNumber } from "../utils/format";

export default function SpecialAds() {
  const [query, setQuery] = useState("");
  const [showList, setShowList] = useState(false);
  const [day, setDay] = useState<"today" | "yesterday">("today");
  const [selectedAdId, setSelectedAdId] = useState<number>();
  const queryClient = useQueryClient();

  const { data: watched = [] } = useQuery({
    queryKey: ["watched-vehicles"],
    queryFn: getWatchedVehicles,
    refetchInterval: 5000,
  });

  const { data: adsPage, isLoading } = useQuery({
    queryKey: ["watched-vehicles", "ads", day],
    queryFn: () => getSpecialAds(50, 0, day),
    refetchInterval: 5000,
  });

  const addMutation = useMutation({
    mutationFn: addWatchedVehicle,
    onSuccess: () => {
      setQuery("");
      setShowList(false);
      queryClient.invalidateQueries({ queryKey: ["watched-vehicles"] });
    },
  });

  const removeMutation = useMutation({
    mutationFn: removeWatchedVehicle,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["watched-vehicles"] }),
  });

  const watchedKeys = useMemo(() => new Set(watched.map((w) => w.vehicle_key)), [watched]);

  const suggestions = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    const pool = CURATED_VEHICLES.filter((v) => !watchedKeys.has(v.key));
    if (!normalized) return pool.slice(0, 30);
    return pool.filter((v) => v.name.toLowerCase().includes(normalized)).slice(0, 30);
  }, [query, watchedKeys]);

  function pick(key: string, name: string) {
    addMutation.mutate({ vehicle_key: key, vehicle_name: name });
  }

  const ads = adsPage?.items ?? [];

  return (
    <>
      <div className="grid h-full min-h-0 grid-cols-[360px_minmax(0,1fr)] gap-4 max-xl:grid-cols-1">
        <section className="glass-panel min-h-0 overflow-y-auto rounded-xl p-4 scroll-area">
          <div className="mb-4 flex items-center gap-2 text-xl font-black">
            <Sparkles className="text-cyan-200" />
            آگهی‌های خاص
          </div>
          <p className="mb-4 text-xs leading-6 text-slate-400 theme-muted">
            فقط از بین مدل‌هایی که پارسر برایشان تضمین‌شده انتخاب کن (سرچ کن، از لیست بزن) — این‌طوری «نامشخص» توی
            این بخش هیچ‌وقت پیش نمی‌آد.
          </p>

          <div className="relative">
            <div className="flex h-11 items-center gap-2 rounded-lg border border-white/10 bg-slate-950/70 px-3">
              <Search size={16} className="shrink-0 text-slate-500" />
              <input
                value={query}
                onFocus={() => setShowList(true)}
                onChange={(event) => {
                  setQuery(event.target.value);
                  setShowList(true);
                }}
                placeholder="جستجوی مدل (مثلاً: پانا ارتقا)"
                className="min-w-0 flex-1 bg-transparent text-sm outline-none"
              />
            </div>

            {showList && (
              <div className="absolute right-0 left-0 top-[calc(100%+4px)] z-10 max-h-72 overflow-y-auto rounded-lg border border-white/10 bg-slate-950 shadow-2xl scroll-area">
                {suggestions.length === 0 ? (
                  <div className="p-3 text-center text-xs text-slate-400">موردی پیدا نشد</div>
                ) : (
                  suggestions.map((v) => (
                    <button
                      key={v.key}
                      onClick={() => pick(v.key, v.name)}
                      className="flex w-full items-center justify-between gap-2 px-3 py-2.5 text-right text-sm transition hover:bg-cyan-300/10"
                    >
                      <span className="truncate">{v.name}</span>
                      <Plus size={14} className="shrink-0 text-cyan-200" />
                    </button>
                  ))
                )}
              </div>
            )}
          </div>

          {showList && (
            <button
              onClick={() => setShowList(false)}
              className="mt-2 w-full rounded-lg bg-white/5 py-1.5 text-xs text-slate-400 hover:bg-white/10"
            >
              بستن لیست
            </button>
          )}

          <div className="mt-6 space-y-2">
            {watched.length === 0 && (
              <div className="rounded-lg border border-dashed border-white/15 p-4 text-center text-xs text-slate-400">
                هنوز مدلی اضافه نکردی
              </div>
            )}
            {watched.map((item) => (
              <div
                key={item.id}
                className="flex items-center justify-between gap-2 rounded-lg border border-white/10 bg-white/5 p-3"
              >
                <span className="min-w-0 truncate text-sm font-bold">{item.vehicle_name ?? item.vehicle_key}</span>
                <button
                  onClick={() => removeMutation.mutate(item.id)}
                  className="grid h-8 w-8 shrink-0 place-items-center rounded-md bg-rose-500/15 text-rose-100 hover:bg-rose-500"
                >
                  <Trash2 size={15} />
                </button>
              </div>
            ))}
          </div>
        </section>

        <section className="glass-panel flex min-h-0 flex-col overflow-hidden rounded-xl">
          <div className="flex items-center justify-between gap-3 border-b border-white/10 p-4">
            <div>
              <div className="font-black">آگهی‌های مدل‌های خاص</div>
              <div className="mt-1 text-xs text-slate-400">{formatCount(ads.length)} آگهی</div>
            </div>
            <div className="flex h-9 shrink-0 overflow-hidden rounded-lg bg-white/10 text-xs font-black">
              <button
                onClick={() => setDay("today")}
                className={["h-full px-3 transition", day === "today" ? "bg-white text-slate-950" : "hover:bg-white/10"].join(" ")}
              >
                امروز
              </button>
              <button
                onClick={() => setDay("yesterday")}
                className={["h-full px-3 transition", day === "yesterday" ? "bg-white text-slate-950" : "hover:bg-white/10"].join(" ")}
              >
                دیروز
              </button>
            </div>
          </div>
          <div className="min-h-0 flex-1 overflow-auto scroll-area">
            {isLoading ? (
              <div className="grid h-full place-items-center text-slate-400">در حال بارگذاری...</div>
            ) : watched.length === 0 ? (
              <div className="grid h-full place-items-center px-6 text-center text-sm text-slate-400">
                اول از سمت چپ یک یا چند مدل خودرو اضافه کن
              </div>
            ) : ads.length === 0 ? (
              <div className="grid h-full place-items-center text-slate-400">هنوز آگهی‌ای برای این مدل‌ها پیدا نشده</div>
            ) : (
              <table className="w-full min-w-[760px] text-sm">
                <thead className="sticky top-0 bg-slate-950/95 text-slate-400">
                  <tr>
                    <th className="border-b border-white/10 px-4 py-3 text-right">خودرو</th>
                    <th className="border-b border-white/10 px-4 py-3 text-right">قیمت</th>
                    <th className="border-b border-white/10 px-4 py-3 text-right">رنگ</th>
                    <th className="border-b border-white/10 px-4 py-3 text-right">کانال</th>
                    <th className="border-b border-white/10 px-4 py-3 text-right">تاریخ</th>
                  </tr>
                </thead>
                <tbody>
                  {ads.map((ad) => (
                    <tr
                      key={ad.id}
                      onClick={() => setSelectedAdId(ad.id)}
                      className="cursor-pointer transition hover:bg-white/5"
                    >
                      <td className="border-b border-white/10 px-4 py-3 font-bold">{ad.vehicle_name ?? "نامشخص"}</td>
                      <td className="border-b border-white/10 px-4 py-3 font-black text-cyan-100">
                        {ad.price_million ? `${formatNumber(ad.price_million)} میلیون` : "بدون قیمت"}
                      </td>
                      <td className="border-b border-white/10 px-4 py-3">{ad.color ?? "-"}</td>
                      <td className="border-b border-white/10 px-4 py-3">
                        {ad.channel_username ? `@${ad.channel_username}` : "-"}
                      </td>
                      <td className="border-b border-white/10 px-4 py-3 text-slate-300">
                        <span className="flex items-center gap-1">
                          {formatDateTime(ad.message_date)}
                          <ExternalLink size={13} className="opacity-50" />
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </section>
      </div>

      {selectedAdId && <AdDetailModal adId={selectedAdId} onClose={() => setSelectedAdId(undefined)} />}
    </>
  );
}
