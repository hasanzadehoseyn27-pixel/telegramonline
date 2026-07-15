import {
  Bell,
  Car,
  FileSpreadsheet,
  Flame,
  Home,
  LayoutDashboard,
  Radio,
  Settings,
  ShieldCheck,
} from "lucide-react";
import { NavLink } from "react-router-dom";

const desktopMenu = [
  { title: "داشبورد", icon: LayoutDashboard, path: "/" },
  { title: "آگهی‌ها", icon: Car, path: "/ads" },
  { title: "کمترین", icon: Flame, path: "/cheapest" },
  { title: "کانال‌ها", icon: Radio, path: "/channels" },
  { title: "هشدار", icon: Bell, path: "/alerts" },
  { title: "گزارش", icon: FileSpreadsheet, path: "/reports" },
  { title: "تنظیمات", icon: Settings, path: "/settings" },
];

const mobileMenu = [
  { title: "آگهی", icon: Car, path: "/ads" },
  { title: "کمترین", icon: Flame, path: "/cheapest" },
  { title: "خانه", icon: Home, path: "/", center: true },
  { title: "کانال", icon: Radio, path: "/channels" },
  { title: "هشدار", icon: Bell, path: "/alerts" },
];

export default function Sidebar() {
  return (
    <>
      <aside className="glass-panel fixed right-0 top-0 z-30 h-screen w-64 p-4 max-lg:hidden">
        <div className="mb-7 rounded-2xl border border-cyan-300/20 bg-cyan-300/10 p-4">
          <div className="flex items-center gap-3 text-lg font-black">
            <span className="grid h-10 w-10 place-items-center rounded-xl bg-cyan-300 text-slate-950">
              TO
            </span>
            TelegramOnline
          </div>
          <div className="mt-3 flex items-center gap-2 text-xs text-cyan-100/75">
            <ShieldCheck size={15} />
            مانیتورینگ خصوصی بازار خودرو
          </div>
        </div>

        <nav className="space-y-2">
          {desktopMenu.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.path}
                to={item.path}
                className={({ isActive }) =>
                  [
                    "flex h-11 items-center gap-3 rounded-xl px-3 text-sm font-bold transition",
                    isActive
                      ? "bg-white text-slate-950 shadow-lg shadow-cyan-400/10"
                      : "text-slate-300 hover:bg-white/10 hover:text-white",
                  ].join(" ")
                }
              >
                <Icon size={19} />
                <span>{item.title}</span>
              </NavLink>
            );
          })}
        </nav>
      </aside>

      <nav className="glass-panel fixed bottom-3 left-3 right-3 z-40 hidden h-16 items-center justify-around rounded-2xl px-2 max-lg:flex">
        {mobileMenu.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) =>
                [
                  "relative grid min-w-12 place-items-center gap-1 rounded-xl px-2 text-[10px] font-black transition",
                  item.center ? "-mt-7 h-16 w-16 rounded-2xl shadow-xl shadow-cyan-500/20" : "py-2",
                  isActive
                    ? item.center
                      ? "bg-cyan-300 text-slate-950"
                      : "bg-white/15 text-white"
                    : item.center
                      ? "bg-white text-slate-950"
                      : "text-slate-300 hover:bg-white/10",
                ].join(" ")
              }
            >
              <Icon size={item.center ? 24 : 18} />
              <span>{item.title}</span>
            </NavLink>
          );
        })}
      </nav>
    </>
  );
}
