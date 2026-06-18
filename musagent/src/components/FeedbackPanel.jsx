import { useState } from 'react';
import { submitFeedback, submitQAFeedback } from '../nlp/api.js';

const STARS = [1, 2, 3, 4, 5];

/**
 * 用户评分反馈面板 — 支持生成/对话/润色等场景
 */
const FeedbackPanel = ({
  sourceType = 'generation',
  topic = '',
  contentPreview = '',
  sourceId = '',
  qaMode = false,
  question = '',
  answer = '',
  onSubmitted,
}) => {
  const [rating, setRating] = useState(0);
  const [hover, setHover] = useState(0);
  const [comment, setComment] = useState('');
  const [helpful, setHelpful] = useState(true);
  const [status, setStatus] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async () => {
    if (!rating) {
      setStatus('请先选择评分');
      return;
    }
    setSubmitting(true);
    setStatus('');
    try {
      if (qaMode) {
        await submitQAFeedback({
          question: question || topic,
          answer: answer || contentPreview,
          rating,
          helpful,
          tags: [sourceType],
        });
      } else {
        await submitFeedback({
          sourceType,
          rating,
          comment,
          topic,
          contentPreview: contentPreview?.slice(0, 400),
          sourceId,
        });
      }
      setStatus('感谢反馈，已记录');
      onSubmitted?.(rating);
    } catch (err) {
      setStatus(`提交失败：${err.message}`);
    }
    setSubmitting(false);
  };

  return (
    <div className="feedback-panel">
      <div className="feedback-panel-head">
        <span className="feedback-panel-title">这条结果有帮助吗？</span>
        <div className="feedback-stars" role="group" aria-label="评分">
          {STARS.map((star) => (
            <button
              key={star}
              type="button"
              className={`feedback-star ${(hover || rating) >= star ? 'is-active' : ''}`}
              onMouseEnter={() => setHover(star)}
              onMouseLeave={() => setHover(0)}
              onClick={() => setRating(star)}
              aria-label={`${star} 星`}
            >
              ★
            </button>
          ))}
        </div>
      </div>

      {!qaMode && (
        <textarea
          className="feedback-comment"
          rows={2}
          placeholder="可选：写下改进建议或喜欢的点…"
          value={comment}
          onChange={(e) => setComment(e.target.value)}
        />
      )}

      {qaMode && (
        <label className="feedback-helpful">
          <input type="checkbox" checked={helpful} onChange={(e) => setHelpful(e.target.checked)} />
          <span>这个回答解决了我的问题</span>
        </label>
      )}

      <div className="feedback-actions">
        <button
          type="button"
          className="feedback-submit"
          onClick={handleSubmit}
          disabled={submitting || !rating}
        >
          {submitting ? '提交中…' : '提交反馈'}
        </button>
        {status && <span className="feedback-status">{status}</span>}
      </div>
    </div>
  );
};

export default FeedbackPanel;
