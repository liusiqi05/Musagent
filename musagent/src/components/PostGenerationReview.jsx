import { useState } from 'react';
import { submitFeedback } from '../nlp/api.js';
import { REVIEW_TAGS } from '../constants/labels.js';

/**
 * 生成后评价闭环 — 评分 → 标签 → 下一步操作
 */
const PostGenerationReview = ({
  topic = '',
  contentPreview = '',
  quality = null,
  onPolish,
  onRegenerate,
  onComplete,
  onSkip,
}) => {
  const [rating, setRating] = useState(0);
  const [hover, setHover] = useState(0);
  const [selectedTags, setSelectedTags] = useState([]);
  const [comment, setComment] = useState('');
  const [phase, setPhase] = useState('rate');
  const [status, setStatus] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const toggleTag = (id) => {
    setSelectedTags((prev) => (prev.includes(id) ? prev.filter((t) => t !== id) : [...prev, id]));
  };

  const tagComment = () => {
    const labels = REVIEW_TAGS.filter((t) => selectedTags.includes(t.id)).map((t) => t.label);
    return [comment, labels.length ? `标签：${labels.join('、')}` : ''].filter(Boolean).join('；');
  };

  const submitReview = async () => {
    if (!rating) {
      setStatus('请先选择 1–5 星评分');
      return;
    }
    setSubmitting(true);
    try {
      await submitFeedback({
        sourceType: 'generation',
        rating,
        comment: tagComment(),
        topic,
        contentPreview: contentPreview?.slice(0, 400),
        metadata: { tags: selectedTags, qualityScore: quality?.overall?.score },
      });
      setPhase('actions');
      setStatus('感谢评价，已用于优化后续推荐');
    } catch (err) {
      setStatus(`提交失败：${err.message}`);
    }
    setSubmitting(false);
  };

  const handleSkip = () => {
    setPhase('actions');
    onSkip?.();
  };

  if (phase === 'actions') {
    return (
      <div className="review-panel review-panel-actions">
        <p className="review-panel-title">接下来想做什么？</p>
        <div className="review-action-grid">
          <button type="button" className="review-action-btn primary" onClick={onPolish}>
            发送到润色
          </button>
          <button type="button" className="review-action-btn" onClick={onRegenerate}>
            沿用分析再生成
          </button>
          <button type="button" className="review-action-btn subtle" onClick={onComplete}>
            完成，继续创作
          </button>
        </div>
        {status && <p className="review-status">{status}</p>}
      </div>
    );
  }

  return (
    <div className="review-panel">
      <div className="review-panel-head">
        <div>
          <p className="review-panel-title">这条生成结果怎么样？</p>
          <p className="review-panel-sub">你的评价会帮助系统优化检索与生成</p>
        </div>
        {quality?.overall && (
          <span className={`quality-badge ${quality.overall.passed ? 'is-pass' : 'is-warn'}`}>
            {quality.overall.label} · {Math.round(quality.overall.score * 100)}分
          </span>
        )}
      </div>

      <div className="feedback-stars review-stars" role="group" aria-label="评分">
        {[1, 2, 3, 4, 5].map((star) => (
          <button
            key={star}
            type="button"
            className={`feedback-star ${(hover || rating) >= star ? 'is-active' : ''}`}
            onMouseEnter={() => setHover(star)}
            onMouseLeave={() => setHover(0)}
            onClick={() => setRating(star)}
          >
            ★
          </button>
        ))}
        <span className="review-star-hint">{rating ? `${rating} 星` : '点击评分'}</span>
      </div>

      <div className="review-tags">
        {REVIEW_TAGS.map((tag) => (
          <button
            key={tag.id}
            type="button"
            className={`review-tag ${selectedTags.includes(tag.id) ? 'is-active' : ''}`}
            onClick={() => toggleTag(tag.id)}
          >
            {tag.label}
          </button>
        ))}
      </div>

      <textarea
        className="feedback-comment"
        rows={2}
        placeholder="可选：具体说说哪里好 / 哪里想改进…"
        value={comment}
        onChange={(e) => setComment(e.target.value)}
      />

      <div className="review-footer">
        <button type="button" className="feedback-submit" onClick={submitReview} disabled={submitting || !rating}>
          {submitting ? '提交中…' : '提交评价并继续'}
        </button>
        <button type="button" className="review-skip" onClick={handleSkip}>
          跳过
        </button>
        {status && <span className="feedback-status">{status}</span>}
      </div>
    </div>
  );
};

export default PostGenerationReview;
