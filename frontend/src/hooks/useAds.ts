import { useQuery } from "@tanstack/react-query";

import {
  getPricedAds,
  getUnpricedAds,
  getUsedAds,
  getBuyerAds,
  type AdsResponse,
} from "../api/ads.api";

import type { AdsParams } from "../types/ads";

import type { AdsTab } from "../store/adsStore";

export function useAds(
  tab: AdsTab,

  params?: AdsParams
) {
  return useQuery<AdsResponse>({
    queryKey: ["ads", tab, params],

    queryFn: () => {
      switch (tab) {
        case "unpriced":
          return getUnpricedAds(params);

        case "used":
          return getUsedAds(params);

        case "buyers":
          return getBuyerAds(params);

        default:
          return getPricedAds(params);
      }
    },

    refetchInterval: 5000,
  });
}
