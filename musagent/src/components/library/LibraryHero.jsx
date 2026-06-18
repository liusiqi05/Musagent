import { Link } from 'react-router-dom';
import { ROUTES } from '../../config/routes.js';

const StatBlock = ({ value, label, sub }) => (
  <div className="library-stat">
    <span className="library-stat__value font-cjk">{value}</span>
    <span className="library-stat__label">{label}</span>
    {sub && <span className="library-stat__sub">{sub}</span>}
  </div>
);

const LibraryHero = ({ stats, searchMode }) => {
  const total = stats.total || 5320;
  const modern = stats.modern || 0;
  const classical = stats.classical || 0;
  const modernPct = total ? Math.round((modern / total) * 100) : 0;

  return (
    <section className="library-hero">
      <div className="library-hero__bg" aria-hidden>
        <svg className="library-hero__moon" viewBox="0 0 120 120" fill="none">
          <circle cx="60" cy="60" r="48" stroke="rgba(231,211,147,0.15)" strokeWidth="1" />
          <path
            d="M72 24c-22 4-36 22-36 42s14 38 36 42c-8-10-12-22-12-34s4-24 12-34z"
            fill="rgba(231,211,147,0.08)"
            stroke="rgba(231,211,147,0.2)"
            strokeWidth="0.8"
          />
        </svg>
        <svg className="library-hero__scroll" viewBox="0 0 200 80" fill="none">
          <path d="M20 40 Q50 20 100 40 T180 40" stroke="rgba(201,168,76,0.12)" strokeWidth="1.5" fill="none" />
          <path d="M25 50 Q55 65 100 50 T175 50" stroke="rgba(201,168,76,0.08)" strokeWidth="1" fill="none" />
        </svg>
      </div>

      <div className="library-hero__inner">
        <div className="library-hero__copy">
          <p className="badge inline-block mb-4 px-4 py-1.5 rounded-full text-xs tracking-widest">知识库</p>
          <h1 className="library-hero__title font-cjk">诗词典藏</h1>
          <p className="library-hero__desc font-cjk">
            {total.toLocaleString()} 首现代诗与古典诗词 · BM25 + BGE 语义检索 · 按情感浏览
          </p>
          <div className="library-hero__links">
            <Link to={ROUTES.inspire.path} className="library-hero__cta library-hero__cta--primary">
              以此寻灵感
            </Link>
            <Link to={ROUTES.knowledgeGraph.path} className="library-hero__cta">
              意象关系图谱 →
            </Link>
          </div>
        </div>

        <div className="library-hero__stats panel-card">
          <StatBlock value={total.toLocaleString()} label="收录诗篇" sub="本地 SQLite 缓存" />
          <div className="library-stat-divider" />
          <StatBlock value={modern.toLocaleString()} label="现代诗" />
          <StatBlock value={classical.toLocaleString()} label="古典诗词" />
          <div className="library-ratio">
            <div className="library-ratio__bar">
              <span className="library-ratio__modern" style={{ width: `${modernPct}%` }} />
              <span className="library-ratio__classical" style={{ width: `${100 - modernPct}%` }} />
            </div>
            <p className="library-ratio__hint text-[10px]">
              现代 {modernPct}% · 古典 {100 - modernPct}%
            </p>
          </div>
          <p className="library-hero__mode text-[10px] mt-3 opacity-70">
            当前检索：{searchMode === 'hybrid' ? '混合（推荐）' : searchMode === 'semantic' ? '语义相近' : '关键词'}
          </p>
        </div>
      </div>
    </section>
  );
};

export default LibraryHero;
