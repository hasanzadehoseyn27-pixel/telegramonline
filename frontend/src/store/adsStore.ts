import { create } from "zustand";
import type { AdsParams } from "../types/ads";

export type AdsTab = "priced" | "unpriced" | "used" | "buyers";

interface AdsStore {
  activeTab: AdsTab;
  filters: AdsParams;
  setTab: (tab: AdsTab) => void;
  setFilters: (filters: Partial<AdsParams>) => void;
  toggleVehicle: (vehicleKey: string) => void;
  resetFilters: () => void;
}

const defaultFilters: AdsParams = {
  search: "",
  vehicleKeys: [],
  timeRange: 24,
  sort: "newest",
  limit: 200,
  offset: 0,
};

export const useAdsStore = create<AdsStore>((set) => ({
  activeTab: "priced",
  filters: defaultFilters,

  setTab: (tab) => set({ activeTab: tab }),

  setFilters: (filters) =>
    set((state) => ({
      filters: {
        ...state.filters,
        ...filters,
        offset: filters.offset ?? 0,
      },
    })),

  toggleVehicle: (vehicleKey) =>
    set((state) => {
      const current = state.filters.vehicleKeys ?? [];
      const next = current.includes(vehicleKey)
        ? current.filter((item) => item !== vehicleKey)
        : [...current, vehicleKey];

      return {
        filters: {
          ...state.filters,
          vehicleKeys: next,
          offset: 0,
        },
      };
    }),

  resetFilters: () => set({ filters: defaultFilters }),
}));
