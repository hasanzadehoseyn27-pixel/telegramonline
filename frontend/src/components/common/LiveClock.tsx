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
        "group relative flex items-center gap-2 overflow-hidden rounded-2xl border border-cyan-300/25 bg-gradient-to-l from-cyan-300/15 via-slate-900/40 to-fuchsia-400/10 text-cyan-50 shadow-lg shadow-cyan-950/20 backdrop-blur-sm transition-transform hover:scale-[1.02]",
        compact ? "px-3 py-2 text-xs" : "px-5 py-2.5 text-sm",
      ].join(" ")}
    >
      <span className="pointer-events-none absolute inset-0 -translate-x-full bg-gradient-to-l from-transparent via-white/10 to-transparent transition-transform duration-1000 group-hover:translate-x-0" />
      <span className="relative grid h-8 w-8 shrink-0 place-items-center rounded-xl bg-gradient-to-br from-cyan-300 to-cyan-500 text-slate-950 shadow-md shadow-cyan-500/30">
        <Clock size={17} className="animate-[spin_8s_linear_infinite]" />
      </span>
      <span className="relative font-black leading-6 tracking-wide">{formatted}</span>
    </div>
  );
}
