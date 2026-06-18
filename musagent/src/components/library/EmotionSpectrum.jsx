const EMOTION_META = [
  { key: 'all', label: '全部', color: '#e7d393', icon: '卷' },
  { key: '孤独', label: '孤独', color: '#a78bfa', icon: '月' },
  { key: '怀旧', label: '怀旧', color: '#d4a574', icon: '忆' },
  { key: '平静', label: '平静', color: '#6ee7b7', icon: '风' },
  { key: '激昂', label: '激昂', color: '#f87171', icon: '火' },
  { key: '悲伤', label: '悲伤', color: '#94a3b8', icon: '雨' },
  { key: '喜悦', label: '喜悦', color: '#fcd34d', icon: '晴' },
];

const EmotionSpectrum = ({ emotions = {}, active, onSelect, total }) => {
  const emotionTotal = Object.values(emotions).reduce((a, b) => a + b, 0) || 1;

  return (
    <div className="emotion-spectrum panel-card">
      <div className="emotion-spectrum__bar" role="presentation">
        {EMOTION_META.filter((e) => e.key !== 'all').map((e) => {
          const count = emotions[e.key] || 0;
          const pct = Math.max((count / emotionTotal) * 100, count > 0 ? 2 : 0);
          return (
            <button
              key={e.key}
              type="button"
              className={`emotion-spectrum__segment ${active === e.key ? 'emotion-spectrum__segment--active' : ''}`}
              style={{ width: `${pct}%`, backgroundColor: e.color }}
              title={`${e.label} ${count} 首`}
              onClick={() => onSelect(e.key)}
            />
          );
        })}
      </div>

      <div className="emotion-spectrum__tabs">
        {EMOTION_META.map((tab) => {
          const count = tab.key === 'all' ? total : emotions[tab.key];
          const isActive = active === tab.key;
          return (
            <button
              key={tab.key}
              type="button"
              onClick={() => onSelect(tab.key)}
              className={`emotion-spectrum__pill ${isActive ? 'emotion-spectrum__pill--active' : ''}`}
              style={isActive ? { borderColor: tab.color, boxShadow: `0 0 20px ${tab.color}33` } : {}}
            >
              <span className="emotion-spectrum__seal" style={{ color: tab.color }}>{tab.icon}</span>
              <span>{tab.label}</span>
              {count != null && tab.key !== 'all' && (
                <span className="emotion-spectrum__count">{count}</span>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
};

export default EmotionSpectrum;
