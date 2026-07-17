import client from "./client";

export interface ChannelActivity {
  username: string;
  title: string | null;
  type: "channel" | "group";
  active: boolean;
  car_ads: number;
}

export async function getChannelActivity(
  day: "today" | "yesterday" = "today",
  vehicleKeys?: string[],
): Promise<ChannelActivity[]> {
  const response = await client.get<ChannelActivity[]>("/channels/activity", {
    params: {
      day,
      ...(vehicleKeys && vehicleKeys.length > 0 ? { vehicle_keys: vehicleKeys } : {}),
    },
  });
  return response.data;
}
