export type SortMode =
  | "newest"
  | "oldest"
  | "price_asc"
  | "price_desc"
  | "year_desc"
  | "year_asc"
  | "mileage_asc"
  | "mileage_desc";

export interface AdsParams {
  search?: string;
  query?: string;
  minPrice?: number;
  maxPrice?: number;
  minMileage?: number;
  maxMileage?: number;
  vehicle?: string;
  vehicleKeys?: string[];
  colors?: string[];
  years?: number[];
  timeRange?: number;
  day?: "today" | "yesterday";
  sort?: SortMode;
  limit?: number;
  offset?: number;
}
