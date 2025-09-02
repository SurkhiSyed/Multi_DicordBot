export const API_URL =
  process.env.REACT_APP_API_URL || "http://localhost:8000"; // dev fallback

export async function apiFetch(path, options = {}) {
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
  });
  return res;
}
