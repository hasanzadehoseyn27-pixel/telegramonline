import client from "./client";
import type { AdsParams } from "../types/ads";

export interface Ad {
  id: number;
  channel_username: string | null;
  source_message_id: string | null;
  raw_text: string;
  vehicle_key: string | null;
  vehicle_name: string | null;
  trim: string | null;
  price_million: number | null;
  year: number | null;
  month: number | null;
  color: string | null;
  mileage_km: number | null;
  phone: string | null;
  status: string;
  delivery?: string | null;
  confidence?: number;
  message_date: string | null;
  day_key?: string | null;
  telegram_link: string | null;
}

export interface AdsResponse {
  items: Ad[];
  limit: number;
  offset: number;
  count: number;
}

function toApiParams(params?: AdsParams) {
  return {
    query: (params?.query ?? params?.search) || undefined,
    vehicle_keys: params?.vehicleKeys?.length ? params.vehicleKeys : undefined,
    colors: params?.colors?.length ? params.colors : undefined,
    years: params?.years?.length ? params.years : undefined,
    min_price: params?.minPrice,
    max_price: params?.maxPrice,
    min_mileage: params?.minMileage,
    max_mileage: params?.maxMileage,
    sort: params?.sort ?? "newest",
    limit: params?.limit ?? 200,
    offset: params?.offset ?? 0,
  };
}

export async function getPricedAds(params?: AdsParams): Promise<AdsResponse> {
  const response = await client.get<AdsResponse>("/ads/priced", {
    params: toApiParams(params),
  });
  return response.data;
}

export async function getUnpricedAds(params?: AdsParams): Promise<AdsResponse> {
  const response = await client.get<AdsResponse>("/ads/unpriced", {
    params: toApiParams(params),
  });
  return response.data;
}

export async function getUsedAds(params?: AdsParams): Promise<AdsResponse> {
  const response = await client.get<AdsResponse>("/ads/used", {
    params: toApiParams(params),
  });
  return response.data;
}

export async function getBuyerAds(params?: AdsParams): Promise<AdsResponse> {
  const response = await client.get<AdsResponse>("/ads/buyers", {
    params: toApiParams(params),
  });
  return response.data;
}

export async function getAdDetail(id: number): Promise<Ad> {
  const response = await client.get<Ad>(`/ads/${id}`);
  return response.data;
}
