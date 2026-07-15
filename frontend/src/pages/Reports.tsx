import { Download, FileSpreadsheet } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { cheapestExcelUrl, getCheapestReport } from "../api/reports.api";
import { formatDateTime, formatNumber } from "../utils/format";

export default function Reports() {
  const [day, setDay] = useState<"today" | "yesterday">("today");
  const { data } = useQuery({
    queryKey: ["reports", "cheapest", day],
    queryFn: () => getCheapestReport(day),
    refetchInterval: day === "today" ? 30000 : false,
  });

  return (
    <div className="grid h-full min-h-0 grid-rows-[auto_minmax(0,1fr)] gap-4">
      <div className="glass-panel flex flex-wrap items-center justify-between gap-3 rounded-xl p-4">
        <div>
          <div className="flex items-center gap-2 text-xl font-black">
            <FileSpreadsheet className="text-cyan-200" />
            گزارش کمترین قیمت
          </div>
          <div className="mt-1 text-sm text-slate-400">امروز و دیروز با خروجی Excel</div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setDay("today")}
            className={[
              "h-10 rounded-lg px-4 text-sm font-black transition",
              day === "today" ? "bg-white text-slate-950" : "bg-white/10 hover:bg-white/20",
            ].join(" ")}
          >
            امروز
          </button>
          <button
            onClick={() => setDay("yesterday")}
            className={[
              "h-10 rounded-lg px-4 text-sm font-black transition",
              day === "yesterday" ? "bg-white text-slate-950" : "bg-white/10 hover:bg-white/20",
            ].join(" ")}
          >
            دیروز
          </button>
          <a
            href={cheapestExcelUrl(day)}
            className="flex h-10 items-center gap-2 rounded-lg bg-cyan-300 px-4 text-sm font-black text-slate-950 transition hover:bg-white"
          >
            <Download size={17} />
            Excel
          </a>
        </div>
      </div>

      <div className="glass-panel min-h-0 overflow-hidden rounded-xl">
        <div className="h-full overflow-auto scroll-area">
          <table className="w-full min-w-[900px] text-sm">
            <thead className="sticky top-0 bg-slate-950/95 text-slate-400">
              <tr>
                <th className="border-b border-white/10 px-4 py-3 text-right">خودرو</th>
                <th className="border-b border-white/10 px-4 py-3 text-right">کمترین قیمت</th>
                <th className="border-b border-white/10 px-4 py-3 text-right">مدل</th>
                <th className="border-b border-white/10 px-4 py-3 text-right">رنگ</th>
                <th className="border-b border-white/10 px-4 py-3 text-right">کانال</th>
                <th className="border-b border-white/10 px-4 py-3 text-right">تاریخ و ساعت</th>
              </tr>
            </thead>
            <tbody>
              {(data?.items ?? []).map((item) => (
                <tr key={`${item.vehicle_key}-${item.id}`} className="hover:bg-white/5">
                  <td className="border-b border-white/10 px-4 py-3 font-bold">{item.vehicle_name ?? "-"}</td>
                  <td className="border-b border-white/10 px-4 py-3 font-black text-cyan-100">
                    {formatNumber(item.price_million)} میلیون
                  </td>
                  <td className="border-b border-white/10 px-4 py-3">{item.year ?? "-"}</td>
                  <td className="border-b border-white/10 px-4 py-3">{item.color ?? "-"}</td>
                  <td className="border-b border-white/10 px-4 py-3">
                    {item.telegram_link ? (
                      <a href={item.telegram_link} target="_blank" rel="noreferrer" className="text-cyan-100">
                        @{item.channel_username}
                      </a>
                    ) : (
                      "-"
                    )}
                  </td>
                  <td className="border-b border-white/10 px-4 py-3 text-slate-300">
                    {formatDateTime(item.message_date)}
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
