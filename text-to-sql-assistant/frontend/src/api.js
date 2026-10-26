/**
 * Thin fetch wrapper around the FastAPI backend (api.py). Keeps all
 * endpoint knowledge and the base URL resolution in one place so
 * components don't repeat fetch boilerplate.
 */
const API_BASE_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

async function handleResponse(resp) {
  if (!resp.ok) {
    let detail = resp.statusText;
    try {
      const body = await resp.json();
      detail = body.detail ? JSON.stringify(body.detail) : detail;
    } catch {
      // response wasn't JSON; fall back to statusText
    }
    throw new Error(`${resp.status} ${detail}`);
  }
  return resp.json();
}

export async function fetchHealth() {
  const resp = await fetch(`${API_BASE_URL}/health`);
  return handleResponse(resp);
}

export async function fetchSchema() {
  const resp = await fetch(`${API_BASE_URL}/schema`);
  return handleResponse(resp);
}

export async function askQuestion(question) {
  const resp = await fetch(`${API_BASE_URL}/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
  return handleResponse(resp);
}

export { API_BASE_URL };
