import { ChevronLeft, ChevronRight, ExternalLink, Search, Sparkles } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { getPricedAds, type Ad } from "../api/ads.api";
import { CURATED_VEHICLES } from "../data/curatedVehicles";
import AdDetailModal from "../components/modal/AdDetailModal";
import AdsFilters from "../components/filters/AdsFilters";
import FiltersDrawer, { FiltersToggleButton } from "../components/filters/FiltersDrawer";
import { useAdsStore } from "../store/adsStore";
import { formatCount, formatDateTime, formatNumber } from "../utils/format";

const PAGE_SIZE = 50;
const ALL_KEYS = CURATED_VEHICLES.map((v) => v.key);

function isInsideTimeRange(ad: Ad, hours?: number) {
  if (!hours || hours >= 24 || !ad.message_date) return true;
  const time = new Date(ad.message_date).getTime();
  if (Number.isNaN(time)) return true;
  return Date.now() - time <= hours * 60 * 60 * 1000;
}

export default function SpecialAds() {
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(0);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [selectedAdId, setSelectedAdId] = useState<number>();
  const { filters, setFilters } = useAdsStore();
  const day = filters.day ?? "today";

  const effectiveVehicleKeys = useMemo(() => {
    if (!filters.vehicleKeys?.length) return ALL_KEYS;
    const narrowed = filters.vehicleKeys.filter((k) => ALL_KEYS.includes(k));
    return narrowed.length > 0 ? narrowed : ALL_KEYS;
  }, [filters.vehicleKeys]);

  const { data: adsPage, isLoading } = useQuery({
    queryKey: ["special-ads", day, page, filters.search, filters.minPrice, filters.maxPrice, filters.maxMileage, effectiveVehicleKeys],
    queryFn: () =>
      getPricedAds({
        vehicleKeys: effectiveVehicleKeys,
        day,
        search: filters.search || undefined,
        minPrice: filters.minPrice,
        maxPrice: filters.maxPrice,
        maxMileage: filters.maxMileage,
        limit: PAGE_SIZE,
        offset: page * PAGE_SIZE,
      }),
    refetchInterval: 5000,
  });

  const ads = useMemo(
    () => (adsPage?.items ?? []).filter((ad) => isInsideTimeRange(ad, filters.timeRange)),
    [adsPage?.items, filters.timeRange],
  );
  const total = adsPage?.total ?? 0;
  const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE));

  useEffect(() => {
    if (total > 0 && page * PAGE_SIZE >= total) {
      setPage(0);
    }
  }, [total, page]);

  const referenceList = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    if (!normalized) return CURATED_VEHICLES;
    return CURATED_VEHICLES.filter((v) => v.name.toLowerCase().includes(normalized));
  }, [query]);

  return (
    <>
      <div className="flex h-[calc(100vh-170px)] max-sm:h-[calc(100vh-250px)] min-h-0 gap-4 max-xl:flex-col">
        <section className="glass-panel flex h-full min-h-0 w-72 shrink-0 flex-col overflow-hidden rounded-xl p-4 max-xl:h-64 max-xl:w-full">
          <div className="mb-1 flex items-center gap-2 text-xl font-black">
            <Sparkles className="text-cyan-200" />
            آگهی‌های خاص
          </div>
          <p className="mb-3 text-xs leading-6 text-slate-400 theme-muted">
            فهرست {formatCount(CURATED_VEHICLES.length)} مدلی که پارسر برایشان تضمین‌شده — جدول کنار همیشه فقط
            آگهی‌های همین‌ها را نشان می‌دهد.
          </p>

          <div className="flex h-11 shrink-0 items-center gap-2 rounded-lg border border-white/10 bg-slate-950/70 px-3">
            <Search size={16} className="shrink-0 text-slate-500" />
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="جستجو در لیست (مثلاً: پانا ارتقا)"
              className="min-w-0 flex-1 bg-transparent text-sm outline-none"
            />
          </div>

          <div className="mt-3 min-h-0 flex-1 space-y-1.5 overflow-y-auto pl-1 scroll-area">
            {referenceList.length === 0 ? (
              <div className="p-3 text-center text-xs text-slate-400">موردی پیدا نشد</div>
            ) : (
              referenceList.map((v) => (
                <div
                  key={v.key}
                  className="truncate rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm font-bold"
                  title={v.name}
                >
                  {v.name}
                </div>
              ))
            )}
          </div>
        </section>

        <div className="flex h-full min-h-0 min-w-0 flex-1 flex-col gap-3">
          <div className="flex min-h-0 flex-1 gap-0">
            <section className="glass-panel flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden rounded-xl">
              <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/10 p-4">
                <div>
                  <div className="font-black">آگهی‌های مدل‌های خاص</div>
                  <div className="mt-1 text-xs text-slate-400">
                    {formatCount(ads.length)} از {formatCount(total)} آگهی
                  </div>
                </div>
                <div className="flex h-9 min-w-0 flex-1 items-center gap-2 rounded-lg border border-white/10 bg-slate-950/70 px-3 sm:max-w-64">
                  <Search size={14} className="shrink-0 text-slate-500" />
                  <input
                    value={filters.search ?? ""}
                    onChange={(event) => setFilters({ search: event.target.value })}
                    placeholder="جستجو در همین جدول..."
                    className="min-w-0 flex-1 bg-transparent text-xs outline-none"
                  />
                </div>
                <FiltersToggleButton open={filtersOpen} onClick={() => setFiltersOpen((v) => !v)} />
              </div>
              <div className="min-h-0 flex-1 overflow-auto scroll-area">
                {isLoading ? (
                  <div className="grid h-full place-items-center text-slate-400">در حال بارگذاری...</div>
                ) : ads.length === 0 ? (
                  <div className="grid h-full place-items-center text-slate-400">هنوز آگهی‌ای برای این مدل‌ها پیدا نشده</div>
                ) : (
                  <table className="w-full min-w-[760px] text-sm">
                    <thead className="sticky top-0 bg-slate-950 text-slate-400">
                      <tr>
                        <th className="whitespace-nowrap border-b border-white/10 px-4 py-3 text-right">خودرو</th>
                        <th className="whitespace-nowrap border-b border-white/10 px-4 py-3 text-right">قیمت</th>
                        <th className="whitespace-nowrap border-b border-white/10 px-4 py-3 text-right">رنگ</th>
                        <th className="whitespace-nowrap border-b border-white/10 px-4 py-3 text-right">کانال</th>
                        <th className="whitespace-nowrap border-b border-white/10 px-4 py-3 text-right">تاریخ</th>
                      </tr>
                    </thead>
                    <tbody>
                      {ads.map((ad) => (
                        <tr
                          key={ad.id}
                          onClick={() => setSelectedAdId(ad.id)}
                          className="cursor-pointer transition hover:bg-white/5"
                        >
                          <td className="whitespace-nowrap border-b border-white/10 px-4 py-3 font-bold">{ad.vehicle_name ?? "نامشخص"}</td>
                          <td className="whitespace-nowrap border-b border-white/10 px-4 py-3 font-black text-cyan-100">
                            {ad.price_million ? `${formatNumber(ad.price_million)} میلیون` : "بدون قیمت"}
                          </td>
                          <td className="whitespace-nowrap border-b border-white/10 px-4 py-3">{ad.color ?? "-"}</td>
                          <td className="whitespace-nowrap border-b border-white/10 px-4 py-3">
                            {ad.channel_username ? `@${ad.channel_username}` : "-"}
                          </td>
                          <td className="whitespace-nowrap border-b border-white/10 px-4 py-3 text-slate-300">
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
            <FiltersDrawer open={filtersOpen} onClose={() => setFiltersOpen(false)}>
              <AdsFilters />
            </FiltersDrawer>
          </div>

          {pageCount > 1 && (
            <div className="glass-panel flex shrink-0 items-center justify-between gap-3 rounded-xl p-3">
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
      </div>

      {selectedAdId && <AdDetailModal adId={selectedAdId} onClose={() => setSelectedAdId(undefined)} />}
    </>
  );
}
