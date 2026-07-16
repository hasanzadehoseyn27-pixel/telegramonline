import { Plus, Radio, Trash2 } from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { addChannel, deleteChannel, getLiveChannels } from "../api/channels.api";
import { formatDateTime, formatNumber } from "../utils/format";

export default function Channels() {
  const [username, setUsername] = useState("");
  const queryClient = useQueryClient();
  const { data } = useQuery({
    queryKey: ["channels", "live"],
    queryFn: getLiveChannels,
    refetchInterval: 5000,
  });

  const addMutation = useMutation({
    mutationFn: addChannel,
    onSuccess: () => {
      setUsername("");
      queryClient.invalidateQueries({ queryKey: ["channels"] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deleteChannel,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["channels"] }),
  });

  return (
    <div className="grid h-full min-h-0 grid-rows-[auto_minmax(0,1fr)] gap-4">
      <div className="glass-panel rounded-xl p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="flex items-center gap-2 text-xl font-black">
              <Radio className="text-cyan-200" />
              مدیریت کانال‌ها
            </div>
            <div className="mt-1 text-sm text-slate-400">
              مجموع امروز: {formatNumber(data?.summary.messages_today ?? 0)} پیام از{" "}
              {formatNumber(data?.summary.active_channels ?? 0)} کانال فعال ·{" "}
              {formatNumber(data?.summary.joined_channels ?? 0)} از{" "}
              {formatNumber(data?.summary.total_channels ?? 0)} کانال عضو شده
            </div>
          </div>
          <div className="flex h-11 overflow-hidden rounded-lg border border-white/10 bg-slate-950/70">
            <input
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              className="w-64 bg-transparent px-3 text-sm outline-none"
              placeholder="@channel"
            />
            <button
              onClick={() => username && addMutation.mutate(username)}
              disabled={addMutation.isPending}
              className="flex items-center gap-1 bg-cyan-300 px-4 text-sm font-black text-slate-950 transition hover:bg-white disabled:opacity-60"
            >
              <Plus size={16} />
              افزودن
            </button>
          </div>
        </div>
      </div>

      <div className="glass-panel min-h-0 overflow-hidden rounded-xl">
        <div className="h-full overflow-auto scroll-area">
          <table className="w-full min-w-[760px] text-sm">
            <thead className="sticky top-0 bg-slate-950/95 text-slate-400">
              <tr>
                <th className="border-b border-white/10 px-4 py-3 text-right">کانال</th>
                <th className="border-b border-white/10 px-4 py-3 text-right">وضعیت</th>
                <th className="border-b border-white/10 px-4 py-3 text-right">پیام‌های امروز</th>
                <th className="border-b border-white/10 px-4 py-3 text-right">تاریخ افزودن</th>
                <th className="border-b border-white/10 px-4 py-3 text-right">عملیات</th>
              </tr>
            </thead>
            <tbody>
              {(data?.channels ?? []).map((channel) => (
                <tr key={channel.id} className="hover:bg-white/5">
                  <td className="border-b border-white/10 px-4 py-3 font-bold">
                    {channel.title ?? channel.username}
                    <div className="mt-1 text-xs text-slate-400">@{channel.username}</div>
                  </td>
                  <td className="border-b border-white/10 px-4 py-3">
                    <span className="rounded-full bg-emerald-400/15 px-2 py-1 text-xs font-bold text-emerald-100">
                      {channel.active && channel.joined ? "فعال و عضو شده" : "در انتظار فعال‌سازی"}
                    </span>
                  </td>
                  <td className="border-b border-white/10 px-4 py-3 font-black text-cyan-100">
                    {formatNumber(channel.today_messages ?? channel.message_count ?? 0)}
                  </td>
                  <td className="border-b border-white/10 px-4 py-3 text-slate-300">
                    {formatDateTime(channel.added_at)}
                  </td>
                  <td className="border-b border-white/10 px-4 py-3">
                    <button
                      onClick={() => deleteMutation.mutate(channel.id)}
                      className="grid h-9 w-9 place-items-center rounded-lg bg-rose-500/15 text-rose-100 transition hover:bg-rose-500"
                    >
                      <Trash2 size={16} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
