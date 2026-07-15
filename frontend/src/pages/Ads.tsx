import AdsFilters from "../components/filters/AdsFilters";
import AdsTable from "../components/table/AdsTable";

export default function Ads() {
  return (
    <div className="grid h-full min-h-0 grid-cols-[minmax(0,1fr)_300px] gap-4 max-xl:grid-cols-1">
      <div className="min-h-0">
        <AdsTable />
      </div>
      <div className="min-h-0 max-xl:hidden">
        <AdsFilters />
      </div>
    </div>
  );
}
