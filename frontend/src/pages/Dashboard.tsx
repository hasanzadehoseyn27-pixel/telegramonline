import { motion } from "framer-motion";
import { Bell, Car, Plus, Radio, TrendingDown } from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { useDashboard } from "../hooks/useDashboard";
import { addChannel, getLiveChannels } from "../api/channels.api";
import { getLiveCheapestVehicles } from "../api/vehicles.api";
import { formatCount } from "../utils/format";

const ACCENTS = [
  { ring: "from-cyan-300/30 to-cyan-500/0", icon: "bg-gradient-to-br from-cyan-300 to-cyan-500 text-slate-950" },
  { ring: "from-emerald-300/30 to-emerald-500/0", icon: "bg-gradient-to-br from-emerald-300 to-emerald-500 text-slate-950" },
  { ring: "from-amber-300/30 to-amber-500/0", icon: "bg-gradient-to-br from-amber-300 to-amber-500 text-slate-950" },
  { ring: "from-fuchsia-300/30 to-fuchsia-500/0", icon: "bg-gradient-to-br from-fuchsia-300 to-fuchsia-500 text-slate-950" },
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
    <div className="relative grid h-full min-h-0 content-start gap-4">
      <div className="pointer-events-none absolute -right-10 -top-16 h-64 w-64 rounded-full bg-cyan-400/25 aurora-blob" />
      <div
        className="pointer-events-none absolute -left-16 top-10 h-72 w-72 rounded-full bg-fuchsia-400/20 aurora-blob"
        style={{ animationDelay: "-6s" }}
      />

      <section className="glass-panel relative overflow-hidden rounded-2xl p-4">
        <div className="mb-4 flex items-baseline gap-2">
          <span className="text-lg font-black shimmer-text sm:text-xl">به داشبورد خوش اومدی</span>
          <span className="text-xs text-slate-400 theme-muted">— همه‌چیز زنده و لحظه‌ای است</span>
        </div>

        <div className="grid gap-4 lg:grid-cols-[1.2fr_.8fr] xl:grid-cols-[1.35fr_.65fr]">
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            {stats.map((stat, index) => {
              const Icon = stat.icon;
              const accent = ACCENTS[index % ACCENTS.length];
              return (
                <motion.div
                  key={stat.title}
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.05, type: "spring", stiffness: 140, damping: 16 }}
                  whileHover={{ y: -3, scale: 1.015 }}
                  className={`group relative overflow-hidden rounded-2xl border border-white/10 bg-gradient-to-br p-3 transition-shadow hover:shadow-lg hover:shadow-cyan-500/10 ${accent.ring}`}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span
                      className={`grid h-10 w-10 place-items-center rounded-xl shadow-md transition-transform group-hover:scale-110 ${accent.icon}`}
                    >
                      <Icon size={19} />
                    </span>
                    <motion.span
                      key={stat.value}
                      initial={{ scale: 0.85, opacity: 0.4 }}
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

          <div className="grid content-between gap-3 rounded-2xl border border-white/10 bg-slate-950/45 p-3">
            <div className="grid grid-cols-2 gap-2">
              <div className="rounded-xl bg-white/[0.07] p-3 transition hover:bg-white/[0.1]">
                <div className="text-xs text-slate-400 theme-muted">کانال فعال</div>
                <div className="mt-1 text-2xl font-black text-cyan-100">
                  {formatCount(channels?.summary.active_channels ?? data?.channels.active ?? 0)}
                </div>
              </div>
              <div className="rounded-xl bg-white/[0.07] p-3 transition hover:bg-white/[0.1]">
                <div className="text-xs text-slate-400 theme-muted">پیام کانال‌ها</div>
                <div className="mt-1 text-2xl font-black text-cyan-100">
                  {formatCount(channels?.summary.messages_today ?? data?.channels.messages_today ?? 0)}
                </div>
              </div>
            </div>

            <div className="flex h-11 overflow-hidden rounded-xl border border-white/10 bg-slate-950/70 transition focus-within:border-cyan-300/50">
              <input
                value={channelUsername}
                onChange={(event) => setChannelUsername(event.target.value)}
                className="min-w-0 flex-1 bg-transparent px-3 text-sm outline-none"
                placeholder="@channel"
              />
              <button
                onClick={() => channelUsername && addChannelMutation.mutate(channelUsername)}
                disabled={addChannelMutation.isPending}
                className="flex shrink-0 items-center gap-1 bg-gradient-to-l from-cyan-300 to-cyan-400 px-3 text-sm font-black text-slate-950 transition hover:brightness-110 disabled:opacity-60"
              >
                <Plus size={16} />
                افزودن
              </button>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
