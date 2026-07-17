import { AnimatePresence, motion } from "framer-motion";
import { Menu, X } from "lucide-react";
import { useState, type ReactNode } from "react";

export default function FiltersDrawer({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false);

  return (
    <div className="flex h-full min-h-0 shrink-0">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className={[
          "flex h-10 shrink-0 items-center gap-2 self-start rounded-xl px-4 text-sm font-black transition",
          open ? "bg-white text-slate-950" : "bg-white/10 hover:bg-white/20",
        ].join(" ")}
      >
        {open ? <X size={17} /> : <Menu size={17} />}
        فیلترها
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ width: 0, opacity: 0, marginRight: 0 }}
            animate={{ width: 300, opacity: 1, marginRight: 16 }}
            exit={{ width: 0, opacity: 0, marginRight: 0 }}
            transition={{ type: "spring", stiffness: 260, damping: 28 }}
            className="h-full min-h-0 overflow-hidden"
          >
            <div className="h-full min-h-0 w-[300px]">{children}</div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
