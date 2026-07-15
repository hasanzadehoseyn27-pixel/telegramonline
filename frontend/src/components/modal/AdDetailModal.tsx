import { AnimatePresence, motion } from "framer-motion";
import { ExternalLink, X } from "lucide-react";
import { useAdDetail } from "../../hooks/useAdDetail";
import { formatDateTime, formatNumber, telegramLink } from "../../utils/format";

interface Props {
  adId?: number;
  onClose: () => void;
}

export default function AdDetailModal({ adId, onClose }: Props) {
  const { data, isLoading } = useAdDetail(adId);
  const link = data?.telegram_link ?? telegramLink(data?.channel_username, data?.source_message_id);

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-50 grid place-items-center bg-slate-950/78 p-4 backdrop-blur-md"
        onClick={onClose}
      >
        <motion.div
          initial={{ opacity: 0, y: 18, scale: 0.96 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 18, scale: 0.96 }}
          onClick={(event) => event.stopPropagation()}
          className="glass-panel flex max-h-[86vh] w-full max-w-3xl flex-col overflow-hidden rounded-xl"
        >
          <div className="flex items-center justify-between border-b border-white/10 p-4">
            <div>
              <div className="font-black">{data?.vehicle_name ?? "متن اصلی پیام"}</div>
              <div className="mt-1 text-xs text-slate-400">{formatDateTime(data?.message_date)}</div>
            </div>
            <button onClick={onClose} className="grid h-9 w-9 place-items-center rounded-lg bg-white/10 hover:bg-white/20">
              <X size={18} />
            </button>
          </div>

          {isLoading ? (
            <div className="grid h-72 place-items-center text-slate-400">در حال دریافت پیام...</div>
          ) : (
            data && (
              <div className="min-h-0 flex-1 overflow-y-auto p-4 scroll-area">
                <div className="mb-4 grid grid-cols-2 gap-2 text-sm md:grid-cols-4">
                  <div className="rounded-lg bg-white/5 p-3">
                    <div className="text-xs text-slate-400">قیمت</div>
                    <div className="mt-1 font-black text-cyan-100">
                      {data.price_million ? `${formatNumber(data.price_million)} میلیون` : "-"}
                    </div>
                  </div>
                  <div className="rounded-lg bg-white/5 p-3">
                    <div className="text-xs text-slate-400">مدل</div>
                    <div className="mt-1 font-bold">{data.year ?? "-"}</div>
                  </div>
                  <div className="rounded-lg bg-white/5 p-3">
                    <div className="text-xs text-slate-400">رنگ</div>
                    <div className="mt-1 font-bold">{data.color ?? "-"}</div>
                  </div>
                  <div className="rounded-lg bg-white/5 p-3">
                    <div className="text-xs text-slate-400">کانال</div>
                    <div className="mt-1 font-bold">{data.channel_username ? `@${data.channel_username}` : "-"}</div>
                  </div>
                </div>

                <div className="max-h-96 overflow-y-auto whitespace-pre-wrap rounded-xl border border-white/10 bg-slate-950/70 p-4 leading-8 text-slate-100 scroll-area">
                  {data.raw_text}
                </div>

                {link && (
                  <a
                    href={link}
                    target="_blank"
                    rel="noreferrer"
                    className="mt-4 flex h-12 items-center justify-center gap-2 rounded-lg bg-cyan-300 font-black text-slate-950 transition hover:bg-white"
                  >
                    رفتن به همین پیام در تلگرام
                    <ExternalLink size={18} />
                  </a>
                )}
              </div>
            )
          )}
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
