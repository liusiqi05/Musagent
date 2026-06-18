// ========== MusAgent 后端 API 客户端 ==========

import { authHeaders } from '../utils/auth.js';

const API_BASE = 'http://localhost:8000/api';

let backendAvailable = null;

async function apiFetch(path, { method = 'GET', body, timeoutMs = 20000, auth = true } = {}) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const headers = body ? { 'Content-Type': 'application/json', ...(auth ? authHeaders() : {}) } : (auth ? authHeaders() : undefined);
    const resp = await fetch(`${API_BASE}${path}`, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
      signal: controller.signal,
    });
    clearTimeout(timeout);
    if (!resp.ok) {
      const text = await resp.text();
      throw new Error(`API ${resp.status}: ${text.slice(0, 120)}`);
    }
    return resp.json();
  } finally {
    clearTimeout(timeout);
  }
}

/** 检测后端是否可用 */
export async function checkBackend() {
  if (backendAvailable !== null) return backendAvailable;
  try {
    const data = await apiFetch('/health', { timeoutMs: 3000 });
    backendAvailable = data?.status === 'ok';
    console.log(`[API] 后端${backendAvailable ? '已' : '未'}连接`, data?.semanticIndex || '');
  } catch (e) {
    backendAvailable = false;
    console.log('[API] 后端未启动:', e.message);
  }
  return backendAvailable;
}

export async function remotePipeline(params) {
  return apiFetch('/pipeline', { method: 'POST', body: params, timeoutMs: 90000 });
}

export async function remoteRetrieve(words, creationType, text = '', searchMode = 'hybrid') {
  return apiFetch('/retrieve', {
    method: 'POST',
    body: { words, creationType, text, searchMode },
    timeoutMs: 30000,
  });
}

export async function fetchKnowledge({
  page = 1,
  pageSize = 30,
  search = '',
  emotion = 'all',
  poemType = 'all',
  searchMode = 'keyword',
} = {}) {
  const params = new URLSearchParams({
    page: String(page),
    pageSize: String(pageSize),
    search,
    emotion,
    poemType,
    searchMode,
  });
  return apiFetch(`/knowledge?${params.toString()}`, { timeoutMs: 30000 });
}

export async function remoteRegenerate(payload) {
  return apiFetch('/regenerate', { method: 'POST', body: payload, timeoutMs: 60000 });
}

export async function remotePolish(payload) {
  return apiFetch('/polish', { method: 'POST', body: payload, timeoutMs: 60000 });
}

export async function chatWithInspiration(message, { sessionId = '', clientId = '', history = [] } = {}) {
  return apiFetch('/chat', {
    method: 'POST',
    body: { message, history, sessionId, clientId },
    timeoutMs: 30000,
  });
}

export async function fetchChatSessions(clientId) {
  const params = new URLSearchParams({ clientId });
  return apiFetch(`/chat/sessions?${params.toString()}`, { timeoutMs: 10000 });
}

export async function createChatSession(clientId, title = '新对话') {
  return apiFetch('/chat/sessions', {
    method: 'POST',
    body: { clientId, title },
    timeoutMs: 10000,
  });
}

export async function fetchChatSession(sessionId, clientId) {
  const params = new URLSearchParams({ clientId });
  return apiFetch(`/chat/sessions/${sessionId}?${params.toString()}`, { timeoutMs: 15000 });
}

export async function deleteChatSession(sessionId, clientId) {
  const params = new URLSearchParams({ clientId });
  return apiFetch(`/chat/sessions/${sessionId}?${params.toString()}`, { method: 'DELETE', timeoutMs: 10000 });
}

export async function remoteSummarize(text, topN = 3) {
  return apiFetch('/summarize', { method: 'POST', body: { text, top_n: topN }, timeoutMs: 30000 });
}

export async function remoteCorrect(text) {
  return apiFetch('/correct', { method: 'POST', body: { text }, timeoutMs: 20000 });
}

export async function remoteSemanticSearch(query, topN = 10, poemType = 'all') {
  return apiFetch('/semantic-search', {
    method: 'POST',
    body: { query, top_n: topN, poemType },
    timeoutMs: 30000,
  });
}

export async function fetchEvaluation() {
  return apiFetch('/evaluate', { timeoutMs: 60000 });
}

export async function fetchStack() {
  return apiFetch('/stack', { timeoutMs: 5000 });
}

export async function fetchHealth() {
  return apiFetch('/health', { timeoutMs: 5000 });
}

export async function submitFeedback(payload) {
  return apiFetch('/feedback', { method: 'POST', body: payload, timeoutMs: 10000 });
}

export async function submitQAFeedback(payload) {
  return apiFetch('/feedback/qa', { method: 'POST', body: payload, timeoutMs: 10000 });
}

export async function fetchFeedbackStats() {
  return apiFetch('/feedback/stats', { timeoutMs: 5000 });
}

export async function fetchFeedbackInsights() {
  return apiFetch('/feedback/insights', { timeoutMs: 5000 });
}

export async function fetchKnowledgeGraph(limit = 80, entity = '') {
  const params = new URLSearchParams({ limit: String(limit), entity });
  return apiFetch(`/knowledge-graph?${params.toString()}`, { timeoutMs: 15000 });
}

export async function fetchConfig() {
  return apiFetch('/config', { timeoutMs: 5000 });
}

export async function fetchReModelStatus() {
  return apiFetch('/kg/re-model', { timeoutMs: 5000 });
}

export async function trainReModel({ epochs = 2, limit = 1200, batchSize = 16 } = {}) {
  return apiFetch('/kg/train-re', {
    method: 'POST',
    body: { epochs, limit, batchSize },
    timeoutMs: 600000,
  });
}

export async function exportReSamples(limit = 500) {
  return apiFetch(`/kg/export-re-samples?limit=${limit}`, { timeoutMs: 60000 });
}

export async function registerUser({ username, password, email = '', displayName = '' }) {
  return apiFetch('/auth/register', {
    method: 'POST',
    body: { username, password, email, displayName },
    timeoutMs: 15000,
    auth: false,
  });
}

export async function loginUser({ username, password, clientId = '' }) {
  return apiFetch('/auth/login', {
    method: 'POST',
    body: { username, password, clientId },
    timeoutMs: 15000,
    auth: false,
  });
}

export async function fetchMe() {
  return apiFetch('/auth/me', { timeoutMs: 8000 });
}

export default {
  checkBackend,
  remotePipeline,
  remoteRetrieve,
  fetchKnowledge,
  remoteRegenerate,
  remotePolish,
  chatWithInspiration,
  fetchChatSessions,
  createChatSession,
  fetchChatSession,
  deleteChatSession,
  remoteSummarize,
  remoteCorrect,
  remoteSemanticSearch,
  fetchEvaluation,
  fetchStack,
  fetchHealth,
  submitFeedback,
  submitQAFeedback,
  fetchFeedbackStats,
  fetchFeedbackInsights,
  fetchKnowledgeGraph,
  fetchConfig,
  fetchReModelStatus,
  trainReModel,
  exportReSamples,
};
