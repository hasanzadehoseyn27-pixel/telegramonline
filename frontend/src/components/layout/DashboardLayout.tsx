import { useEffect, useState, type ReactNode } from "react";
import { useQueryClient } from "@tanstack/react-query";
import Sidebar from "./Sidebar";
import Header from "./Header";

interface Props {
  children: ReactNode;
}

export default function DashboardLayout({ children }: Props) {
  const queryClient = useQueryClient();
  const [theme, setTheme] = useState<"dark" | "light">(() => {
    return localStorage.getItem("telegramonline_theme") === "light" ? "light" : "dark";
  });

  useEffect(() => {
    document.documentElement.classList.toggle("light-theme", theme === "light");
    localStorage.setItem("telegramonline_theme", theme);
  }, [theme]);

  useEffect(() => {
    const baseUrl = import.meta.env.VITE_WS_URL || "ws://127.0.0.1:8000/ws";
    const socket = new WebSocket(baseUrl);

    socket.onmessage = () => {
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      queryClient.invalidateQueries({ queryKey: ["ads"] });
      queryClient.invalidateQueries({ queryKey: ["vehicles", "cheapest-live"] });
      queryClient.invalidateQueries({ queryKey: ["alerts"] });
      queryClient.invalidateQueries({ queryKey: ["alert-events"] });
      queryClient.invalidateQueries({ queryKey: ["channels"] });
      queryClient.invalidateQueries({ queryKey: ["filters"] });
    };

    return () => socket.close();
  }, [queryClient]);

  return (
    <div
      className="relative h-screen overflow-hidden text-white"
      style={{ background: "var(--page-bg)", color: "var(--text-primary)" }}
    >
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_82%_12%,rgba(34,211,238,.16),transparent_26%),radial-gradient(circle_at_16%_92%,rgba(244,63,94,.13),transparent_28%)]" />
      <Sidebar />
      <Header theme={theme} onToggleTheme={() => setTheme((value) => (value === "dark" ? "light" : "dark"))} />
      <main className="relative mr-64 h-screen overflow-hidden pt-14 max-lg:mr-0 max-sm:pb-20 max-sm:pt-12">
        <div className="h-full overflow-hidden px-4 py-2 sm:px-5 lg:px-7">{children}</div>
      </main>
    </div>
  );
}
