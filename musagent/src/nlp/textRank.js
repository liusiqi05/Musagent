// ========== TextRank 摘要算法 ==========

/**
 * 计算两句话的相似度（基于共同词比例）
 */
function sentenceSimilarity(wordsA, wordsB) {
  const setA = new Set(wordsA);
  const setB = new Set(wordsB);
  if (setA.size === 0 || setB.size === 0) return 0;
  let common = 0;
  for (const w of setA) {
    if (setB.has(w)) common++;
  }
  return common / (Math.log(setA.size + 1) + Math.log(setB.size + 1));
}

/**
 * TextRank 算法
 * @param {string[][]} sentences - 句子的词列表数组
 * @param {number} damping - 阻尼系数
 * @param {number} iterations - 迭代次数
 * @returns {number[]} 每句的得分
 */
function textRank(sentences, damping = 0.85, iterations = 100) {
  const n = sentences.length;
  if (n <= 1) return [1];

  // 构建相似度矩阵
  const simMatrix = [];
  for (let i = 0; i < n; i++) {
    simMatrix[i] = [];
    for (let j = 0; j < n; j++) {
      if (i === j) {
        simMatrix[i][j] = 0;
      } else {
        simMatrix[i][j] = sentenceSimilarity(sentences[i], sentences[j]);
      }
    }
  }

  // 转移矩阵
  const weights = simMatrix.map(row => {
    const sum = row.reduce((a, b) => a + b, 0);
    return row.map(v => sum > 0 ? v / sum : 1 / n);
  });

  // PageRank 迭代
  let scores = new Array(n).fill(1 / n);
  for (let iter = 0; iter < iterations; iter++) {
    const newScores = new Array(n).fill((1 - damping) / n);
    for (let i = 0; i < n; i++) {
      for (let j = 0; j < n; j++) {
        if (i !== j) {
          newScores[i] += damping * weights[j][i] * scores[j];
        }
      }
    }
    scores = newScores;
  }

  return scores;
}

/**
 * 把文本分句
 */
function splitSentences(text) {
  return text
    .split(/[。！？\n]+/)
    .map(s => s.trim())
    .filter(s => s.length > 2);
}

/**
 * 生成 TextRank 摘要
 * @param {string} text - 输入文本
 * @param {string[]} allWords - 分词结果
 * @param {number} topN - 保留 Top N 句
 * @returns {{ summary: string, topicWords: string[] }}
 */
export function summarize(text, allWords, topN = 3) {
  const sentences = splitSentences(text);
  if (sentences.length === 0) return { summary: text.slice(0, 100), topicWords: allWords.slice(0, 5) };

  // 每句分词
  const sentWords = sentences.map(s => {
    const clean = s.replace(/[，、：；""''（）()[\]【】\d\w]/g, '');
    return [...new Set(clean.split('').filter(c => c.trim()))];
  });

  const scores = textRank(sentWords);
  const ranked = sentences.map((s, i) => ({ sentence: s, score: scores[i] }));
  ranked.sort((a, b) => b.score - a.score);

  const topSentences = ranked.slice(0, Math.min(topN, ranked.length));
  // 按原顺序排列
  const ordered = topSentences.sort((a, b) =>
    sentences.indexOf(a.sentence) - sentences.indexOf(b.sentence)
  );

  return {
    summary: ordered.map(item => item.sentence).join('。'),
    topicWords: allWords.slice(0, 5),
  };
}

export default { summarize };
