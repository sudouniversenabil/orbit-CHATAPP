export interface ModelInfo {
  id: string;
  name: string;
  model: string;
  available: boolean;
  active: boolean;
  detail: string | null;
}

export interface CommandInfo {
  id: string;
  name: string;
  description: string;
  examples: string[];
}

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!response.ok) {
    const body = (await response.json().catch(() => ({}))) as { detail?: string };
    throw new Error(body.detail ?? `Request failed (${response.status})`);
  }
  return (await response.json()) as T;
}

export const api = {
  baseUrl: API_BASE,
  health: () => request<{ status: string; app: string }>("/health"),
  models: () => request<ModelInfo[]>("/models"),
  commands: () => request<CommandInfo[]>("/commands"),
  selectModel: (provider_id: string) =>
    request<{ active_provider: string; model: string }>("/models/select", {
      method: "POST",
      body: JSON.stringify({ provider_id }),
    }),
};
