/** 全站中文标签 — 实体类型、关系、垂直领域 */

export const VERTICAL_LABELS = {
  literature_poetry: '文学诗歌',
};

export const ENTITY_TYPE_LABELS = {
  person: '人物',
  location: '地点',
  imagery: '意象',
  work: '作品',
  organization: '体裁',
  time: '时间',
  topic: '主题/情感',
  unknown: '其他',
};

/** 关系中文 — 优先展示文本/意象/情感语义，元数据类靠后 */
export const RELATION_LABELS = {
  imagery_co_occurs: '意象共现',
  evokes_emotion: '唤起情感',
  emotion_resonance: '情感共鸣',
  theme_echo: '主题呼应',
  symbolizes: '象征',
  semantic_echo: '语义呼应',
  contains_imagery: '含意象',
  metaphor_of: '比喻',
  inspired_by: '借鉴',
  co_occurs_with: '同现',
  related_to: '关联',
  located_in: '场景',
  has_emotion: '情感基调',
  authored_by: '作者',
  belongs_to_type: '体裁',
  has_attribute: '属性',
};

export const RELATION_GROUPS = {
  semantic: ['imagery_co_occurs', 'evokes_emotion', 'emotion_resonance', 'theme_echo', 'symbolizes', 'semantic_echo', 'contains_imagery', 'metaphor_of', 'inspired_by'],
  meta: ['authored_by', 'belongs_to_type'],
};

export const ENTITY_TYPE_COLORS = {
  person: '#e7d393',
  location: '#7ec8e3',
  imagery: '#c9a0dc',
  work: '#f4a582',
  organization: '#98d8c8',
  time: '#b0b0b0',
  topic: '#ffffff',
  unknown: '#888888',
};

export const REVIEW_TAGS = [
  { id: 'imagery', label: '意象准确' },
  { id: 'emotion', label: '情感贴合' },
  { id: 'rhythm', label: '节奏好' },
  { id: 'citation', label: '化用自然' },
  { id: 'length', label: '篇幅合适' },
  { id: 'retry', label: '想再改改' },
];

export function verticalLabel(code) {
  return VERTICAL_LABELS[code] || '文学诗歌';
}

export function entityTypeLabel(code) {
  return ENTITY_TYPE_LABELS[code] || '其他';
}

export function relationLabel(code) {
  return RELATION_LABELS[code] || code;
}
