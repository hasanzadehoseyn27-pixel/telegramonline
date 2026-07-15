import client from "./client";

export interface VehicleFilterOption {
  key: string;
  name: string;
  count: number;
}

export interface FilterOptions {
  vehicles: VehicleFilterOption[];
  years: { year: number; count: number }[];
  colors: { color: string; count: number }[];
  ranges: {
    min_price: number;
    max_price: number;
    min_mileage: number;
    max_mileage: number;
  };
  counts: {
    priced: number;
    unpriced: number;
    used: number;
    buyers: number;
  };
}

export async function getFilterOptions(): Promise<FilterOptions> {
  const response = await client.get<FilterOptions>("/filters/options");
  return response.data;
}
