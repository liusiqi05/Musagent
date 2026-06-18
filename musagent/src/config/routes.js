/** 全站路由与导航配置 — 用户创作路径 vs 系统技术页分离 */

export const ROUTES = {
  home: { path: '/', label: '首页' },
  inspire: { path: '/inspire', label: '灵感生成', desc: '主题输入 → 生成 → 评价 → 润色' },
  library: { path: '/library', label: '知识库', desc: '5320 首诗词检索与参考' },
  polish: { path: '/polish', label: '创作润色', desc: '保留原意的文学化改写' },
  summary: { path: '/summary', label: '自动文摘', desc: '长文压缩为精华摘要' },
  correct: { path: '/correct', label: '文本校错', desc: '错别字与标点规范' },
  login: { path: '/login', label: '登录', desc: '跨设备同步对话与创作记录' },
  knowledgeGraph: { path: '/knowledge-graph', label: '关系图谱', desc: '作品·作者·意象关联网络' },
  workflow: { path: '/workflow', label: '流水线架构', desc: '模块化 NLP 流水线说明' },
  stack: { path: '/stack', label: '模型技术栈', desc: 'Transformer-RAG 组件' },
  // v3.0 重命名：算法评测从 /evaluate 移到 /benchmark
  evaluate: { path: '/evaluate', label: '算法评测 (旧)', desc: '旧路径，重定向到 /benchmark' },
  benchmark: { path: '/benchmark', label: '算法评测', desc: '开发者定量 benchmark' },
};

/** 桌面顶栏主入口（创作者常用） */
export const NAV_PRIMARY = [
  ROUTES.inspire,
  ROUTES.library,
  ROUTES.polish,
];

/** 收进「更多」的下拉菜单 */
export const NAV_MORE = [
  { group: '工具', items: [ROUTES.summary, ROUTES.correct] },
  { group: '系统', items: [ROUTES.knowledgeGraph, ROUTES.workflow, ROUTES.stack, ROUTES.benchmark] },
];

/** 移动端抽屉分组（完整列表） */
export const NAV_GROUPS = [
  { id: 'create', label: '创作', items: [ROUTES.inspire, ROUTES.library, ROUTES.polish] },
  { id: 'tools', label: '工具', items: [ROUTES.summary, ROUTES.correct] },
  { id: 'system', label: '系统', items: [ROUTES.knowledgeGraph, ROUTES.workflow, ROUTES.stack, ROUTES.benchmark] },
];

export const LEGACY_REDIRECTS = {
  '/cocktails': ROUTES.inspire.path,
  '/menu': ROUTES.library.path,
  '/contact': ROUTES.polish.path,
  '/about': ROUTES.workflow.path,
  '/evaluate': ROUTES.benchmark.path,
};

export const allNavPaths = NAV_GROUPS.flatMap((g) => g.items.map((i) => i.path));
