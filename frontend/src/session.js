const SESSION_KEY = "datapro_customer_chat_session_id";

export function getOrCreateSessionId() {
  let sessionId = localStorage.getItem(SESSION_KEY);

  if (!sessionId) {
    sessionId = createSessionId();
    localStorage.setItem(SESSION_KEY, sessionId);
  }

  return sessionId;
}

export function resetSessionId() {
  const newSessionId = createSessionId();
  localStorage.setItem(SESSION_KEY, newSessionId);
  return newSessionId;
}

function createSessionId() {
  return (
    window.crypto?.randomUUID?.() ||
    `session-${Date.now()}-${Math.random().toString(16).slice(2)}`
  );
}
