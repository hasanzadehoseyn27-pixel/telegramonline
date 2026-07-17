import { AnimatePresence, motion } from "framer-motion";
import { Menu, X } from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";

function useIsDesktop() {
  const [isDesktop, setIsDesktop] = useState(() =>
    typeof window !== "undefined" ? window.innerWidth >= 1024 : true,
  );

  useEffect(() => {
    const mql = window.matchMedia("(min-width: 1024px)");
    const handler = () => setIsDesktop(mql.matches);
    handler();
    mql.addEventListener("change", handler);
    return () => mql.removeEventListener("change", handler);
  }, []);

  return isDesktop;
}

export default function FiltersDrawer({ open, onClose, children }: { open: boolean; onClose?: () => void; children: ReactNode }) {
  const isDesktop = useIsDesktop();

  if (isDesktop) {
    return (
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ width: 0, opacity: 0, marginRight: 0 }}
            animate={{ width: 300, opacity: 1, marginRight: 16 }}
            exit={{ width: 0, opacity: 0, marginRight: 0 }}
            transition={{ type: "spring", stiffness: 260, damping: 28 }}
            className="h-full min-h-0 shrink-0 overflow-hidden"
          >
            <div className="h-full min-h-0 w-[300px]">{children}</div>
          </motion.div>
        )}
      </AnimatePresence>
    );
  }

  // موبایل/تبلت: کنار جدول جا نمی‌شه، پس به‌جای فشردن، یه اورلی تمام‌صفحه باز می‌شه
  return (
    <AnimatePresence>
      {open && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 flex justify-end bg-slate-950/70 backdrop-blur-sm"
          onClick={onClose}
        >
          <motion.div
            initial={{ x: -320 }}
            animate={{ x: 0 }}
            exit={{ x: -320 }}
            transition={{ type: "spring", stiffness: 260, damping: 28 }}
            onClick={(event) => event.stopPropagation()}
            className="h-full w-[86vw] max-w-sm p-3"
          >
            {children}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

export function FiltersToggleButton({ open, onClick }: { open: boolean; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={[
        "flex h-10 shrink-0 items-center gap-2 rounded-xl px-4 text-sm font-black transition",
        open ? "bg-white text-slate-950" : "bg-white/10 hover:bg-white/20",
      ].join(" ")}
    >
      {open ? <X size={17} /> : <Menu size={17} />}
      فیلترها
    </button>
  );
}
