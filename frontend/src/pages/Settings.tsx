import { Download, Plus, Radio, Settings as SettingsIcon, Trash2 } from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { addSourceGroup, deleteSourceGroup, getSourceGroups } from "../api/sourceGroups.api";
import { cheapestExcelUrl } from "../api/reports.api";
import { formatCount, formatDateTime } from "../utils/format";

export default function Settings() {
  const [groupLink, setGroupLink] = useState("");
  const queryClient = useQueryClient();
  const { data: groups = [] } = useQuery({
    queryKey: ["source-groups"],
    queryFn: getSourceGroups,
    refetchInterval: 5000,
  });

  const addMutation = useMutation({
    mutationFn: addSourceGroup,
    onSuccess: () => {
      setGroupLink("");
      queryClient.invalidateQueries({ queryKey: ["source-groups"] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deleteSourceGroup,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["source-groups"] }),
  });

  return (
    <div className="grid h-full min-h-0 grid-rows-[auto_minmax(0,1fr)] gap-4">
      <section className="glass-panel rounded-2xl p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="flex items-center gap-2 text-xl font-black">
              <SettingsIcon className="text-cyan-200" />
              تنظیمات پایش
            </div>
            <p className="mt-1 text-sm text-slate-400 theme-muted">
              گروه‌های منبع را اضافه کن تا collector کانال‌های فوروارد شده داخل آن‌ها را خودکار پیدا و join کند.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <a
              href={cheapestExcelUrl("today")}
              className="flex h-10 items-center gap-2 rounded-xl bg-cyan-300 px-4 text-sm font-black text-slate-950 transition hover:bg-white"
            >
              <Download size={17} />
              اکسل امروز
            </a>
            <a
              href={cheapestExcelUrl("yesterday")}
              className="flex h-10 items-center gap-2 rounded-xl bg-white/10 px-4 text-sm font-black transition hover:bg-white hover:text-slate-950"
            >
              <Download size={17} />
              اکسل دیروز
            </a>
          </div>
        </div>
      </section>

      <section className="grid min-h-0 grid-cols-[380px_minmax(0,1fr)] gap-4 max-xl:grid-cols-1">
        <div className="glass-panel rounded-2xl p-4">
          <div className="mb-4 flex items-center gap-2 text-lg font-black">
            <Radio className="text-cyan-200" />
            اضافه کردن گروه
          </div>
          <div className="flex h-11 overflow-hidden rounded-xl border border-white/10 bg-slate-950/70">
            <input
              value={groupLink}
              onChange={(event) => setGroupLink(event.target.value)}
              className="min-w-0 flex-1 bg-transparent px-3 text-sm outline-none"
              placeholder="https://t.me/group یا @group"
            />
            <button
              onClick={() => groupLink && addMutation.mutate(groupLink)}
              disabled={addMutation.isPending}
              className="flex shrink-0 items-center gap-1 bg-cyan-300 px-3 text-sm font-black text-slate-950 transition hover:bg-white disabled:opacity-60"
            >
              <Plus size={16} />
              افزودن
            </button>
          </div>
          <p className="mt-3 text-xs leading-6 text-slate-400 theme-muted">
            collector هر ۳۰ ثانیه گروه‌های جدید را فعال می‌کند و بعد به صورت ۲۴ ساعته پیام‌های فورواردی آن‌ها را برای کشف کانال مبدا زیر نظر می‌گیرد.
          </p>
        </div>

        <div className="glass-panel min-h-0 overflow-hidden rounded-2xl">
          <div className="flex items-center justify-between border-b border-white/10 p-4">
            <div className="font-black">لیست گروه‌های منبع</div>
            <div className="rounded-full bg-cyan-300/15 px-3 py-1 text-xs font-black text-cyan-100">
              {formatCount(groups.length)} گروه
            </div>
          </div>
          <div className="h-full overflow-auto pb-16 scroll-area">
            <table className="w-full min-w-[760px] text-sm max-md:hidden">
              <thead className="sticky top-0 bg-slate-950/95 text-slate-400">
                <tr>
                  <th className="border-b border-white/10 px-4 py-3 text-right">گروه</th>
                  <th className="border-b border-white/10 px-4 py-3 text-right">وضعیت</th>
                  <th className="border-b border-white/10 px-4 py-3 text-right">کانال کشف‌شده</th>
                  <th className="border-b border-white/10 px-4 py-3 text-right">تاریخ افزودن</th>
                  <th className="border-b border-white/10 px-4 py-3 text-right">حذف</th>
                </tr>
              </thead>
              <tbody>
                {groups.map((group) => (
                  <tr key={group.id} className="hover:bg-white/5">
                    <td className="border-b border-white/10 px-4 py-3 font-bold">
                      {group.title ?? group.username}
                      <div className="mt-1 text-xs text-slate-400">@{group.username}</div>
                    </td>
                    <td className="border-b border-white/10 px-4 py-3">
                      <span className="rounded-full bg-white/10 px-2 py-1 text-xs">
                        {group.joined ? "فعال" : "در انتظار collector"}
                      </span>
                    </td>
                    <td className="border-b border-white/10 px-4 py-3 font-black text-cyan-100">
                      {formatCount(group.discovered_channels)}
                    </td>
                    <td className="border-b border-white/10 px-4 py-3 text-slate-300">
                      {formatDateTime(group.added_at)}
                    </td>
                    <td className="border-b border-white/10 px-4 py-3">
                      <button
                        onClick={() => deleteMutation.mutate(group.id)}
                        className="grid h-9 w-9 place-items-center rounded-xl bg-rose-500/15 text-rose-100 transition hover:bg-rose-500"
                      >
                        <Trash2 size={16} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            <div className="grid gap-3 p-3 md:hidden">
              {groups.map((group) => (
                <div key={group.id} className="rounded-2xl border border-white/10 bg-white/[0.07] p-3">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="truncate font-black">{group.title ?? group.username}</div>
                      <div className="mt-1 text-xs text-slate-400">@{group.username}</div>
                    </div>
                    <button
                      onClick={() => deleteMutation.mutate(group.id)}
                      className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-rose-500/15 text-rose-100"
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
                  <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
                    <div className="rounded-xl bg-slate-950/60 p-2">
                      وضعیت
                      <div className="mt-1 font-bold">{group.joined ? "فعال" : "در انتظار"}</div>
                    </div>
                    <div className="rounded-xl bg-slate-950/60 p-2">
                      کشف شده
                      <div className="mt-1 font-bold">{formatCount(group.discovered_channels)}</div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
