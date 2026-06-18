// ==================== MusAgent Mock Data ====================
// 文学与艺术灵感生成平台 - 多智能体协作系统

// ---------- 诗歌示例（轻量 Mock，完整数据动态加载） ----------
export const poetryExamples = [];

// ---------- 艺术风格库 ----------
export const artStyles = [
  {
    id: 'impressionism',
    name: '印象派',
    description: '捕捉光与色彩的瞬间变化，强调主观感受',
    keywords: ['光影', '色彩', '瞬间', '自然', '朦胧'],
    colorPalette: ['#F5D76E', '#E8A87C', '#95B8D1', '#D4A5A5'],
    musicMatch: '德彪西《月光》',
    emotion: '柔和、梦幻',
  },
  {
    id: 'expressionism',
    name: '表现主义',
    description: '通过扭曲和夸张表达内心情感',
    keywords: ['扭曲', '情绪', '呐喊', '强烈', '主观'],
    colorPalette: ['#8B0000', '#1C1C1C', '#FFD700', '#4B0082'],
    musicMatch: '勋伯格《升华之夜》',
    emotion: '激烈、不安',
  },
  {
    id: 'minimalism',
    name: '极简主义',
    description: '少即是多，以最少的元素传达最深的意境',
    keywords: ['留白', '简洁', '线条', '空间', '克制'],
    colorPalette: ['#FFFFFF', '#2D2D2D', '#D3D3D3', '#8C8C8C'],
    musicMatch: '菲利普·格拉斯《玻璃工厂》',
    emotion: '宁静、深远',
  },
  {
    id: 'chinese-ink',
    name: '中国水墨',
    description: '墨分五色，虚实相生，意趣天成',
    keywords: ['水墨', '留白', '山水', '意境', '气韵'],
    colorPalette: ['#1A1A1A', '#4A4A4A', '#8C8C8C', '#C4C4C4'],
    musicMatch: '古琴《流水》',
    emotion: '空灵、深远',
  },
  {
    id: 'cyberpunk',
    name: '赛博朋克',
    description: '高科技低生活，霓虹与黑暗交织的未来图景',
    keywords: ['霓虹', '科技', '都市', '反乌托邦', '虚拟'],
    colorPalette: ['#FF00FF', '#00FFFF', '#1A0033', '#FF6600'],
    musicMatch: '合成波电子乐',
    emotion: '迷幻、疏离',
  },
  {
    id: 'surrealism',
    name: '超现实主义',
    description: '梦境与现实的交错，潜意识的自由表达',
    keywords: ['梦境', '潜意识', '荒诞', '自由', '隐喻'],
    colorPalette: ['#2C3E50', '#E74C3C', '#F39C12', '#1ABC9C'],
    musicMatch: '萨蒂《裸体舞曲》',
    emotion: '奇异、梦幻',
  },
];

// ---------- 音乐情绪库 ----------
export const musicMoods = [
  { id: 'm1', mood: '孤独', genre: '后摇 / 氛围音乐', recommendation: 'Sigur Rós — 《()》', bpm: '60-80', scene: '深夜独自思考时' },
  { id: 'm2', mood: '温柔', genre: '古典 / 钢琴独奏', recommendation: '肖邦 — 《夜曲 Op.9 No.2》', bpm: '55-70', scene: '安静的午后阅读' },
  { id: 'm3', mood: '激昂', genre: '交响乐 / 摇滚', recommendation: '贝多芬 — 《第五交响曲》', bpm: '120-160', scene: '创作冲刺时' },
  { id: 'm4', mood: '怀旧', genre: '爵士 / 民谣', recommendation: 'Chet Baker — 《My Funny Valentine》', bpm: '60-90', scene: '回忆往事时' },
  { id: 'm5', mood: '治愈', genre: '轻音乐 / 新世纪', recommendation: '坂本龙一 — 《Merry Christmas Mr. Lawrence》', bpm: '70-90', scene: '需要心灵慰藉时' },
  { id: 'm6', mood: '沉思', genre: '极简音乐 / 环境音乐', recommendation: 'Max Richter — 《On the Nature of Daylight》', bpm: '50-65', scene: '冥想或写作时' },
  { id: 'm7', mood: '迷幻', genre: '迷幻摇滚 / 电子', recommendation: 'Pink Floyd — 《The Dark Side of the Moon》', bpm: '60-120', scene: '需要灵感突破时' },
  { id: 'm8', mood: '空灵', genre: '世界音乐 / 新世纪', recommendation: 'Enya — 《Only Time》', bpm: '50-70', scene: '放松与放空时' },
];

// ---------- Agent 工作流步骤 ----------
export const agentSteps = [
  {
    id: 'wordseg',
    name: 'WordSegAgent',
    label: '中文分词',
    icon: '📝',
    description: '对用户输入进行中文分词，并过滤停用词与无效短词',
    input: '用户原始输入文本',
    output: '词列表 + 词频统计',
    status: 'success',
    detail: '使用 Jieba 对主题或文本片段分词，为关键词提取、情感分析和知识库检索提供基础特征。',
  },
  {
    id: 'intent',
    name: 'IntentAgent',
    label: '意图识别',
    icon: '🎯',
    description: '解析用户输入，识别创作意图与需求类型',
    input: '用户原始输入文本',
    output: '意图标签 + 置信度',
    status: 'success',
    detail: '判断用户是想创作现代诗、分析古典诗词、匹配艺术风格还是推荐音乐情绪。',
  },
  {
    id: 'ner',
    name: 'NERAgent',
    label: '实体识别',
    icon: '🏷️',
    description: '识别人物、地点、时间与意象名词',
    input: '用户原始输入文本',
    output: '实体列表 + 意象词',
    status: 'success',
    detail: 'ckiplab/bert-base-chinese-ner 抽取人名/地名/机构，Jieba 补充时间词与意象名词。',
  },
  {
    id: 'emotion',
    name: 'EmotionAgent',
    label: '融合情感分析',
    icon: '💭',
    description: '文学词典 + RoBERTa 融合的情感分析',
    input: '文本片段',
    output: '六维情感向量 + 融合主导情绪',
    status: 'success',
    detail: '文学词典捕捉诗歌情绪词，RoBERTa 提供深度情感极性，按 50%/50% 融合输出最终情绪。',
  },
  {
    id: 'keyword',
    name: 'KeywordAgent',
    label: '关键词提取',
    icon: '🔑',
    description: '抽取核心意象、关键词和主题标签',
    input: '文本片段 / 用户主题',
    output: '关键词列表 + 意象图谱',
    status: 'success',
    detail: '使用 TF-IDF 和语义分析提取最具代表性的词语与意象。',
  },
  {
    id: 'retrieval',
    name: 'RetrievalAgent',
    label: '混合检索',
    icon: '🔍',
    description: 'BM25 召回 + BGE 向量 + Cross-Encoder 精排',
    input: '关键词 + 主题文本',
    output: '相似作品 + BM25/BGE/重排分数',
    status: 'success',
    detail: '在 5320 首诗歌库中先用 BM25 与 BGE-small-zh 混合召回，再用 bge-reranker Cross-Encoder 精排 Top 结果。',
  },
  {
    id: 'rag',
    name: 'RAGAgent',
    label: 'RAG 知识增强',
    icon: '📚',
    description: '对检索到的参考作品二次分析，提取可注入生成模型的结构化上下文',
    input: 'Top 3 相似作品',
    output: '参考意象 + 情感 + 原文片段',
    status: 'success',
    detail: '对参考诗再次分词、提取关键词并分析情绪，将结果组织为 WriterAgent 可使用的 RAG 上下文。',
  },
  {
    id: 'style',
    name: 'StyleAgent',
    label: '风格匹配',
    icon: '🎨',
    description: '匹配最适合的艺术风格与音乐氛围',
    input: '情感向量 + 关键词',
    output: '推荐艺术风格 + 音乐推荐',
    status: 'success',
    detail: '综合情感分析和关键词，从艺术风格库中匹配视觉风格与音乐。',
  },
  {
    id: 'writer',
    name: 'WriterAgent',
    label: '文本生成',
    icon: '✍️',
    description: '基于分析结果生成或润色文本',
    input: '所有前置 Agent 输出',
    output: '生成作品 / 润色后文本',
    status: 'success',
    detail: '融合意图、情感、关键词、RAG 参考作品和推荐风格，调用 DeepSeek WriterAgent 生成；失败时降级为算法模板。',
  },
  {
    id: 'summary',
    name: 'SummaryAgent',
    label: '结果汇总',
    icon: '📋',
    description: '整合所有 Agent 输出，呈现最终结果',
    input: '全部 Agent 输出',
    output: '结构化结果展示',
    status: 'success',
    detail: '将各 Agent 的结果整合为统一的 JSON 结构，便于前端渲染。',
  },
];

// ---------- 灵感生成结果（Mock） ----------
export const inspirationResults = {
  '城市孤独': {
    keywords: ['霓虹', '人潮', '地铁', '雨夜', '玻璃窗', '倒影'],
    emotion: { dominant: '孤独', scores: { 孤独: 0.85, 怀旧: 0.45, 温柔: 0.20, 激昂: 0.05, 治愈: 0.10 } },
    imagery: ['空荡的地铁车厢', '雨中的霓虹倒影', '高楼间的狭缝天空'],
    generated: `城市沉入夜色
霓虹在雨中晕开成模糊的暖光
地铁呼啸而过，带走最后一批
沉默的脸庞
玻璃窗上是另一个自己
和千万盏灯，都不属于我`,
    artStyle: '赛博朋克',
    music: '坂本龙一 — 《Rain》',
    similarWorks: [
      { title: '《孤独的根号三》', similarity: '0.87' },
      { title: '《灯》— 废名', similarity: '0.72' },
    ],
  },
  '黄昏与成长': {
    keywords: ['夕阳', '远山', '归鸟', '少年', '告别', '路途'],
    emotion: { dominant: '怀旧', scores: { 怀旧: 0.78, 温柔: 0.55, 孤独: 0.30, 激昂: 0.25, 治愈: 0.40 } },
    imagery: ['天边最后一抹橙色', '背着行囊的少年', '延伸至地平线的路'],
    generated: `黄昏把影子拉得很长很长
像极了十八岁那年，我们说过
要去远方
后来远山吞没了夕阳
归鸟衔走了最后一声告别
而我在路途中，慢慢长成了
自己`,
    artStyle: '印象派',
    music: '德彪西 — 《亚麻色头发的少女》',
    similarWorks: [
      { title: '《晚钟》— 洛尔迦', similarity: '0.81' },
      { title: '《送别》— 李叔同', similarity: '0.76' },
    ],
  },
  '雨夜里的自我和解': {
    keywords: ['雨声', '窗台', '灯火', '旧日记', '释然', '咖啡'],
    emotion: { dominant: '治愈', scores: { 治愈: 0.82, 温柔: 0.60, 怀旧: 0.50, 孤独: 0.35, 激昂: 0.05 } },
    imagery: ['雨滴滑过玻璃', '暖黄的台灯下', '翻开旧日记的手'],
    generated: `雨夜是最好的倾听者
它敲着窗，不急于说话
我把旧日记翻到最后一页
那些以为过不去的
都成了湿润的标点
咖啡凉了，而我终于
和镜子里的人握手言和`,
    artStyle: '极简主义',
    music: '肖邦 — 《雨滴前奏曲》',
    similarWorks: [
      { title: '《雨巷》— 戴望舒', similarity: '0.90' },
      { title: '《听听那冷雨》— 余光中', similarity: '0.84' },
    ],
  },
};

// ---------- 平台能力列表 ----------
export const platformCapabilities = [
  { icon: '🔑', title: '关键词提取', desc: '基于语义分析自动抽取文本核心意象与关键词' },
  { icon: '💭', title: '情感分析', desc: '多维度情感识别，精准捕捉文本情绪基调' },
  { icon: '🔍', title: '相似作品检索', desc: '从古典诗词和现代诗歌库中检索语义相近作品' },
  { icon: '🎨', title: '艺术风格分类', desc: '匹配印象派、水墨、赛博朋克等多种视觉艺术风格' },
  { icon: '✍️', title: '文本生成与润色', desc: '生成现代诗/古典诗/散文，并提供修辞优化建议' },
  { icon: '🤖', title: '多 Agent 调度', desc: '7 个专业 Agent 协作，覆盖从分析到创作全流程' },
];

// ---------- 创作类型选项 ----------
export const creationTypes = ['现代诗', '古典诗', '散文', '短篇片段'];

// ---------- 情绪基调选项 ----------
export const emotionTones = ['孤独', '温柔', '激昂', '怀旧', '治愈'];

// ---------- 艺术风格选项 ----------
export const artStyleOptions = ['印象派', '表现主义', '极简主义', '中国水墨', '赛博朋克', '超现实主义'];

// ---------- 知识库分类 ----------
export const knowledgeCategories = [
  { id: 'modern-poetry', label: '现代诗知识库', icon: '📖', source: '来源于 Iess/chinese_modern_poetry', count: '大量现代中文诗歌' },
  { id: 'classical-poetry', label: '古典诗词知识库', icon: '📜', source: '来源于 ZoneTwelve/chinese-poetry', count: '涵盖唐宋元明清经典' },
  { id: 'art-styles', label: '艺术风格知识库', icon: '🎨', source: '人工构建风格/音乐/情绪标签', count: '6 种核心艺术风格' },
];
