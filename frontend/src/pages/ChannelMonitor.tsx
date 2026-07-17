import { Car, Radio, Sparkles } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { getChannelActivity } from "../api/channelMonitor.api";
import { CURATED_VEHICLES } from "../data/curatedVehicles";
import { formatCount } from "../utils/format";

const CURATED_KEYS = CURATED_VEHICLES.map((v) => v.key);

export default function ChannelMonitor() {
  const [tab, setTab] = useState<"all" | "special">("all");
  const [day, setDay] = useState<"today" | "yesterday">("today");

  const { data = [], isLoading } = useQuery({
    queryKey: ["channel-monitor", tab, day],
    queryFn: () => getChannelActivity(day, tab === "special" ? CURATED_KEYS : undefined),
    refetchInterval: 5000,
  });

  const { channels, groups, totalChannels, totalGroups } = useMemo(() => {
    const channels = data.filter((d) => d.type === "channel");
    const groups = data.filter((d) => d.type === "group");
    return {
      channels,
      groups,
      totalChannels: channels.reduce((sum, c) => sum + c.car_ads, 0),
      totalGroups: groups.reduce((sum, g) => sum + g.car_ads, 0),
    };
  }, [data]);

  return (
    <div className="flex h-full min-h-0 flex-col gap-4">
      <div className="glass-panel flex flex-wrap items-center justify-between gap-3 rounded-2xl p-4">
        <div>
          <div className="flex items-center gap-2 text-xl font-black">
            <Radio className="text-cyan-200" />
            مانیتور زنده کانال‌ها و گروه‌ها
          </div>
          <div className="mt-1 text-sm text-slate-400 theme-muted">
            تعداد پیام‌های خودرویی غیرتکراری هر کانال/گروه، از نیمه‌شب تا همین لحظه
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <div className="flex h-10 overflow-hidden rounded-xl bg-white/10 text-sm font-black">
            <button
              onClick={() => setTab("all")}
              className={["flex h-full items-center gap-1.5 px-4 transition", tab === "all" ? "bg-white text-slate-950" : "hover:bg-white/10"].join(" ")}
            >
              <Car size={15} />
              همه آگهی‌ها
            </button>
            <button
              onClick={() => setTab("special")}
              className={["flex h-full items-center gap-1.5 px-4 transition", tab === "special" ? "bg-white text-slate-950" : "hover:bg-white/10"].join(" ")}
            >
              <Sparkles size={15} />
              آگهی‌های خاص
            </button>
          </div>
          <div className="flex h-10 overflow-hidden rounded-xl bg-white/10 text-sm font-black">
            <button
              onClick={() => setDay("today")}
              className={["h-full px-4 transition", day === "today" ? "bg-cyan-300 text-slate-950" : "hover:bg-white/10"].join(" ")}
            >
              امروز
            </button>
            <button
              onClick={() => setDay("yesterday")}
              className={["h-full px-4 transition", day === "yesterday" ? "bg-cyan-300 text-slate-950" : "hover:bg-white/10"].join(" ")}
            >
              دیروز
            </button>
          </div>
        </div>
      </div>

      <div className="grid min-h-0 flex-1 grid-cols-2 gap-4 max-lg:grid-cols-1">
        <ActivityColumn title="کانال‌ها" total={totalChannels} rows={channels} isLoading={isLoading} />
        <ActivityColumn title="گروه‌ها" total={totalGroups} rows={groups} isLoading={isLoading} />
      </div>
    </div>
  );
}

function ActivityColumn({
  title,
  total,
  rows,
  isLoading,
}: {
  title: string;
  total: number;
  rows: { username: string; title: string | null; car_ads: number; active: boolean }[];
  isLoading: boolean;
}) {
  return (
    <section className="glass-panel flex min-h-0 min-w-0 flex-col overflow-hidden rounded-2xl">
      <div className="flex items-center justify-between gap-2 border-b border-white/10 p-4">
        <div className="font-black">{title}</div>
        <div className="rounded-full bg-cyan-300 px-3 py-1 text-sm font-black text-slate-950">
          {formatCount(total)} پیام خودرویی
        </div>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto scroll-area">
        {isLoading ? (
          <div className="grid h-full place-items-center text-slate-400">در حال بارگذاری...</div>
        ) : rows.length === 0 ? (
          <div className="grid h-full place-items-center text-slate-400">چیزی پیدا نشد</div>
        ) : (
          <div className="divide-y divide-white/10">
            {rows.map((row) => (
              <div key={row.username} className="flex items-center justify-between gap-3 px-4 py-2.5">
                <div className="min-w-0">
                  <div className="truncate text-sm font-bold">{row.title || row.username}</div>
                  <div className="truncate text-xs text-slate-400">
                    @{row.username} {!row.active && "· غیرفعال"}
                  </div>
                </div>
                <div
                  className={[
                    "shrink-0 rounded-lg px-2.5 py-1 text-sm font-black",
                    row.car_ads > 0 ? "bg-emerald-400/15 text-emerald-200" : "bg-white/5 text-slate-500",
                  ].join(" ")}
                >
                  {formatCount(row.car_ads)}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
