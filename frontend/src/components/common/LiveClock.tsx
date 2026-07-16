import { useEffect, useMemo, useState } from "react";

function formatDate(date: Date) {
  return new Intl.DateTimeFormat("fa-IR-u-ca-persian", {
    weekday: "long",
    year: "numeric",
    month: "long",
    day: "numeric",
  }).format(date);
}

function formatTime(date: Date) {
  return new Intl.DateTimeFormat("fa-IR-u-ca-persian", {
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

  const dateText = useMemo(() => formatDate(now), [now]);
  const timeText = useMemo(() => formatTime(now), [now]);

  return (
    <div
      className={[
        "relative flex items-center gap-3 overflow-hidden rounded-2xl border border-cyan-300/20 bg-gradient-to-l from-slate-900/60 via-slate-900/40 to-cyan-300/10 shadow-lg shadow-cyan-950/20 backdrop-blur-sm",
        compact ? "px-3 py-1.5" : "px-5 py-2",
      ].join(" ")}
    >
      <span className="relative flex h-2.5 w-2.5 shrink-0">
        <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-cyan-300 opacity-75" />
        <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-cyan-300" />
      </span>
      <div className="leading-tight">
        {!compact && <div className="text-[11px] font-medium text-cyan-100/70">{dateText}</div>}
        <div
          className={[
            "font-black tracking-widest text-white tabular-nums",
            compact ? "text-xs" : "text-lg",
          ].join(" ")}
        >
          {timeText}
        </div>
      </div>
    </div>
  );
}
