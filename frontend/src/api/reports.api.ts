import client from "./client";
import type { CheapestVehicle } from "./vehicles.api";

export interface CheapestReport {
  day: "today" | "yesterday";
  count: number;
  items: CheapestVehicle[];
}

export async function getCheapestReport(day: "today" | "yesterday" = "today"): Promise<CheapestReport> {
  const response = await client.get<CheapestReport>("/reports/cheapest", {
    params: { day },
  });
  return response.data;
}

export function cheapestExcelUrl(day: "today" | "yesterday" = "today"): string {
  const baseUrl = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000/api";
  return `${baseUrl}/reports/cheapest.xlsx?day=${day}`;
}
