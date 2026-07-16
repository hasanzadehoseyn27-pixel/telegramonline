import { motion } from "framer-motion";
import { Bell, Car, Plus, Radio, ShoppingBag, Sparkles, TrendingDown, Wrench } from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import AdsFilters from "../components/filters/AdsFilters";
import AdsTable from "../components/table/AdsTable";
import LiveClock from "../components/common/LiveClock";
import { useDashboard } from "../hooks/useDashboard";
import { useAdsStore, type AdsTab } from "../store/adsStore";
import { addChannel, getLiveChannels } from "../api/channels.api";
import { getLiveCheapestVehicles } from "../api/vehicles.api";
import { formatCount } from "../utils/format";

const tabButtons: { tab: AdsTab; title: string; icon: typeof Car }[] = [
  { tab: "priced", title: "قیمت‌دار", icon: Car },
  { tab: "unpriced", title: "بدون قیمت", icon: Bell },
  { tab: "used", title: "کارکرده", icon: Wrench },
  { tab: "buyers", title: "خریدارم", icon: ShoppingBag },
];

export default function Dashboard() {
  const [channelUsername, setChannelUsername] = useState("");
  const { data } = useDashboard();
  const { data: cheapest } = useQuery({
    queryKey: ["vehicles", "cheapest-live", "count"],
    queryFn: () => getLiveCheapestVehicles(1, 0),
    refetchInterval: 5000,
  });
  const { data: channels } = useQuery({
    queryKey: ["channels", "live"],
    queryFn: getLiveChannels,
    refetchInterval: 5000,
  });
  const { activeTab, setTab } = useAdsStore();
  const queryClient = useQueryClient();

  const addChannelMutation = useMutation({
    mutationFn: addChannel,
    onSuccess: () => {
      setChannelUsername("");
      queryClient.invalidateQueries({ queryKey: ["channels"] });
    },
  });

  const stats = useMemo(
    () => [
      { title: "پیام امروز", value: data?.today.total_ads ?? 0, icon: Radio },
      { title: "قیمت‌دار", value: data?.today.priced ?? 0, icon: Car },
      { title: "بدون قیمت", value: data?.today.unpriced ?? 0, icon: Bell },
      { title: "کمترین‌ها", value: cheapest?.total ?? 0, icon: TrendingDown },
    ],
    [cheapest?.total, data],
  );

  return (
    <div className="grid h-full min-h-0 grid-rows-[auto_minmax(0,1fr)] gap-4">
      <section className="glass-panel overflow-hidden rounded-2xl">
        <div className="grid gap-4 p-4 lg:grid-cols-[1.2fr_.8fr] xl:grid-cols-[1.35fr_.65fr]">
          <div className="min-w-0">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <div className="inline-flex items-center gap-2 rounded-full border border-cyan-300/20 bg-cyan-300/10 px-3 py-1 text-xs font-black text-cyan-100">
                  <Sparkles size={15} />
                  نبض زنده بازار خودرو
                </div>
                <h2 className="mt-3 text-2xl font-black tracking-normal sm:text-3xl">
                  داشبورد امروز، خلوت و زنده
                </h2>
                <p className="mt-2 max-w-2xl text-sm leading-7 text-slate-400 theme-muted">
                  همه عددها با داده‌های امروز هماهنگ می‌شوند؛ کمترین‌ها از همان منبع صفحه کمترین قیمت خوانده می‌شود.
                </p>
              </div>
              <LiveClock compact />
            </div>

            <div className="mt-5 grid grid-cols-2 gap-2 lg:grid-cols-4">
              {stats.map((stat, index) => {
                const Icon = stat.icon;
                return (
                  <motion.div
                    key={stat.title}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.04 }}
                    className="rounded-2xl border border-white/10 bg-white/[0.07] p-3"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="grid h-9 w-9 place-items-center rounded-xl bg-white text-slate-950">
                        <Icon size={18} />
                      </span>
                      <motion.span
                        key={stat.value}
                        initial={{ scale: 0.88, opacity: 0.5 }}
                        animate={{ scale: 1, opacity: 1 }}
                        className="text-2xl font-black sm:text-3xl"
                      >
                        {formatCount(stat.value)}
                      </motion.span>
                    </div>
                    <div className="mt-2 text-xs font-bold text-slate-400 theme-muted">{stat.title}</div>
                  </motion.div>
                );
              })}
            </div>
          </div>

          <div className="grid content-between gap-3 rounded-2xl border border-white/10 bg-slate-950/45 p-3">
            <div className="grid grid-cols-2 gap-2">
              <div className="rounded-xl bg-white/[0.07] p-3">
                <div className="text-xs text-slate-400 theme-muted">کانال فعال</div>
                <div className="mt-1 text-2xl font-black">
                  {formatCount(channels?.summary.active_channels ?? data?.channels.active ?? 0)}
                </div>
              </div>
              <div className="rounded-xl bg-white/[0.07] p-3">
                <div className="text-xs text-slate-400 theme-muted">پیام کانال‌ها</div>
                <div className="mt-1 text-2xl font-black">
                  {formatCount(channels?.summary.messages_today ?? data?.channels.messages_today ?? 0)}
                </div>
              </div>
            </div>

            <div className="flex h-11 overflow-hidden rounded-xl border border-white/10 bg-slate-950/70">
              <input
                value={channelUsername}
                onChange={(event) => setChannelUsername(event.target.value)}
                className="min-w-0 flex-1 bg-transparent px-3 text-sm outline-none"
                placeholder="@channel"
              />
              <button
                onClick={() => channelUsername && addChannelMutation.mutate(channelUsername)}
                disabled={addChannelMutation.isPending}
                className="flex shrink-0 items-center gap-1 bg-cyan-300 px-3 text-sm font-black text-slate-950 transition hover:bg-white disabled:opacity-60"
              >
                <Plus size={16} />
                افزودن
              </button>
            </div>

            <div className="flex min-w-0 flex-wrap gap-2">
              {tabButtons.map((item) => {
                const Icon = item.icon;
                return (
                  <button
                    key={item.tab}
                    onClick={() => setTab(item.tab)}
                    className={[
                      "flex h-10 shrink-0 items-center gap-2 rounded-xl px-4 text-sm font-black transition",
                      activeTab === item.tab ? "bg-white text-slate-950" : "bg-white/10 hover:bg-white/20",
                    ].join(" ")}
                  >
                    <Icon size={17} />
                    {item.title}
                  </button>
                );
              })}
            </div>
          </div>
        </div>
      </section>

      <section className="grid min-h-0 grid-cols-[minmax(0,1fr)_300px] gap-4 max-xl:grid-cols-1">
        <div className="min-w-0 min-h-0">
          <AdsTable />
        </div>
        <div className="min-h-0 max-xl:hidden">
          <AdsFilters />
        </div>
      </section>
    </div>
  );
}
