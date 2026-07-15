import { useQuery } from "@tanstack/react-query";

import { getDashboard, type DashboardData } from "../api/dashboard.api";

export function useDashboard() {
  return useQuery<DashboardData>({
    queryKey: ["dashboard"],

    queryFn: getDashboard,

    refetchInterval: 5000,
  });
}
