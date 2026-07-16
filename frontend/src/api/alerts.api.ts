import client from "./client";

export type AlertCondition = "lt" | "gt" | "between" | "less_than" | "greater_than";

export interface PriceAlert {
  id: number;
  user_id: number;
  vehicle_key: string;
  vehicle_name: string | null;
  condition: AlertCondition | string;
  min_price: number | null;
  max_price: number | null;
  active: boolean;
  created_at: string;
}

export interface AlertEvent {
  id: number;
  alert_id: number;
  ad_id: number;
  vehicle_key: string | null;
  vehicle_name: string | null;
  condition: string | null;
  price_million: number | null;
  channel_username: string | null;
  source_message_id: string | null;
  raw_text: string | null;
  created_at: string;
  telegram_link: string | null;
}

export interface AlertPayload {
  user_id: number;
  vehicle_key: string;
  vehicle_name?: string | null;
  condition: string;
  min_price?: number;
  max_price?: number;
}

export async function getAlerts(userId = 1): Promise<PriceAlert[]> {
  const response = await client.get<PriceAlert[]>("/alerts", {
    params: { user_id: userId },
  });
  return response.data;
}

export async function createAlert(payload: AlertPayload): Promise<PriceAlert> {
  const response = await client.post<PriceAlert>("/alerts", payload);
  return response.data;
}

export async function removeAlert(id: number): Promise<{ ok: boolean }> {
  const response = await client.delete<{ ok: boolean }>(`/alerts/${id}`);
  return response.data;
}

export async function toggleAlert(id: number): Promise<{ ok: boolean; active: boolean }> {
  const response = await client.patch<{ ok: boolean; active: boolean }>(`/alerts/${id}/toggle`);
  return response.data;
}

export async function getAlertEvents(): Promise<AlertEvent[]> {
  const response = await client.get<AlertEvent[]>("/alerts/events", {
    params: { limit: 100, offset: 0 },
  });
  return response.data;
}

export async function getAlertEventsCount(): Promise<number> {
  const response = await client.get<{ count: number }>("/alerts/events/count");
  return response.data.count;
}

export async function markAlertEventsRead(): Promise<{ ok: boolean; marked: number }> {
  const response = await client.post<{ ok: boolean; marked: number }>("/alerts/events/mark-read");
  return response.data;
}

export async function removeAllAlerts(userId = 1): Promise<{ ok: boolean; deleted: number }> {
  const response = await client.delete<{ ok: boolean; deleted: number }>("/alerts", {
    params: { user_id: userId },
  });
  return response.data;
}
