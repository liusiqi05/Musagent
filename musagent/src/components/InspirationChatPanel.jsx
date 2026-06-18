import { useCallback, useEffect, useRef, useState } from 'react';
import FeedbackPanel from './FeedbackPanel.jsx';
import {
  chatWithInspiration,
  fetchChatSessions,
  createChatSession,
  fetchChatSession,
  deleteChatSession,
  checkBackend,
} from '../nlp/api.js';
import {
  getChatClientId,
  getActiveChatSessionId,
  setActiveChatSessionId,
  formatSessionTime,
  loadLocalChatBackup,
  saveLocalChatBackup,
} from '../utils/chatClient.js';

const EMPTY_WELCOME = {
  role: 'assistant',
  content: '嘿，我是灵感菌～你可以分享情绪、聊聊灵感，或者只是……说说话。对话会自动保存，下次回来还能接着聊。',
  nlp: null,
  isWelcome: true,
};

export default function InspirationChatPanel({ onApplyTopic }) {
  const clientIdRef = useRef(getChatClientId());
  const chatEndRef = useRef(null);

  const [sessions, setSessions] = useState([]);
  const [activeSessionId, setActiveSessionId] = useState('');
  const [messages, setMessages] = useState([]);
  const [chatInput, setChatInput] = useState('');
  const [chatLoading, setChatLoading] = useState(false);
  const [loadingSessions, setLoadingSessions] = useState(true);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [error, setError] = useState('');

  const clientId = clientIdRef.current;

  const refreshSessions = useCallback(async () => {
    const ok = await checkBackend();
    if (!ok) {
      const backup = loadLocalChatBackup(clientId);
      setSessions(backup.sessions || []);
      return backup.sessions || [];
    }
    const data = await fetchChatSessions(clientId);
    setSessions(data.sessions || []);
    return data.sessions || [];
  }, [clientId]);

  const loadSession = useCallback(async (sessionId) => {
    if (!sessionId) {
      setMessages([]);
      setActiveSessionId('');
      setActiveChatSessionId('');
      return;
    }
    setError('');
    setActiveSessionId(sessionId);
    setActiveChatSessionId(sessionId);
    const ok = await checkBackend();
    if (!ok) {
      const backup = loadLocalChatBackup(clientId);
      const found = (backup.sessions || []).find((s) => s.id === sessionId);
      setMessages(found?.messages || []);
      return;
    }
    try {
      const data = await fetchChatSession(sessionId, clientId);
      setMessages(data.messages || []);
    } catch (err) {
      setError(err.message || '加载对话失败');
      setMessages([]);
    }
  }, [clientId]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoadingSessions(true);
      try {
        const list = await refreshSessions();
        if (cancelled) return;
        const stored = getActiveChatSessionId();
        const pick = stored && list.some((s) => s.id === stored)
          ? stored
          : list[0]?.id;
        if (pick) {
          await loadSession(pick);
        }
      } catch (err) {
        if (!cancelled) setError(err.message || '无法加载历史对话');
      } finally {
        if (!cancelled) setLoadingSessions(false);
      }
    })();
    return () => { cancelled = true; };
  }, [refreshSessions, loadSession]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, chatLoading]);

  const backupToLocal = (sessionList, sessionId, msgs) => {
    const backup = loadLocalChatBackup(clientId);
    const others = (backup.sessions || []).filter((s) => s.id !== sessionId);
    const meta = sessionList.find((s) => s.id === sessionId) || {
      id: sessionId,
      title: msgs.find((m) => m.role === 'user')?.content?.slice(0, 28) || '新对话',
      updatedAt: new Date().toISOString(),
      messageCount: msgs.length,
    };
    saveLocalChatBackup(clientId, {
      sessions: [{ ...meta, messages: msgs }, ...others].slice(0, 30),
    });
  };

  const handleNewChat = async () => {
    setError('');
    setChatInput('');
    const ok = await checkBackend();
    if (ok) {
      try {
        const created = await createChatSession(clientId);
        await refreshSessions();
        setMessages([]);
        setActiveSessionId(created.id);
        setActiveChatSessionId(created.id);
        setSidebarOpen(false);
        return;
      } catch (err) {
        setError(err.message);
      }
    }
    const localId = `local-${Date.now()}`;
    setActiveSessionId(localId);
    setActiveChatSessionId(localId);
    setMessages([]);
    setSessions((prev) => [{ id: localId, title: '新对话', messageCount: 0, updatedAt: new Date().toISOString() }, ...prev]);
    setSidebarOpen(false);
  };

  const handleDeleteSession = async (sessionId, e) => {
    e.stopPropagation();
    if (!window.confirm('确定删除这条对话记录？')) return;
    const ok = await checkBackend();
    if (ok && !sessionId.startsWith('local-')) {
      try {
        await deleteChatSession(sessionId, clientId);
      } catch {
        /* continue local cleanup */
      }
    }
    const next = sessions.filter((s) => s.id !== sessionId);
    setSessions(next);
    saveLocalChatBackup(clientId, { sessions: next });
    if (activeSessionId === sessionId) {
      if (next[0]?.id) {
        await loadSession(next[0].id);
      } else {
        await handleNewChat();
      }
    }
  };

  const handleSelectSession = async (sessionId) => {
    await loadSession(sessionId);
    setSidebarOpen(false);
  };

  const handleSendMessage = async () => {
    const text = chatInput.trim();
    if (!text || chatLoading) return;
    setChatInput('');
    setChatLoading(true);
    setError('');

    let sessionId = activeSessionId;
    const ok = await checkBackend();

    if (ok && !sessionId) {
      try {
        const created = await createChatSession(clientId);
        sessionId = created.id;
        setActiveSessionId(sessionId);
        setActiveChatSessionId(sessionId);
      } catch (err) {
        setError(err.message);
        setChatLoading(false);
        return;
      }
    }

    if (!sessionId) {
      sessionId = `local-${Date.now()}`;
      setActiveSessionId(sessionId);
      setActiveChatSessionId(sessionId);
    }

    const userMsg = { role: 'user', content: text, nlp: null };
    setMessages((prev) => [...prev.filter((m) => !m.isWelcome), userMsg]);

    try {
      const res = await chatWithInspiration(text, {
        sessionId: sessionId.startsWith('local-') ? '' : sessionId,
        clientId,
        history: messages.filter((m) => !m.isWelcome).map((m) => ({ role: m.role, content: m.content })),
      });

      if (res.sessionId && res.sessionId !== sessionId) {
        sessionId = res.sessionId;
        setActiveSessionId(sessionId);
        setActiveChatSessionId(sessionId);
      }

      const assistantMsg = {
        role: 'assistant',
        content: res.reply,
        llmUsed: res.llmUsed,
        nlp: res.nlp || null,
      };

      setMessages((prev) => {
        const base = prev.filter((m) => !m.isWelcome);
        const next = [...base, assistantMsg];
        if (!ok || sessionId.startsWith('local-')) {
          const title = res.sessionTitle || text.slice(0, 28);
          const meta = { id: sessionId, title, messageCount: next.length, updatedAt: new Date().toISOString() };
          setSessions((sess) => {
            const filtered = sess.filter((s) => s.id !== sessionId);
            const merged = [meta, ...filtered];
            backupToLocal(merged, sessionId, next);
            return merged;
          });
        }
        return next;
      });

      if (ok) {
        await refreshSessions();
      }
    } catch {
      setMessages((prev) => [...prev, {
        role: 'assistant',
        content: '😔 抱歉，我暂时无法回应。请确保后端服务已启动，然后重试。',
        nlp: null,
      }]);
    }
    setChatLoading(false);
  };

  const handleChatKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const applyChatToTopic = (msg, index) => {
    const previousUser = [...messages].slice(0, index).reverse().find((m) => m.role === 'user');
    const terms = (msg.nlp?.keywords || []).slice(0, 4).map((k) => k.keyword);
    const nextTopic = terms.length > 0 ? terms.join(' ') : previousUser?.content || '';
    if (nextTopic && onApplyTopic) {
      onApplyTopic(nextTopic);
    }
  };

  const displayMessages = messages.length === 0 && !loadingSessions
    ? [EMPTY_WELCOME]
    : messages.filter((m) => !m.isWelcome);

  return (
    <div className="chat-panel max-w-5xl mx-auto">
      <div className="info-banner mb-4 font-cjk flex flex-wrap items-center justify-between gap-2">
        <span>对话自动保存，可无限轮续聊。刷新页面或下次打开仍可继续。</span>
        <button
          type="button"
          className="chat-sidebar-toggle lg:hidden text-xs px-3 py-1 rounded-full border"
          style={{ borderColor: 'var(--border-color)', color: 'var(--text-secondary)' }}
          onClick={() => setSidebarOpen((v) => !v)}
        >
          {sidebarOpen ? '收起历史' : '历史对话'}
        </button>
      </div>

      <div className="chat-layout">
        <aside className={`chat-sidebar ${sidebarOpen ? 'is-open' : ''}`}>
          <div className="chat-sidebar-head">
            <h3 className="font-cjk text-sm font-semibold">历史对话</h3>
            <button type="button" className="chat-new-btn" onClick={handleNewChat}>+ 新对话</button>
          </div>
          <div className="chat-session-list">
            {loadingSessions && <p className="text-xs p-3 font-cjk" style={{ color: 'var(--text-muted)' }}>加载中…</p>}
            {!loadingSessions && sessions.length === 0 && (
              <p className="text-xs p-3 font-cjk" style={{ color: 'var(--text-muted)' }}>暂无记录，发送第一条消息开始吧</p>
            )}
            {sessions.map((s) => (
              <button
                key={s.id}
                type="button"
                className={`chat-session-item ${activeSessionId === s.id ? 'is-active' : ''}`}
                onClick={() => handleSelectSession(s.id)}
              >
                <span className="chat-session-title font-cjk">{s.title || '新对话'}</span>
                <span className="chat-session-meta">
                  {formatSessionTime(s.updatedAt)}
                  {s.messageCount ? ` · ${s.messageCount} 条` : ''}
                </span>
                <span
                  role="button"
                  tabIndex={0}
                  className="chat-session-delete"
                  onClick={(e) => handleDeleteSession(s.id, e)}
                  onKeyDown={(e) => e.key === 'Enter' && handleDeleteSession(s.id, e)}
                  aria-label="删除对话"
                >
                  ✕
                </span>
              </button>
            ))}
          </div>
        </aside>

        <div className="chat-main rounded-2xl overflow-hidden" style={{ backgroundColor: 'var(--bg-card)', border: '1px solid var(--border-color)' }}>
          {error && (
            <p className="text-xs px-4 py-2 text-red-300 bg-red-500/10 font-cjk">{error}</p>
          )}
          <div className="h-[min(60vh,480px)] overflow-y-auto p-4 space-y-4">
            {(displayMessages.length === 0 && !loadingSessions) ? (
              <div className="flex-center h-full">
                <div className="text-center">
                  <span className="text-4xl block mb-3">🍄</span>
                  <p className="font-cjk" style={{ color: 'var(--text-secondary)' }}>开始和灵感菌对话吧</p>
                </div>
              </div>
            ) : (
              displayMessages.map((msg, i) => (
                <div key={msg.id || i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  <div className={`max-w-[80%] ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
                    <div
                      className={`px-4 py-3 rounded-2xl text-sm leading-relaxed font-cjk ${
                        msg.role === 'user' ? 'bg-yellow text-black rounded-br-md' : 'rounded-bl-md'
                      }`}
                      style={msg.role !== 'user' ? { backgroundColor: 'var(--bg-secondary)', color: 'var(--text-primary)', border: '1px solid var(--border-color)' } : {}}
                    >
                      {msg.content}
                    </div>
                    {msg.role === 'assistant' && msg.nlp && !msg.isWelcome && (
                      <>
                        <div className="flex flex-wrap gap-1.5 mt-1.5">
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-cjk" style={{ backgroundColor: 'rgba(231,211,147,0.15)', color: '#e7d393' }}>
                            {msg.nlp.emotion?.dominant || '未知'}
                          </span>
                          {(msg.nlp.keywords || []).slice(0, 3).map((k, ki) => (
                            <span key={ki} className="px-2 py-0.5 rounded-full text-[10px] font-cjk" style={{ backgroundColor: 'var(--bg-secondary)', color: 'var(--text-muted)' }}>
                              #{k.keyword}
                            </span>
                          ))}
                        </div>
                        <button
                          type="button"
                          onClick={() => applyChatToTopic(msg, i)}
                          className="mt-2 px-3 py-1 rounded-full text-[10px] bg-yellow text-black font-cjk"
                        >
                          用这段对话生成灵感
                        </button>
                        <div className="mt-2">
                          <FeedbackPanel
                            sourceType="chat"
                            qaMode
                            topic={messages[i - 1]?.content || ''}
                            question={messages[i - 1]?.content || ''}
                            answer={msg.content}
                            contentPreview={msg.content}
                          />
                        </div>
                      </>
                    )}
                  </div>
                </div>
              ))
            )}
            {chatLoading && (
              <div className="flex justify-start">
                <div className="px-4 py-3 rounded-2xl rounded-bl-md text-sm" style={{ backgroundColor: 'var(--bg-secondary)', border: '1px solid var(--border-color)' }}>
                  <span className="inline-flex gap-1">
                    <span className="w-2 h-2 rounded-full bg-yellow animate-pulse" />
                    <span className="w-2 h-2 rounded-full bg-yellow animate-pulse" style={{ animationDelay: '150ms' }} />
                    <span className="w-2 h-2 rounded-full bg-yellow animate-pulse" style={{ animationDelay: '300ms' }} />
                  </span>
                </div>
              </div>
            )}
            <div ref={chatEndRef} />
          </div>

          <div className="p-3" style={{ borderTop: '1px solid var(--border-color)' }}>
            <div className="flex gap-2">
              <input
                type="text"
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                onKeyDown={handleChatKeyDown}
                placeholder="分享你的情绪或灵感想法……"
                disabled={chatLoading}
                className="flex-1 px-4 py-2.5 rounded-xl text-sm focus:outline-none disabled:opacity-50 font-cjk"
                style={{
                  backgroundColor: 'var(--bg-secondary)',
                  color: 'var(--text-primary)',
                  border: '1px solid var(--border-color)',
                }}
              />
              <button
                type="button"
                onClick={handleSendMessage}
                disabled={chatLoading || !chatInput.trim()}
                className="px-5 py-2.5 rounded-xl bg-yellow text-black font-medium text-sm hover:opacity-80 transition-opacity disabled:opacity-40 cursor-pointer font-cjk"
              >
                发送
              </button>
            </div>
            <p className="text-[10px] mt-1.5 text-center font-cjk" style={{ color: 'var(--text-muted)' }}>
              按 Enter 发送 · 对话已自动保存
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
