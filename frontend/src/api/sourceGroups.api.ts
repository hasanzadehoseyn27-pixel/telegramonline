import client from "./client";

export interface SourceGroup {
  id: number;
  username: string;
  title: string | null;
  active: boolean;
  joined: boolean;
  discovered_channels: number;
  added_at: string;
}

export interface SourceGroupActionResponse {
  ok: boolean;
  message: string;
  group_id?: number | null;
}

export async function getSourceGroups(): Promise<SourceGroup[]> {
  const response = await client.get<SourceGroup[]>("/source-groups");
  return response.data;
}

export async function addSourceGroup(username: string): Promise<SourceGroupActionResponse> {
  const response = await client.post<SourceGroupActionResponse>("/source-groups", { username });
  return response.data;
}

export async function deleteSourceGroup(id: number): Promise<SourceGroupActionResponse> {
  const response = await client.delete<SourceGroupActionResponse>(`/source-groups/${id}`);
  return response.data;
}
