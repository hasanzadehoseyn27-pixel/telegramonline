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
      className="grid h-full min-h-0 w-full max-w-full grid-rows-[auto_minmax(0,1fr)] gap-1"
      style={{ width: "100%", maxWidth: "100%" }}
    >
      <div className="flex min-w-0 flex-wrap items-center justify-between gap-1">
        <div className="grid min-w-0 flex-1 grid-cols-2 gap-1.5 sm:flex sm:flex-wrap sm:gap-1.5">
          {tabButtons.map((item) => {
            const Icon = item.icon;
            return (
              <button
                key={item.tab}
                onClick={() => setTab(item.tab)}
                className={[
                  "flex h-9 min-w-0 items-center justify-center gap-1.5 rounded-xl px-2 text-xs font-black transition sm:shrink-0 sm:gap-2 sm:px-3 sm:text-sm",
                  activeTab === item.tab ? "bg-white text-slate-950" : "bg-white/10 hover:bg-white/20",
                ].join(" ")}
              >
                <Icon size={16} />
                <span className="truncate">{item.title}</span>
              </button>
            );
          })}
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
