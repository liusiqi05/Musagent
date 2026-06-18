// ========== 混合多因子相似度检索 ==========
// TF-IDF + n-gram + Jaccard + 情感匹配 四因子混合打分
import { segment } from './segmenter.js';
import { extractKeywords, buildVector, cosineSimilarity } from './tfidf.js';

let kbCache = null;

/** character n-grams：捕捉子词/字形级别的语义相似性 */
function charNGrams(text, n = 2) {
  const grams = new Set();
  for (let i = 0; i <= text.length - n; i++) grams.add(text.slice(i, i + n));
  return [...grams];
}

/** Jaccard 相似度 */
function jaccard(setA, setB) {
  const a = new Set(setA), b = new Set(setB);
  let inter = 0; for (const x of a) { if (b.has(x)) inter++; }
  const union = a.size + b.size - inter;
  return union === 0 ? 0 : inter / union;
}

function buildKnowledgeBase(poemsData) {
  const allDocs = []; const allWordLists = [];

  for (const p of poemsData.modern) {
    const { words } = segment(p.content);
    allDocs.push({ type: '现代诗', title: p.title, author: p.author, content: p.content, words, wordSet: new Set(words), ngrams2: charNGrams(p.content, 2), ngrams3: charNGrams(p.content, 3) });
    allWordLists.push(words);
  }
  for (const p of poemsData.classical) {
    const { words } = segment(p.content);
    allDocs.push({ type: '古典诗', title: p.title, author: p.author, content: p.content, words, wordSet: new Set(words), ngrams2: charNGrams(p.content, 2), ngrams3: charNGrams(p.content, 3) });
    allWordLists.push(words);
  }

  // 词汇表 = 词 + n-gram 特征
  const vocabSet = new Set();
  allWordLists.forEach(wl => wl.forEach(w => vocabSet.add(w)));
  allDocs.forEach(d => { d.ngrams2.forEach(g => vocabSet.add('2_' + g)); d.ngrams3.forEach(g => vocabSet.add('3_' + g)); });
  const vocabulary = [...vocabSet];

  const docVectors = allDocs.map(doc => {
    const feats = [...doc.words, ...doc.ngrams2.map(g => '2_' + g), ...doc.ngrams3.map(g => '3_' + g)];
    return buildVector(extractKeywords(feats, allWordLists, 50), vocabulary);
  });

  console.log(`[RetrievalAgent] 知识库就绪：${allDocs.length} 篇，词汇量 ${vocabulary.length}（含 n-gram 特征）`);
  return { docs: allDocs, vocabulary, docVectors, corpus: allWordLists };
}

async function getKB() {
  if (!kbCache) { const m = await import('../data/poems_extracted.json'); kbCache = buildKnowledgeBase(m.default); }
  return kbCache;
}

function detectEmotion(text) {
  const map = { '孤独':['孤独','寂寞','独自'], '怀旧':['怀念','记忆','往事'], '激昂':['激昂','热血','梦想'], '平静':['宁静','安静','淡然'], '悲伤':['痛苦','泪','碎'], '喜悦':['快乐','幸福','笑'] };
  let best='平静',max=0;
  for(const[e,kws]of Object.entries(map)){let s=0;for(const k of kws)if(text.includes(k))s++;if(s>max){max=s;best=e;}}
  return best;
}

export async function retrieveSimilar(queryWords, queryText = '', queryEmotion = '平静', topN = 5) {
  const kb = await getKB();

  const qNG2 = charNGrams(queryText || queryWords.join(''), 2);
  const qNG3 = charNGrams(queryText || queryWords.join(''), 3);
  const qFeats = [...queryWords, ...qNG2.map(g => '2_' + g), ...qNG3.map(g => '3_' + g)];
  const qVec = buildVector(extractKeywords(qFeats, kb.corpus, 30), kb.vocabulary);
  const qSet = new Set(queryWords);

  const scored = kb.docs.map((doc, i) => {
    const tfidf   = cosineSimilarity(qVec, kb.docVectors[i]);
    const jacc    = jaccard(qSet, doc.wordSet);
    const ngram   = (jaccard(new Set(qNG2), new Set(doc.ngrams2)) + jaccard(new Set(qNG3), new Set(doc.ngrams3))) / 2;
    const emotion = detectEmotion(doc.content) === queryEmotion ? 1 : 0.5;
    const hybrid  = tfidf * 0.4 + jacc * 0.3 + ngram * 0.2 + emotion * 0.1;

    return { type: doc.type, title: doc.title, author: doc.author, content: doc.content.slice(0, 100), similarity: hybrid, details: { tfidf, jaccard: jacc, ngram, emotion } };
  });

  scored.sort((a, b) => b.similarity - a.similarity);
  return scored.slice(0, topN);
}

// 艺术风格库
const ART_STYLES = [
  { name: '印象派', keywords: ['光影', '色彩', '模糊', '瞬间', '朦胧', '柔和', '梦幻', '自然'] },
  { name: '表现主义', keywords: ['扭曲', '呐喊', '强烈', '痛苦', '情绪', '黑暗', '浓烈', '不安'] },
  { name: '极简主义', keywords: ['留白', '简洁', '线条', '空间', '克制', '空旷', '静谧', '几何'] },
  { name: '中国水墨', keywords: ['山水', '意境', '留白', '气韵', '墨', '虚实', '飘逸', '古雅'] },
  { name: '赛博朋克', keywords: ['霓虹', '科技', '都市', '虚拟', '雨夜', '钢筋', '电子', '未来'] },
  { name: '超现实主义', keywords: ['梦境', '荒诞', '潜意识', '自由', '奇异', '不羁', '幻想', '迷离'] },
];

const MUSIC_MOODS = [
  { mood: '孤独', genre: '后摇 / 氛围', desc: 'Sigur Rós, 坂本龙一' },
  { mood: '温柔', genre: '钢琴独奏', desc: '肖邦夜曲, 德彪西' },
  { mood: '激昂', genre: '交响乐', desc: '贝多芬, 马勒' },
  { mood: '怀旧', genre: '爵士 / 民谣', desc: 'Chet Baker, Bob Dylan' },
  { mood: '平静', genre: '极简 / 新世纪', desc: 'Max Richter, Enya' },
  { mood: '焦虑', genre: '电子 / 工业', desc: 'Nine Inch Nails, Radiohead' },
  { mood: '喜悦', genre: '流行 / 放克', desc: 'Earth Wind & Fire, Daft Punk' },
];

export function matchArtStyle(words, emotion) {
  const scores = ART_STYLES.map(style => {
    let score = 0;
    for (const word of words) {
      if (style.keywords.includes(word)) score += 1;
    }
    const emotionMap = {
      '孤独': ['表现主义', '极简主义', '赛博朋克'],
      '怀旧': ['印象派', '中国水墨'],
      '激昂': ['表现主义', '超现实主义'],
      '平静': ['极简主义', '中国水墨'],
      '喜悦': ['印象派', '超现实主义'],
      '悲伤': ['表现主义', '中国水墨'],
      '焦虑': ['赛博朋克', '表现主义'],
    };
    if (emotionMap[emotion] && emotionMap[emotion].includes(style.name)) {
      score += 2;
    }
    return { ...style, score };
  });
  scores.sort((a, b) => b.score - a.score);
  return scores.slice(0, 3);
}

export function matchMusic(emotion) {
  return MUSIC_MOODS.find(m => m.mood === emotion) || MUSIC_MOODS[4];
}

export default { retrieveSimilar, matchArtStyle, matchMusic };
