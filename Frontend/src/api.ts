
const API_URL =
  import.meta.env.VITE_API_URL || "http://127.0.0.1:5000";

export async function apiRequest(
  path: string,
  options: RequestInit = {}
) {
  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    credentials: "include",
    headers: {
      ...(options.headers || {}),
    },
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(data.error || `Request failed: ${response.status}`);
  }

  return data;
}
