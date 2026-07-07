const API_BASE_URL = "";

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `API error: ${response.status}`);
  }

  return response.json();
}

export async function sendChatMessage({ sessionId, message }) {
  return request("/api/chat", {
    method: "POST",
    body: JSON.stringify({
      session_id: sessionId,
      message,
    }),
  });
}

export async function endSession({ sessionId, rating }) {
  return request("/api/end_session", {
    method: "POST",
    body: JSON.stringify({
      session_id: sessionId,
      rating,
    }),
  });
}

export async function fetchInsights() {
  return request("/api/insights");
}
