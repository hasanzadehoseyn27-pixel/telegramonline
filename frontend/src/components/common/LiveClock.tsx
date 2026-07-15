import { Clock } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

function formatClock(date: Date) {
  return new Intl.DateTimeFormat("fa-IR-u-ca-persian", {
    weekday: "long",
    year: "numeric",
    month: "long",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).format(date);
}

export default function LiveClock({ compact = false }: { compact?: boolean }) {
  const [now, setNow] = useState(() => new Date());

  useEffect(() => {
    const timer = window.setInterval(() => setNow(new Date()), 1000);
    return () => window.clearInterval(timer);
  }, []);

  const formatted = useMemo(() => formatClock(now), [now]);

  return (
    <div
      className={[
        "flex items-center gap-2 rounded-xl border border-cyan-300/20 bg-cyan-300/10 text-cyan-50 shadow-lg shadow-cyan-950/10",
        compact ? "px-3 py-2 text-xs" : "px-4 py-3 text-sm",
      ].join(" ")}
    >
      <span className="grid h-8 w-8 place-items-center rounded-lg bg-cyan-300 text-slate-950">
        <Clock size={17} />
      </span>
      <span className="font-black leading-6">{formatted}</span>
    </div>
  );
}
