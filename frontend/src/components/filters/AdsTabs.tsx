import { Bell, Car, ShoppingBag, Wrench } from "lucide-react";
import { useAdsStore, type AdsTab } from "../../store/adsStore";

const tabs: { key: AdsTab; label: string; icon: typeof Car }[] = [
  { key: "priced", label: "قیمت‌دار", icon: Car },
  { key: "unpriced", label: "بدون قیمت", icon: Bell },
  { key: "used", label: "کارکرده", icon: Wrench },
  { key: "buyers", label: "خریدارم", icon: ShoppingBag },
];

export default function AdsTabs() {
  const { activeTab, setTab } = useAdsStore();

  return (
    <div className="flex flex-wrap gap-2">
      {tabs.map((tab) => {
        const Icon = tab.icon;
        return (
          <button
            key={tab.key}
            onClick={() => setTab(tab.key)}
            className={[
              "flex h-10 items-center gap-2 rounded-lg px-4 text-sm font-black transition",
              activeTab === tab.key ? "bg-cyan-300 text-slate-950" : "bg-white/10 hover:bg-white/20",
            ].join(" ")}
          >
            <Icon size={17} />
            {tab.label}
          </button>
        );
      })}
    </div>
  );
}
