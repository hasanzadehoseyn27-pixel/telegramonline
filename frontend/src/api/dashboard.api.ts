import client from "./client";
import type { CheapestVehicle } from "./vehicles.api";

export interface DashboardData {
  today: {
    total_ads: number;
    priced: number;
    unpriced: number;
    used: number;
    buyers: number;
  };
  channels: {
    active: number;
    messages_today: number;
  };
  alerts: {
    count: number;
  };
  cheapest: CheapestVehicle[];
}

export async function getDashboard(): Promise<DashboardData> {
  const response = await client.get<DashboardData>("/dashboard");
  return response.data;
}
