import { formatAuthor } from '../../utils/author.js';

const EMOTION_ACCENT = {
  孤独: '#a78bfa',
  怀旧: '#d4a574',
  平静: '#6ee7b7',
  激昂: '#f87171',
  悲伤: '#94a3b8',
  喜悦: '#fcd34d',
};

const ScrollOrnament = () => (
  <svg className="poem-card-ornament" viewBox="0 0 48 48" fill="none" aria-hidden>
    <circle cx="24" cy="24" r="20" stroke="currentColor" strokeWidth="0.5" opacity="0.35" />
    <path d="M24 8v32M8 24h32" stroke="currentColor" strokeWidth="0.4" opacity="0.2" />
    <circle cx="24" cy="24" r="3" fill="currentColor" opacity="0.25" />
  </svg>
);

const PoemScrollCard = ({ poem, expanded, onToggle }) => {
  const accent = EMOTION_ACCENT[poem.emotion] || '#c9a84c';
  const isClassical = poem.type === '古典诗';
  const preview = poem.content?.length > 140 && !expanded;

  return (
    <article
      className={`poem-scroll-card ${expanded ? 'poem-scroll-card--expanded' : ''}`}
      style={{ '--poem-accent': accent }}
      onClick={onToggle}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') onToggle(); }}
    >
      <div className="poem-scroll-card__glow" aria-hidden />
      <ScrollOrnament />

      <header className="poem-scroll-card__head">
        <span className={`poem-scroll-card__type ${isClassical ? 'poem-scroll-card__type--classical' : ''}`}>
          {isClassical ? '古典' : '现代'}
        </span>
        <span className="poem-scroll-card__emotion">{poem.emotion}</span>
      </header>

      <h3 className="poem-scroll-card__title font-cjk">
        {isClassical ? `「${poem.title}」` : poem.title}
      </h3>
      <p className="poem-scroll-card__author font-cjk">{formatAuthor(poem.author)}</p>

      <div className={`poem-scroll-card__body font-cjk ${preview ? 'poem-scroll-card__body--clamp' : ''}`}>
        {poem.content}
      </div>

      {preview && (
        <span className="poem-scroll-card__more">展开全文</span>
      )}
      {expanded && poem.content?.length > 80 && (
        <span className="poem-scroll-card__more">收起</span>
      )}

      {(poem.keywords?.length > 0) && (
        <footer className="poem-scroll-card__tags">
          {poem.keywords.slice(0, 6).map((kw) => (
            <span key={kw} className="poem-scroll-card__tag">#{kw}</span>
          ))}
        </footer>
      )}
    </article>
  );
};

export default PoemScrollCard;
