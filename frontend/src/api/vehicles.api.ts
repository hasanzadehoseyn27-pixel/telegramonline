import client from "./client";
import type { Ad } from "./ads.api";

export interface CheapestVehicle {
  id: number;
  vehicle_key: string | null;
  vehicle_name: string | null;
  price_million: number;
  year: number | null;
  month: number | null;
  color: string | null;
  mileage_km?: number | null;
  phone: string | null;
  channel_username: string | null;
  source_message_id?: string | null;
  message_date: string | null;
  telegram_link: string | null;
  ad_count: number;
}

export interface CheapestLivePage {
  items: CheapestVehicle[];
  total: number;
  limit: number;
  offset: number;
}

export async function getLiveCheapestVehicles(limit = 100, offset = 0): Promise<CheapestLivePage> {
  const response = await client.get<CheapestLivePage>("/vehicles/cheapest/live", {
    params: { limit, offset },
  });
  return response.data;
}

export async function getAdsForModel(vehicleKey: string): Promise<Ad[]> {
  const response = await client.get<Ad[]>("/vehicles/for-model", {
    params: { vehicle_key: vehicleKey },
  });
  return response.data;
}
