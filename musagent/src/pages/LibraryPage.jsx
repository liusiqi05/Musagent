import { useGSAP } from '@gsap/react';
import gsap from 'gsap';
import { useEffect, useMemo, useState } from 'react';
import EmotionSpectrum from '../components/library/EmotionSpectrum.jsx';
import LibraryHero from '../components/library/LibraryHero.jsx';
import PoemScrollCard from '../components/library/PoemScrollCard.jsx';
import { fetchKnowledge } from '../nlp/api.js';
import { formatAuthor } from '../utils/author.js';

const PER_PAGE = 30;

const EMPTY_STATS = {
  total: 0,
  modern: 0,
  classical: 0,
  emotions: {},
};

const SEARCH_MODES = [
  { key: 'keyword', label: '关键词', hint: '标题、作者、正文 — 速度最快' },
  { key: 'semantic', label: '语义相近', hint: 'BGE 向量理解意思相近的诗词' },
  { key: 'hybrid', label: '混合检索', hint: 'BM25 + 语义并集，探索灵感时推荐' },
];

const TYPE_TABS = [
  { key: 'all', label: '全部体裁' },
  { key: '现代诗', label: '现代诗' },
  { key: '古典诗', label: '古典诗词' },
];

const FeaturedPoem = ({ poem, onOpen }) => {
  if (!poem) return null;
  return (
    <div className="featured-poem panel-card" onClick={() => onOpen(poem.id)} role="button" tabIndex={0}>
      <div className="featured-poem__label font-cjk">今日展卷</div>
      <h2 className="featured-poem__title font-cjk">{poem.title}</h2>
      <p className="featured-poem__meta font-cjk">
        {formatAuthor(poem.author)} · {poem.type} · {poem.emotion}
      </p>
      <p className="featured-poem__excerpt font-cjk line-clamp-4">{poem.content}</p>
      <span className="featured-poem__cta">展卷阅读 →</span>
    </div>
  );
};

const LibraryPage = () => {
  const [poems, setPoems] = useState([]);
  const [stats, setStats] = useState(EMPTY_STATS);
  const [filteredTotal, setFilteredTotal] = useState(0);
  const [hasMore, setHasMore] = useState(false);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState('');
  const [activeEmotion, setActiveEmotion] = useState('all');
  const [activeType, setActiveType] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [searchMode, setSearchMode] = useState('hybrid');
  const [expandedId, setExpandedId] = useState(null);
  const [page, setPage] = useState(1);

  const showFeatured = !searchQuery.trim() && activeEmotion === 'all' && activeType === 'all';
  const featuredPoem = useMemo(() => {
    if (!showFeatured || poems.length === 0) return null;
    const idx = new Date().getDate() % poems.length;
    return poems[idx];
  }, [showFeatured, poems]);

  const gridPoems = useMemo(() => {
    if (!featuredPoem) return poems;
    return poems.filter((p) => p.id !== featuredPoem.id);
  }, [poems, featuredPoem]);

  useEffect(() => {
    let cancelled = false;
    const timer = window.setTimeout(async () => {
      setLoading(true);
      setError('');
      try {
        const data = await fetchKnowledge({
          page: 1,
          pageSize: PER_PAGE,
          search: searchQuery.trim(),
          emotion: activeEmotion,
          poemType: activeType,
          searchMode,
        });
        if (cancelled) return;
        setPoems(data.items || []);
        setStats(data.stats || EMPTY_STATS);
        setFilteredTotal(data.filteredTotal || 0);
        setHasMore(Boolean(data.hasMore));
        setPage(1);
        setExpandedId(null);
      } catch (e) {
        if (cancelled) return;
        setError(e.message || '知识库接口请求失败');
        setPoems([]);
        setFilteredTotal(0);
        setHasMore(false);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }, 250);

    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [searchQuery, activeEmotion, activeType, searchMode]);

  const loadMore = async () => {
    if (loadingMore || !hasMore) return;
    const nextPage = page + 1;
    setLoadingMore(true);
    setError('');
    try {
      const data = await fetchKnowledge({
        page: nextPage,
        pageSize: PER_PAGE,
        search: searchQuery.trim(),
        emotion: activeEmotion,
        poemType: activeType,
        searchMode,
      });
      setPoems((prev) => [...prev, ...(data.items || [])]);
      setFilteredTotal(data.filteredTotal || 0);
      setHasMore(Boolean(data.hasMore));
      setPage(nextPage);
    } catch (e) {
      setError(e.message || '加载更多失败');
    } finally {
      setLoadingMore(false);
    }
  };

  useGSAP(() => {
    gsap.from('.library-hero', { y: 24, opacity: 0, duration: 0.8, ease: 'power2.out' });
    gsap.from('.library-toolbar', { y: 16, opacity: 0, duration: 0.6, ease: 'power2.out', delay: 0.15 });
    gsap.from('.poem-scroll-card', { y: 20, opacity: 0, duration: 0.5, ease: 'power2.out', stagger: 0.03, delay: 0.25 });
  }, [poems.length, loading]);

  return (
    <section className="page-library page-manuscript min-h-dvh pt-24 md:pt-28 pb-20">
      <div className="container mx-auto px-5 2xl:px-0 max-w-6xl">
        {loading && poems.length === 0 ? (
          <div className="library-loading">
            <div className="library-loading__scroll" aria-hidden>
              <span /><span /><span />
            </div>
            <p className="font-cjk text-sm" style={{ color: 'var(--text-secondary)' }}>正在展卷…</p>
            <p className="text-xs mt-2" style={{ color: 'var(--text-muted)' }}>5320 首诗词已缓存至本地数据库</p>
          </div>
        ) : (
          <>
            <LibraryHero stats={stats} searchMode={searchMode} />

            <div className="library-toolbar">
              <div className="library-search panel-card">
                <span className="library-search__icon" aria-hidden>搜</span>
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="寻一句诗、一位诗人、一种心境…"
                  className="library-search__input font-cjk"
                />
                {searchQuery && (
                  <button type="button" className="library-search__clear" onClick={() => setSearchQuery('')}>
                    清除
                  </button>
                )}
              </div>

              <div className="library-mode-tabs">
                {SEARCH_MODES.map((mode) => (
                  <button
                    key={mode.key}
                    type="button"
                    onClick={() => setSearchMode(mode.key)}
                    className={`library-mode-tab ${searchMode === mode.key ? 'library-mode-tab--active' : ''}`}
                    title={mode.hint}
                  >
                    {mode.label}
                  </button>
                ))}
              </div>
              <p className="library-mode-hint text-center text-[11px] font-cjk">
                {SEARCH_MODES.find((m) => m.key === searchMode)?.hint}
              </p>
            </div>

            <EmotionSpectrum
              emotions={stats.emotions}
              active={activeEmotion}
              onSelect={setActiveEmotion}
              total={stats.total}
            />

            <div className="library-type-row">
              {TYPE_TABS.map((tab) => {
                const count = tab.key === '现代诗' ? stats.modern
                  : tab.key === '古典诗' ? stats.classical
                    : stats.total;
                return (
                  <button
                    key={tab.key}
                    type="button"
                    onClick={() => setActiveType(tab.key)}
                    className={`library-type-chip ${activeType === tab.key ? 'library-type-chip--active' : ''}`}
                  >
                    {tab.label}
                    <span className="library-type-chip__n">{count?.toLocaleString?.() ?? count}</span>
                  </button>
                );
              })}
            </div>

            {error && (
              <div className="info-banner mb-8 text-sm">{error} — 请确认后端已在 8000 端口启动</div>
            )}

            {loading && poems.length > 0 && (
              <p className="text-center text-xs mb-6 font-cjk" style={{ color: 'var(--text-muted)' }}>
                正在刷新筛选…
              </p>
            )}

            {poems.length === 0 ? (
              <div className="library-empty inspire-empty-state">
                <span className="library-empty__icon font-cjk">空</span>
                <p className="font-cjk">未寻得相符的诗篇</p>
                <p className="text-xs mt-2" style={{ color: 'var(--text-muted)' }}>试试换个关键词，或点选上方情感光谱</p>
              </div>
            ) : (
              <>
                {featuredPoem && (
                  <FeaturedPoem poem={featuredPoem} onOpen={setExpandedId} />
                )}

                <div className="poem-grid">
                  {gridPoems.map((poem) => (
                    <PoemScrollCard
                      key={poem.id}
                      poem={poem}
                      expanded={expandedId === poem.id}
                      onToggle={() => setExpandedId(expandedId === poem.id ? null : poem.id)}
                    />
                  ))}
                </div>
              </>
            )}

            <div className="library-footer font-cjk">
              <span>已展 {poems.length} / {filteredTotal} 卷</span>
              {hasMore && (
                <button
                  type="button"
                  onClick={loadMore}
                  disabled={loadingMore}
                  className="library-load-more"
                >
                  {loadingMore ? '展卷中…' : `继续展卷（+${PER_PAGE} 首）`}
                </button>
              )}
            </div>
          </>
        )}
      </div>
    </section>
  );
};

export default LibraryPage;
