import client from "./client";

export interface LoginResponse {
  token: string;
  username: string;
}

export async function login(username: string, password: string): Promise<LoginResponse> {
  const response = await client.post<LoginResponse>("/auth/login", {
    username,
    password,
  });

  localStorage.setItem("telegramonline_token", response.data.token);
  localStorage.setItem("telegramonline_username", response.data.username);

  return response.data;
}

export function logout() {
  localStorage.removeItem("telegramonline_token");
  localStorage.removeItem("telegramonline_username");
}

export function isAuthenticated() {
  return Boolean(localStorage.getItem("telegramonline_token"));
}
