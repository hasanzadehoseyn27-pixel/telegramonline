import { keepPreviousData, useQuery } from "@tanstack/react-query";

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

    // با تغییر فیلتر/جستجو/صفحه، به‌جای پرش به حالت "loading" (که کل
    // جدول از جمله خودِ اینپوت جستجو رو موقتاً حذف می‌کرد و فوکوس رو
    // می‌بُرد)، داده‌ی قبلی رو نگه می‌داره تا داده‌ی جدید برسه.
    placeholderData: keepPreviousData,

    refetchInterval: 5000,
  });
}
