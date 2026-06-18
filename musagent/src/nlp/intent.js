// ========== 意图分类器 ==========

const INTENT_PATTERNS = {
  '诗歌创作': ['诗', '诗歌', '写诗', '作诗', '创作诗', '写一首', '诗句', '作一首', '现代诗', '古典诗'],
  '散文创作': ['散文', '随笔', '杂文', '小品', '散记', '抒情', '记叙'],
  '小说创作': ['小说', '故事', '短篇', '长篇', '叙事', '情节', '角色', '人物'],
  '诗词分析': ['分析', '鉴赏', '赏析', '解读', '解析', '讲解', '理解', '含义', '意思'],
  '艺术风格探索': ['艺术', '风格', '画', '音乐', '印象', '表现', '水墨', '赛博', '视觉'],
  '音乐氛围推荐': ['音乐', '歌曲', '配乐', '氛围', '节奏', '旋律', '乐器', 'BGM'],
  '知识问答': ['什么', '怎么', '如何', '为什么', '解释', '定义', '是什么', '介绍一下'],
  '文本润色': ['润色', '修改', '优化', '改进', '改写', '修饰', '调整', '完善', '润饰'],
};

export function classifyIntent(text) {
  const scores = {};
  for (const [intent, keywords] of Object.entries(INTENT_PATTERNS)) {
    let score = 0;
    for (const kw of keywords) {
      if (text.includes(kw)) score += 1;
    }
    scores[intent] = score;
  }

  // 找最高分
  let bestIntent = '诗歌创作';
  let maxScore = 0;
  for (const [intent, score] of Object.entries(scores)) {
    if (score > maxScore) {
      maxScore = score;
      bestIntent = intent;
    }
  }

  // 如果所有分数都为 0，默认诗歌创作
  if (maxScore === 0) {
    bestIntent = '诗歌创作';
    scores['诗歌创作'] = 0.5;
  }

  const total = Math.max(Object.values(scores).reduce((a, b) => a + b, 0), 1);
  const confidence = {};
  for (const [k, v] of Object.entries(scores)) {
    confidence[k] = Math.round((v / total) * 100) / 100;
  }

  return { intent: bestIntent, confidence, allScores: scores };
}

export default { classifyIntent };
