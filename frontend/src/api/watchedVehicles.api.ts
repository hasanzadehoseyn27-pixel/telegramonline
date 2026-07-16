import client from "./client";
import type { Ad, AdsResponse } from "./ads.api";

export interface WatchedVehicle {
  id: number;
  vehicle_key: string;
  vehicle_name: string | null;
  added_at: string;
}

export async function getWatchedVehicles(): Promise<WatchedVehicle[]> {
  const response = await client.get<WatchedVehicle[]>("/watched-vehicles");
  return response.data;
}

export async function addWatchedVehicle(payload: {
  vehicle_key: string;
  vehicle_name?: string | null;
}): Promise<WatchedVehicle> {
  const response = await client.post<WatchedVehicle>("/watched-vehicles", payload);
  return response.data;
}

export async function removeWatchedVehicle(id: number): Promise<{ ok: boolean }> {
  const response = await client.delete<{ ok: boolean }>(`/watched-vehicles/${id}`);
  return response.data;
}

export async function getSpecialAds(limit = 50, offset = 0): Promise<AdsResponse> {
  const response = await client.get<AdsResponse>("/watched-vehicles/ads", {
    params: { limit, offset },
  });
  return response.data;
}

export type { Ad };
