import client from "./client";

export interface Channel {
  id: number;
  username: string;
  title: string | null;
  active: boolean;
  joined: boolean;
  added_at: string | null;
  message_count?: number;
  today_messages?: number;
}

export interface ChannelLiveResponse {
  channels: Channel[];
  summary: {
    active_channels: number;
    messages_today: number;
  };
}

export interface ChannelActionResponse {
  ok: boolean;
  message: string;
  channel_id?: number | null;
}

export async function getChannels(): Promise<Channel[]> {
  const response = await client.get<Channel[]>("/channels");
  return response.data;
}

export async function getLiveChannels(): Promise<ChannelLiveResponse> {
  const response = await client.get<ChannelLiveResponse>("/channels/live");
  return response.data;
}

export async function addChannel(username: string): Promise<ChannelActionResponse> {
  const response = await client.post<ChannelActionResponse>("/channels", { username });
  return response.data;
}

export async function deleteChannel(id: number): Promise<ChannelActionResponse> {
  const response = await client.delete<ChannelActionResponse>(`/channels/${id}`);
  return response.data;
}
