import { useQuery } from "@tanstack/react-query";

import { getAdDetail } from "../api/ads.api";

export function useAdDetail(id?: number) {
  return useQuery({
    queryKey: ["ad-detail", id],

    queryFn: () => {
      if (!id) {
        throw new Error("Ad id is required");
      }

      return getAdDetail(id);
    },

    enabled: Boolean(id),
  });
}
