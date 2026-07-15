import client from "./client";

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
}

export async function getLiveCheapestVehicles(limit = 100): Promise<CheapestVehicle[]> {
  const response = await client.get<CheapestVehicle[]>("/vehicles/cheapest/live", {
    params: { limit },
  });
  return response.data;
}
