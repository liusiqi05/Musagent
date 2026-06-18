// ========== 中文情感分析 ==========

// 情感词典
const EMOTION_DICT = {
  喜悦: ['快乐', '幸福', '喜悦', '欢', '笑', '乐', '甜', '美', '好', '棒',
    '开心', '高兴', '欣喜', '愉快', '满足', '欣慰', '雀跃', '灿烂', '明媚',
    '阳光', '温暖', '希望', '光亮', '绽放', '盛开', '春天', '彩虹', '花朵'],

  悲伤: ['悲伤', '痛苦', '难过', '伤心', '哭泣', '泪水', '泪', '哭', '叹',
    '碎裂', '破碎', '凋零', '枯萎', '苍白', '灰暗', '阴霾', '沉重', '窒息',
    '失去', '告别', '离别', '诀别', '永别', '凋谢', '消散', '淹没'],

  孤独: ['孤独', '寂寞', '孤单', '独自', '一人', '空', '冷', '荒漠',
    '深夜', '无人', '沉默', '静默', '空旷', '荒凉', '冷清', '落寞',
    '彷徨', '迷茫', '漂泊', '流浪', '异乡', '陌生', '疏离', '隔绝'],

  怀旧: ['怀念', '怀旧', '回忆', '记忆', '往事', '从前', '曾经', '过去',
    '童年', '少年', '故乡', '老家', '旧日', '旧时光', '故人', '故地',
    '往昔', '昔日', '当年', '那时', '泛黄', '老照片', '日记', '信笺'],

  激昂: ['激昂', '奋斗', '拼搏', '热血', '汹涌', '澎湃', '燃烧', '怒放',
    '呐喊', '咆哮', '狂野', '奔放', '豪迈', '壮阔', '雄伟', '磅礴',
    '青春', '力量', '勇气', '信念', '梦想', '追逐', '冲锋', '翱翔'],

  平静: ['平静', '宁静', '安静', '祥和', '安宁', '静谧', '淡然', '从容',
    '悠闲', '自在', '安详', '平和', '缓缓', '慢慢', '轻轻', '淡淡',
    '微风', '湖水', '远山', '白云', '禅', '茶', '书', '琴'],

  焦虑: ['焦虑', '不安', '紧张', '恐惧', '害怕', '担忧', '烦躁', '压抑',
    '窒息', '纠葛', '缠', '困', '锁', '束缚', '囚禁', '深渊',
    '黑暗', '漆黑', '阴冷', '寒', '凛冽', '刺骨', '颤抖', '窒息'],
};

/**
 * 情感分析
 * @param {string[]} words - 分词后的词列表
 * @returns {{ dominant: string, scores: Record<string, number>, intensity: number }}
 */
export function analyzeSentiment(words) {
  const scores = {};
  let totalMatches = 0;

  for (const [emotion, keywords] of Object.entries(EMOTION_DICT)) {
    let score = 0;
    for (const word of words) {
      if (keywords.includes(word)) {
        score += 1;
        totalMatches++;
      }
    }
    scores[emotion] = score;
  }

  // 如果完全没有匹配，返回默认
  if (totalMatches === 0) {
    return {
      dominant: '平静',
      scores: { 喜悦: 0, 悲伤: 0, 孤独: 0, 怀旧: 0, 激昂: 0, 平静: 1, 焦虑: 0 },
      intensity: 0.1,
    };
  }

  // 归一化
  const maxScore = Math.max(...Object.values(scores), 1);
  const normalized = {};
  for (const [k, v] of Object.entries(scores)) {
    normalized[k] = Math.round((v / maxScore) * 100) / 100;
  }

  // 找主导情感
  let dominant = '平静';
  let max = 0;
  for (const [k, v] of Object.entries(normalized)) {
    if (v > max) { max = v; dominant = k; }
  }

  return {
    dominant,
    scores: normalized,
    intensity: Math.round((totalMatches / Math.max(words.length, 1)) * 100) / 100,
  };
}

export default { analyzeSentiment };
