// ========== TF-IDF 关键词提取 ==========

/**
 * 计算 TF（词频）
 */
function computeTF(word, words) {
  const total = words.length;
  const count = words.filter(w => w === word).length;
  return count / (total || 1);
}

/**
 * 计算 IDF（逆文档频率）
 */
function computeIDF(word, documents) {
  const totalDocs = documents.length;
  const docsWithWord = documents.filter(doc => doc.includes(word)).length;
  return Math.log((totalDocs + 1) / (docsWithWord + 1)) + 1;
}

/**
 * TF-IDF 关键词提取
 * @param {string[]} words - 分词后的词列表
 * @param {string[][]} corpus - 语料库（每个文档是词列表）
 * @param {number} topN - 返回 Top N 关键词
 * @returns {{ keyword: string, tfidf: number }[]}
 */
export function extractKeywords(words, corpus = null, topN = 10) {
  // 如果没有语料库，使用自建语料库（words 自身作为单文档）
  const documents = corpus || [words];
  const uniqueWords = [...new Set(words)];

  const scores = uniqueWords.map(word => {
    const tf = computeTF(word, words);
    const idf = computeIDF(word, documents);
    return { keyword: word, tfidf: tf * idf };
  });

  scores.sort((a, b) => b.tfidf - a.tfidf);
  return scores.slice(0, topN);
}

/**
 * 构建 TF-IDF 向量
 */
export function buildVector(keywords, vocabulary) {
  const vec = new Array(vocabulary.length).fill(0);
  const kwMap = {};
  keywords.forEach(k => { kwMap[k.keyword] = k.tfidf; });

  vocabulary.forEach((word, i) => {
    if (kwMap[word]) vec[i] = kwMap[word];
  });
  return vec;
}

/**
 * 余弦相似度
 */
export function cosineSimilarity(vecA, vecB) {
  let dot = 0, magA = 0, magB = 0;
  for (let i = 0; i < vecA.length; i++) {
    dot += vecA[i] * vecB[i];
    magA += vecA[i] * vecA[i];
    magB += vecB[i] * vecB[i];
  }
  magA = Math.sqrt(magA);
  magB = Math.sqrt(magB);
  if (magA === 0 || magB === 0) return 0;
  return dot / (magA * magB);
}

export default { extractKeywords, buildVector, cosineSimilarity };
