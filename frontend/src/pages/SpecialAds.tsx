import { ExternalLink, Plus, Sparkles, Trash2 } from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import {
  addWatchedVehicle,
  getSpecialAds,
  getWatchedVehicles,
  removeWatchedVehicle,
} from "../api/watchedVehicles.api";
import { getFilterOptions } from "../api/filters.api";
import AdDetailModal from "../components/modal/AdDetailModal";
import { formatCount, formatDateTime, formatNumber } from "../utils/format";

export default function SpecialAds() {
  const [vehicleKey, setVehicleKey] = useState("");
  const [selectedAdId, setSelectedAdId] = useState<number>();
  const queryClient = useQueryClient();

  const { data: filterOptions } = useQuery({
    queryKey: ["filters", "options"],
    queryFn: getFilterOptions,
  });

  const { data: watched = [] } = useQuery({
    queryKey: ["watched-vehicles"],
    queryFn: getWatchedVehicles,
    refetchInterval: 5000,
  });

  const { data: adsPage, isLoading } = useQuery({
    queryKey: ["watched-vehicles", "ads"],
    queryFn: () => getSpecialAds(50, 0),
    refetchInterval: 5000,
  });

  const addMutation = useMutation({
    mutationFn: addWatchedVehicle,
    onSuccess: () => {
      setVehicleKey("");
      queryClient.invalidateQueries({ queryKey: ["watched-vehicles"] });
    },
  });

  const removeMutation = useMutation({
    mutationFn: removeWatchedVehicle,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["watched-vehicles"] }),
  });

  function submit() {
    if (!vehicleKey) return;
    const vehicle = filterOptions?.vehicles.find((v) => v.key === vehicleKey);
    addMutation.mutate({ vehicle_key: vehicleKey, vehicle_name: vehicle?.name });
  }

  const ads = adsPage?.items ?? [];

  return (
    <>
      <div className="grid h-full min-h-0 grid-cols-[340px_minmax(0,1fr)] gap-4 max-xl:grid-cols-1">
        <section className="glass-panel min-h-0 overflow-y-auto rounded-xl p-4 scroll-area">
          <div className="mb-4 flex items-center gap-2 text-xl font-black">
            <Sparkles className="text-cyan-200" />
            آگهی‌های خاص
          </div>
          <p className="mb-4 text-xs leading-6 text-slate-400 theme-muted">
            فقط مدل‌هایی که اینجا اضافه می‌کنی (و مشتقات همون مدل) توی لیست کنار نشون داده می‌شن؛ بقیه‌ی آگهی‌ها
            مخفی می‌مونن.
          </p>

          <div className="space-y-2">
            <select
              value={vehicleKey}
              onChange={(event) => setVehicleKey(event.target.value)}
              className="h-11 w-full rounded-lg border border-white/10 bg-slate-950/70 px-3 text-sm outline-none"
            >
              <option value="">انتخاب مدل</option>
              {(filterOptions?.vehicles ?? []).map((vehicle) => (
                <option key={vehicle.key} value={vehicle.key}>
                  {vehicle.name}
                </option>
              ))}
            </select>
            <button
              onClick={submit}
              disabled={!vehicleKey || addMutation.isPending}
              className="flex h-11 w-full items-center justify-center gap-2 rounded-lg bg-cyan-300 font-black text-slate-950 transition hover:bg-white disabled:opacity-50"
            >
              <Plus size={17} />
              اضافه کردن به لیست خاص
            </button>
          </div>

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
          <div className="border-b border-white/10 p-4">
            <div className="font-black">آگهی‌های مدل‌های خاص</div>
            <div className="mt-1 text-xs text-slate-400">{formatCount(ads.length)} آگهی امروز</div>
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
