import { Bell, ExternalLink, Plus, Trash2 } from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { createAlert, getAlertEvents, getAlerts, removeAlert, toggleAlert } from "../api/alerts.api";
import { getFilterOptions } from "../api/filters.api";
import FormattedNumberInput from "../components/common/FormattedNumberInput";
import { formatDateTime, formatNumber } from "../utils/format";

type Condition = "lt" | "gt" | "between";

export default function Alerts() {
  const [vehicleKey, setVehicleKey] = useState("");
  const [condition, setCondition] = useState<Condition>("lt");
  const [minPrice, setMinPrice] = useState<number>();
  const [maxPrice, setMaxPrice] = useState<number>();
  const queryClient = useQueryClient();

  const { data: filterOptions } = useQuery({
    queryKey: ["filters", "options"],
    queryFn: getFilterOptions,
  });
  const { data: alerts = [] } = useQuery({
    queryKey: ["alerts", "list"],
    queryFn: () => getAlerts(1),
    refetchInterval: 5000,
  });
  const { data: events = [] } = useQuery({
    queryKey: ["alert-events"],
    queryFn: getAlertEvents,
    refetchInterval: 5000,
  });

  const selectedVehicle = useMemo(
    () => filterOptions?.vehicles.find((vehicle) => vehicle.key === vehicleKey),
    [filterOptions?.vehicles, vehicleKey],
  );

  const createMutation = useMutation({
    mutationFn: createAlert,
    onSuccess: () => {
      setMinPrice(undefined);
      setMaxPrice(undefined);
      queryClient.invalidateQueries({ queryKey: ["alerts"] });
    },
  });

  const removeMutation = useMutation({
    mutationFn: removeAlert,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["alerts"] }),
  });

  const toggleMutation = useMutation({
    mutationFn: toggleAlert,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["alerts"] }),
  });

  function submit() {
    if (!vehicleKey) {
      return;
    }

    createMutation.mutate({
      user_id: 1,
      vehicle_key: vehicleKey,
      vehicle_name: selectedVehicle?.name,
      condition,
      min_price: condition === "gt" || condition === "between" ? minPrice : undefined,
      max_price: condition === "lt" || condition === "between" ? maxPrice : undefined,
    });
  }

  return (
    <div className="grid h-full min-h-0 grid-cols-[360px_minmax(0,1fr)] gap-4 max-xl:grid-cols-1">
      <section className="glass-panel rounded-xl p-4">
        <div className="mb-4 flex items-center gap-2 text-xl font-black">
          <Bell className="text-rose-200" />
          هشدار قیمت
        </div>

        <div className="space-y-4">
          <label className="block">
            <span className="text-xs font-semibold text-slate-400">مدل خودرو</span>
            <select
              value={vehicleKey}
              onChange={(event) => setVehicleKey(event.target.value)}
              className="mt-2 h-11 w-full rounded-lg border border-white/10 bg-slate-950/70 px-3 text-sm outline-none"
            >
              <option value="">انتخاب مدل</option>
              {(filterOptions?.vehicles ?? []).map((vehicle) => (
                <option key={vehicle.key} value={vehicle.key}>
                  {vehicle.name}
                </option>
              ))}
            </select>
          </label>

          <div>
            <span className="text-xs font-semibold text-slate-400">نوع هشدار</span>
            <div className="mt-2 grid grid-cols-3 gap-1 rounded-lg bg-slate-950/70 p-1">
              {[
                ["lt", "کمتر از"],
                ["gt", "بیشتر از"],
                ["between", "بین دو قیمت"],
              ].map(([value, label]) => (
                <button
                  key={value}
                  onClick={() => setCondition(value as Condition)}
                  className={[
                    "h-9 rounded-md text-xs font-black transition",
                    condition === value ? "bg-rose-400 text-white" : "hover:bg-white/10",
                  ].join(" ")}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>

          {(condition === "gt" || condition === "between") && (
            <FormattedNumberInput label="حداقل قیمت" value={minPrice} suffix="میلیون" onChange={setMinPrice} />
          )}
          {(condition === "lt" || condition === "between") && (
            <FormattedNumberInput label="حداکثر قیمت" value={maxPrice} suffix="میلیون" onChange={setMaxPrice} />
          )}

          <button
            onClick={submit}
            disabled={!vehicleKey || createMutation.isPending}
            className="flex h-11 w-full items-center justify-center gap-2 rounded-lg bg-rose-400 font-black text-white transition hover:bg-white hover:text-slate-950 disabled:opacity-50"
          >
            <Plus size={17} />
            ثبت هشدار
          </button>
        </div>

        <div className="mt-6 space-y-2">
          {alerts.map((alert) => (
            <div key={alert.id} className="rounded-lg border border-white/10 bg-white/5 p-3">
              <div className="flex items-center justify-between">
                <div className="font-bold">{alert.vehicle_name ?? alert.vehicle_key}</div>
                <button
                  onClick={() => removeMutation.mutate(alert.id)}
                  className="grid h-8 w-8 place-items-center rounded-md bg-rose-500/15 text-rose-100 hover:bg-rose-500"
                >
                  <Trash2 size={15} />
                </button>
              </div>
              <button
                onClick={() => toggleMutation.mutate(alert.id)}
                className="mt-2 rounded-full bg-white/10 px-2 py-1 text-xs text-slate-300 hover:bg-white/20"
              >
                {alert.active ? "فعال" : "غیرفعال"}
              </button>
            </div>
          ))}
        </div>
      </section>

      <section className="glass-panel min-h-0 overflow-hidden rounded-xl">
        <div className="border-b border-white/10 p-4">
          <div className="font-black">رویدادهای پیدا شده</div>
          <div className="mt-1 text-xs text-slate-400">{formatNumber(events.length)} هشدار اخیر</div>
        </div>
        <div className="h-full overflow-auto pb-20 scroll-area">
          <table className="w-full min-w-[820px] text-sm">
            <thead className="sticky top-0 bg-slate-950/95 text-slate-400">
              <tr>
                <th className="border-b border-white/10 px-4 py-3 text-right">خودرو</th>
                <th className="border-b border-white/10 px-4 py-3 text-right">قیمت</th>
                <th className="border-b border-white/10 px-4 py-3 text-right">کانال</th>
                <th className="border-b border-white/10 px-4 py-3 text-right">تاریخ</th>
                <th className="border-b border-white/10 px-4 py-3 text-right">تلگرام</th>
              </tr>
            </thead>
            <tbody>
              {events.map((event) => (
                <tr key={event.id} className="hover:bg-white/5">
                  <td className="border-b border-white/10 px-4 py-3 font-bold">
                    {event.vehicle_name ?? event.vehicle_key ?? "-"}
                  </td>
                  <td className="border-b border-white/10 px-4 py-3 font-black text-rose-100">
                    {event.price_million ? `${formatNumber(event.price_million)} میلیون` : "-"}
                  </td>
                  <td className="border-b border-white/10 px-4 py-3">
                    {event.channel_username ? `@${event.channel_username}` : "-"}
                  </td>
                  <td className="border-b border-white/10 px-4 py-3 text-slate-300">
                    {formatDateTime(event.created_at)}
                  </td>
                  <td className="border-b border-white/10 px-4 py-3">
                    {event.telegram_link && (
                      <a href={event.telegram_link} target="_blank" rel="noreferrer" className="text-cyan-100">
                        <ExternalLink size={18} />
                      </a>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
