import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { fetchMe, loginUser, registerUser } from '../nlp/api.js';
import { getAuthToken, getAuthUser, saveAuth, clearAuth } from '../utils/auth.js';
import { getChatClientId } from '../utils/chatClient.js';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(getAuthUser);
  const [loading, setLoading] = useState(!!getAuthToken());

  const refresh = useCallback(async () => {
    const token = getAuthToken();
    if (!token) {
      setUser(null);
      setLoading(false);
      return null;
    }
    try {
      const data = await fetchMe();
      setUser(data.user);
      saveAuth(token, data.user);
      return data.user;
    } catch {
      clearAuth();
      setUser(null);
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const login = useCallback(async (username, password) => {
    const result = await loginUser({ username, password, clientId: getChatClientId() });
    if (!result.success) throw new Error(result.error || '登录失败');
    saveAuth(result.token, result.user);
    setUser(result.user);
    return result;
  }, []);

  const register = useCallback(async (payload) => {
    const result = await registerUser(payload);
    if (!result.success) throw new Error(result.error || '注册失败');
    saveAuth(result.token, result.user);
    setUser(result.user);
    return result;
  }, []);

  const logout = useCallback(() => {
    clearAuth();
    setUser(null);
  }, []);

  const value = useMemo(() => ({
    user, loading, login, register, logout, refresh, isLoggedIn: !!user,
  }), [user, loading, login, register, logout, refresh]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}

export default AuthContext;
