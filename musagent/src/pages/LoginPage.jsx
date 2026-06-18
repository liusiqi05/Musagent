import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext.jsx';
import PageHeader from '../components/PageHeader.jsx';
import { ROUTES } from '../config/routes.js';

const LoginPage = () => {
  const navigate = useNavigate();
  const { login, register, isLoggedIn } = useAuth();
  const [mode, setMode] = useState('login');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [email, setEmail] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  if (isLoggedIn) {
    navigate(ROUTES.inspire.path, { replace: true });
    return null;
  }

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setBusy(true);
    try {
      if (mode === 'login') {
        await login(username.trim(), password);
      } else {
        await register({ username: username.trim(), password, email: email.trim() });
      }
      navigate(ROUTES.inspire.path);
    } catch (err) {
      setError(err.message || '操作失败');
    }
    setBusy(false);
  };

  return (
    <section className="page-auth page-manuscript min-h-dvh pt-28 pb-16">
      <div className="container mx-auto px-5 max-w-md">
        <PageHeader
          badge="账号"
          title={mode === 'login' ? '登录 MusAgent' : '注册账号'}
          description="登录后对话与创作记录可跨设备同步，不再只绑本机浏览器。"
        />

        <form onSubmit={handleSubmit} className="auth-card panel-card space-y-4">
          <div>
            <label className="block text-xs mb-2 font-cjk" style={{ color: 'var(--text-muted)' }}>用户名</label>
            <input
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full px-4 py-3 rounded-xl text-sm kg-input font-cjk"
              required
              minLength={2}
            />
          </div>
          {mode === 'register' && (
            <div>
              <label className="block text-xs mb-2 font-cjk" style={{ color: 'var(--text-muted)' }}>邮箱（可选）</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-4 py-3 rounded-xl text-sm kg-input font-cjk"
              />
            </div>
          )}
          <div>
            <label className="block text-xs mb-2 font-cjk" style={{ color: 'var(--text-muted)' }}>密码</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-4 py-3 rounded-xl text-sm kg-input font-cjk"
              required
              minLength={6}
            />
          </div>
          {error && <p className="text-xs text-red-300 font-cjk">{error}</p>}
          <button type="submit" disabled={busy} className="w-full py-3 rounded-xl bg-yellow text-black font-semibold font-cjk disabled:opacity-50">
            {busy ? '处理中…' : mode === 'login' ? '登录' : '注册并登录'}
          </button>
          <button
            type="button"
            onClick={() => { setMode(mode === 'login' ? 'register' : 'login'); setError(''); }}
            className="w-full text-xs font-cjk"
            style={{ color: 'var(--text-muted)' }}
          >
            {mode === 'login' ? '没有账号？去注册' : '已有账号？去登录'}
          </button>
        </form>

        <p className="text-center mt-6 text-xs font-cjk" style={{ color: 'var(--text-muted)' }}>
          暂不登录也可使用 · <Link to={ROUTES.inspire.path} className="text-yellow hover:underline">继续创作</Link>
        </p>
      </div>
    </section>
  );
};

export default LoginPage;
