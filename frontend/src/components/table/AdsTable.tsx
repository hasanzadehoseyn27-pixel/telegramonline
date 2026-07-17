import { motion } from "framer-motion";
import { ChevronLeft, ChevronRight, ExternalLink, Search } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useAds } from "../../hooks/useAds";
import { useAdsStore } from "../../store/adsStore";
import type { Ad } from "../../api/ads.api";
import AdDetailModal from "../modal/AdDetailModal";
import { formatCount, formatDateTime, formatNumber, telegramLink } from "../../utils/format";

const headers = ["خودرو", "قیمت", "مدل", "رنگ", "کارکرد", "تلفن", "کانال", "تاریخ و ساعت"];

function isInsideTimeRange(ad: Ad, hours?: number) {
  if (!hours || hours >= 24 || !ad.message_date) {
    return true;
  }

  const time = new Date(ad.message_date).getTime();
  if (Number.isNaN(time)) {
    return true;
  }

  return Date.now() - time <= hours * 60 * 60 * 1000;
}

export default function AdsTable() {
  const { activeTab, filters, setFilters } = useAdsStore();
  const { data, isLoading, isError } = useAds(activeTab, filters);
  const [selectedAdId, setSelectedAdId] = useState<number>();

  const ads: Ad[] = useMemo(
    () => (data?.items ?? []).filter((ad) => isInsideTimeRange(ad, filters.timeRange)),
    [data?.items, filters.timeRange],
  );

  const pageSize = filters.limit ?? 50;
  const offset = filters.offset ?? 0;
  const total = data?.total ?? 0;
  const pageCount = Math.max(1, Math.ceil(total / pageSize));
  const currentPage = Math.floor(offset / pageSize) + 1;

  // اگه بعد از سرچ/فیلتر جدید، صفحه‌ی فعلی دیگه در محدوده‌ی نتایج نباشه
  // (مثلاً روی صفحه ۵ بودیم و نتایج جدید فقط ۲ صفحه شدن)، برگرد صفحه‌ی اول
  // به‌جای ماندن روی یک صفحه‌ی خالی با نوار صفحه‌بندی گمشده.
  useEffect(() => {
    if (total > 0 && offset >= total) {
      setFilters({ offset: 0 });
    }
  }, [total, offset, setFilters]);

  if (isLoading) {
    return (
      <div className="glass-panel grid h-full place-items-center rounded-xl">
        <div className="space-y-3 text-center">
          <div className="mx-auto h-11 w-11 animate-spin rounded-full border-2 border-cyan-300 border-t-transparent" />
          <div className="text-sm text-slate-300">در حال دریافت آگهی‌ها...</div>
        </div>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="grid h-full place-items-center rounded-xl border border-rose-400/30 bg-rose-500/10 text-rose-100">
        خطا در دریافت آگهی‌ها
      </div>
    );
  }

  return (
    <div className="flex h-full min-h-0 flex-col gap-3">
      <div className="glass-panel flex min-h-0 flex-1 flex-col overflow-hidden rounded-xl">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/10 px-3 py-3 sm:px-4">
          <div>
            <div className="text-sm font-black">جدول آگهی‌های امروز</div>
            <div className="mt-1 text-xs text-slate-400">
              {formatCount(ads.length)} از {formatCount(total)} ردیف از داده‌های همان روز
            </div>
          </div>
          <div className="flex min-w-0 flex-1 items-center justify-end gap-2 max-sm:w-full max-sm:flex-none">
            <div className="flex h-10 min-w-0 flex-1 items-center gap-2 rounded-xl border border-white/10 bg-slate-950/70 px-3 sm:max-w-sm">
              <Search size={17} className="shrink-0 text-slate-500" />
              <input
                value={filters.search ?? ""}
                onChange={(event) => setFilters({ search: event.target.value })}
                className="min-w-0 flex-1 bg-transparent text-sm outline-none"
                placeholder="جستجو در جدول..."
              />
            </div>
            <select
              value={filters.sort ?? "newest"}
              onChange={(event) => setFilters({ sort: event.target.value as typeof filters.sort })}
              className="h-10 rounded-xl border border-white/10 bg-slate-950/70 px-2 text-xs font-bold outline-none sm:px-3"
            >
              <option value="newest">جدیدترین</option>
              <option value="oldest">قدیمی‌ترین</option>
              <option value="price_asc">ارزان‌ترین</option>
              <option value="price_desc">گران‌ترین</option>
              <option value="year_desc">مدل بالاتر</option>
              <option value="mileage_asc">کارکرد کمتر</option>
            </select>
            <div className="hidden rounded-full border border-cyan-300/20 bg-cyan-300/10 px-3 py-1 text-xs font-bold text-cyan-100 sm:block">
              زنده
            </div>
          </div>
        </div>

        <div className="min-h-0 flex-1 overflow-auto scroll-area">
          <table className="w-full min-w-[760px] border-separate border-spacing-0 text-sm">
            <thead className="sticky top-0 z-10 bg-slate-950/95 backdrop-blur">
              <tr className="text-slate-400">
                {headers.map((header) => (
                  <th key={header} className="whitespace-nowrap border-b border-white/10 px-4 py-3 text-right font-bold">
                    {header}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {ads.length === 0 ? (
                <tr>
                  <td colSpan={headers.length} className="px-4 py-16 text-center text-slate-400">
                    آگهی مطابق فیلترها پیدا نشد
                  </td>
                </tr>
              ) : (
                ads.map((ad, index) => {
                  const link = ad.telegram_link ?? telegramLink(ad.channel_username, ad.source_message_id);
                  return (
                    <motion.tr
                      key={ad.id}
                      initial={{ opacity: 0, y: 8 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: Math.min(index * 0.015, 0.22) }}
                      onClick={() => setSelectedAdId(ad.id)}
                      className="cursor-pointer border-b border-white/10 transition hover:bg-white/[0.07]"
                    >
                      <td className="whitespace-nowrap border-b border-white/10 px-4 py-3 font-bold text-white">
                        {ad.vehicle_name ?? "نامشخص"}
                      </td>
                      <td className="whitespace-nowrap border-b border-white/10 px-4 py-3 font-black text-cyan-200">
                        {ad.price_million ? `${formatNumber(ad.price_million)} میلیون` : "بدون قیمت"}
                      </td>
                      <td className="whitespace-nowrap border-b border-white/10 px-4 py-3 text-slate-200">{ad.year ?? "-"}</td>
                      <td className="whitespace-nowrap border-b border-white/10 px-4 py-3 text-slate-200">{ad.color ?? "-"}</td>
                      <td className="whitespace-nowrap border-b border-white/10 px-4 py-3 text-slate-200">
                        {ad.mileage_km ? `${formatNumber(ad.mileage_km)} km` : "-"}
                      </td>
                      <td className="whitespace-nowrap border-b border-white/10 px-4 py-3 text-slate-200">{ad.phone ?? "-"}</td>
                      <td className="whitespace-nowrap border-b border-white/10 px-4 py-3">
                        {link ? (
                          <a
                            href={link}
                            target="_blank"
                            rel="noreferrer"
                            onClick={(event) => event.stopPropagation()}
                            className="inline-flex items-center gap-1 rounded-full bg-white/10 px-2 py-1 text-xs text-cyan-100 transition hover:bg-cyan-300 hover:text-slate-950"
                          >
                            @{ad.channel_username}
                            <ExternalLink size={13} />
                          </a>
                        ) : (
                          "-"
                        )}
                      </td>
                      <td className="whitespace-nowrap border-b border-white/10 px-4 py-3 text-slate-300">
                        {formatDateTime(ad.message_date)}
                      </td>
                    </motion.tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {pageCount > 1 && (
        <div className="glass-panel flex shrink-0 flex-wrap items-center justify-center gap-2 rounded-xl p-2.5 sm:justify-between sm:gap-3 sm:p-3">
          <button
            type="button"
            onClick={() => setFilters({ offset: Math.max(0, offset - pageSize) })}
            disabled={currentPage <= 1}
            className="flex shrink-0 items-center gap-1 rounded-xl bg-white/10 px-2.5 py-2 text-xs font-bold transition sm:px-3 sm:text-sm hover:bg-white hover:text-slate-950 disabled:opacity-40 disabled:hover:bg-white/10 disabled:hover:text-inherit"
          >
            <ChevronRight size={16} />
            قبلی
          </button>
          <div className="text-sm text-slate-400">
            صفحه {formatCount(currentPage)} از {formatCount(pageCount)}
          </div>
          <button
            type="button"
            onClick={() => setFilters({ offset: Math.min((pageCount - 1) * pageSize, offset + pageSize) })}
            disabled={currentPage >= pageCount}
            className="flex shrink-0 items-center gap-1 rounded-xl bg-white/10 px-2.5 py-2 text-xs font-bold transition sm:px-3 sm:text-sm hover:bg-white hover:text-slate-950 disabled:opacity-40 disabled:hover:bg-white/10 disabled:hover:text-inherit"
          >
            بعدی
            <ChevronLeft size={16} />
          </button>
        </div>
      )}

      {selectedAdId && <AdDetailModal adId={selectedAdId} onClose={() => setSelectedAdId(undefined)} />}
    </div>
  );
}
