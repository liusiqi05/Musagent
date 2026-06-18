const CLIENT_KEY = 'musagent:clientId';
const ACTIVE_SESSION_KEY = 'musagent:activeChatSession';

export function getChatClientId() {
  let id = localStorage.getItem(CLIENT_KEY);
  if (!id) {
    id = crypto.randomUUID();
    localStorage.setItem(CLIENT_KEY, id);
  }
  return id;
}

export function getActiveChatSessionId() {
  return localStorage.getItem(ACTIVE_SESSION_KEY) || '';
}

export function setActiveChatSessionId(sessionId) {
  if (sessionId) {
    localStorage.setItem(ACTIVE_SESSION_KEY, sessionId);
  } else {
    localStorage.removeItem(ACTIVE_SESSION_KEY);
  }
}

const LOCAL_BACKUP_KEY = 'musagent:chatBackup';

export function loadLocalChatBackup(clientId) {
  try {
    const raw = localStorage.getItem(LOCAL_BACKUP_KEY);
    if (!raw) return { sessions: [] };
    const data = JSON.parse(raw);
    return data[clientId] || { sessions: [] };
  } catch {
    return { sessions: [] };
  }
}

export function saveLocalChatBackup(clientId, payload) {
  try {
    const raw = localStorage.getItem(LOCAL_BACKUP_KEY);
    const all = raw ? JSON.parse(raw) : {};
    all[clientId] = payload;
    localStorage.setItem(LOCAL_BACKUP_KEY, JSON.stringify(all));
  } catch {
    /* ignore quota errors */
  }
}

export function formatSessionTime(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  const now = new Date();
  const sameDay = d.toDateString() === now.toDateString();
  if (sameDay) {
    return d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
  }
  return d.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' });
}
