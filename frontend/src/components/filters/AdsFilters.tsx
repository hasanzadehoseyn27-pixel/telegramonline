import { Search, SlidersHorizontal, X } from "lucide-react";
import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getFilterOptions } from "../../api/filters.api";
import { useAdsStore } from "../../store/adsStore";
import FormattedNumberInput from "../common/FormattedNumberInput";
import { formatNumber } from "../../utils/format";

const ranges = [1, 3, 6, 12, 24];

export default function AdsFilters() {
  const [vehicleSearch, setVehicleSearch] = useState("");
  const { filters, setFilters, resetFilters, toggleVehicle } = useAdsStore();
  const { data } = useQuery({
    queryKey: ["filters", "options"],
    queryFn: getFilterOptions,
    refetchInterval: 5000,
  });

  const selectedVehicles = filters.vehicleKeys ?? [];
  const vehicles = useMemo(() => {
    const normalized = vehicleSearch.trim().toLowerCase();
    return (data?.vehicles ?? []).filter((vehicle) => {
      if (!normalized) {
        return true;
      }
      return vehicle.name.toLowerCase().includes(normalized) || vehicle.key.toLowerCase().includes(normalized);
    });
  }, [data?.vehicles, vehicleSearch]);

  return (
    <aside className="glass-panel flex h-full min-h-0 flex-col rounded-xl p-4">
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2 font-black">
          <SlidersHorizontal size={18} />
          فیلترها
        </div>
        <button
          onClick={resetFilters}
          className="flex items-center gap-1 rounded-md px-2 py-1 text-xs text-rose-200 transition hover:bg-rose-500/15"
        >
          <X size={14} />
          پاک کردن
        </button>
      </div>

      <div className="space-y-2.5 overflow-y-auto pl-1 scroll-area">
        <label className="block">
          <span className="text-xs font-semibold text-slate-400">جستجو</span>
          <div className="mt-2 flex h-11 items-center gap-2 rounded-lg border border-white/10 bg-slate-950/70 px-3">
            <Search size={17} className="text-slate-500" />
            <input
              value={filters.search ?? ""}
              onChange={(event) => setFilters({ search: event.target.value })}
              className="h-full min-w-0 flex-1 bg-transparent text-sm outline-none"
              placeholder="نام خودرو، رنگ، متن آگهی..."
            />
          </div>
        </label>

        <div>
          <span className="text-xs font-semibold text-slate-400">بازه زمانی</span>
          <div className="mt-2 grid grid-cols-5 gap-1 rounded-lg bg-slate-950/70 p-1">
            {ranges.map((range) => (
              <button
                key={range}
                onClick={() => setFilters({ timeRange: range })}
                className={[
                  "h-9 rounded-md text-xs font-bold transition",
                  filters.timeRange === range
                    ? "bg-cyan-300 text-slate-950"
                    : "text-slate-300 hover:bg-white/10",
                ].join(" ")}
              >
                {formatNumber(range)}س
              </button>
            ))}
          </div>
        </div>

        <FormattedNumberInput
          label="حداقل قیمت"
          value={filters.minPrice}
          suffix="میلیون"
          placeholder="مثلا 1,500"
          onChange={(value) => setFilters({ minPrice: value })}
        />

        <FormattedNumberInput
          label="حداکثر قیمت"
          value={filters.maxPrice}
          suffix="میلیون"
          placeholder="مثلا 2,500"
          onChange={(value) => setFilters({ maxPrice: value })}
        />

        <FormattedNumberInput
          label="حداکثر کارکرد"
          value={filters.maxMileage}
          suffix="کیلومتر"
          placeholder="مثلا 50,000"
          onChange={(value) => setFilters({ maxMileage: value })}
        />

        <div>
          <span className="text-xs font-semibold text-slate-400">مدل خودرو</span>
          <input
            value={vehicleSearch}
            onChange={(event) => setVehicleSearch(event.target.value)}
            className="mt-2 h-10 w-full rounded-lg border border-white/10 bg-slate-950/70 px-3 text-sm outline-none transition focus:border-cyan-300/60"
            placeholder="جستجوی مدل..."
          />
          <div className="mt-2 max-h-64 space-y-1 overflow-y-auto pr-1 scroll-area">
            {vehicles.map((vehicle) => (
              <label
                key={vehicle.key}
                className="flex items-center justify-between gap-2 rounded-lg px-2 py-2 text-sm transition hover:bg-white/5"
              >
                <span className="flex min-w-0 items-center gap-2">
                  <input
                    type="checkbox"
                    checked={selectedVehicles.includes(vehicle.key)}
                    onChange={() => toggleVehicle(vehicle.key)}
                    className="h-4 w-4 accent-cyan-300"
                  />
                  <span className="truncate">{vehicle.name}</span>
                </span>
                <span className="rounded-full bg-white/10 px-2 py-0.5 text-xs text-slate-300">
                  {formatNumber(vehicle.count)}
                </span>
              </label>
            ))}
          </div>
        </div>
      </div>
    </aside>
  );
}
