import { Bell, Car, ShoppingBag, Wrench } from "lucide-react";
import { useState } from "react";
import AdsFilters from "../components/filters/AdsFilters";
import FiltersDrawer, { FiltersToggleButton } from "../components/filters/FiltersDrawer";
import AdsTable from "../components/table/AdsTable";
import { useAdsStore, type AdsTab } from "../store/adsStore";

const tabButtons: { tab: AdsTab; title: string; icon: typeof Car }[] = [
  { tab: "priced", title: "قیمت‌دار", icon: Car },
  { tab: "unpriced", title: "بدون قیمت", icon: Bell },
  { tab: "used", title: "کارکرده", icon: Wrench },
  { tab: "buyers", title: "خریدارم", icon: ShoppingBag },
];

export default function Ads() {
  const { activeTab, setTab } = useAdsStore();
  const [filtersOpen, setFiltersOpen] = useState(false);

  return (
    <div
      className="grid h-[calc(100vh-170px)] max-sm:h-[calc(100vh-250px)] min-h-0 w-full max-w-full grid-rows-[auto_minmax(0,1fr)] gap-4"
      style={{ width: "100%", maxWidth: "100%" }}
    >
      <div className="flex min-w-0 flex-wrap items-center justify-between gap-2">
        <div className="flex min-w-0 flex-wrap gap-2 max-sm:hidden">
          {tabButtons.map((item) => {
            const Icon = item.icon;
            return (
              <button
                key={item.tab}
                onClick={() => setTab(item.tab)}
                className={[
                  "flex h-10 shrink-0 items-center gap-2 rounded-xl px-4 text-sm font-black transition",
                  activeTab === item.tab ? "bg-white text-slate-950" : "bg-white/10 hover:bg-white/20",
                ].join(" ")}
              >
                <Icon size={17} />
                {item.title}
              </button>
            );
          })}
        </div>

        <div className="flex h-10 shrink-0 items-center rounded-xl bg-white/5 px-3 text-xs font-black text-cyan-100 sm:hidden">
          {tabButtons.find((t) => t.tab === activeTab)?.title}
        </div>

        <FiltersToggleButton open={filtersOpen} onClick={() => setFiltersOpen((v) => !v)} />
      </div>

      <div className="flex min-h-0 min-w-0 gap-0 max-xl:flex-col">
        <div className="min-h-0 min-w-0 flex-1">
          <AdsTable />
        </div>
        <FiltersDrawer open={filtersOpen} onClose={() => setFiltersOpen(false)}>
          <AdsFilters showStatusTabs />
        </FiltersDrawer>
      </div>
    </div>
  );
}
