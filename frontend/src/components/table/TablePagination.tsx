interface Props {
  count: number;
}

export default function TablePagination({ count }: Props) {
  return (
    <div className="flex h-10 items-center justify-between border-t border-white/10 px-4 text-xs text-slate-400">
      <span>{count} ردیف</span>
      <span>داده‌های امروز</span>
    </div>
  );
}
