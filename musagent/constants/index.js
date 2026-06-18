const navLinks = [
 {
	id: "cocktails",
	title: "灵感生成",
 },
 {
	id: "about",
	title: "知识库",
 },
 {
	id: "work",
	title: "Agent 工作流",
 },
 {
	id: "contact",
	title: "创作润色",
 },
];

const inspirationTopicLists = [
 {
	name: "城市孤独",
	type: "现代诗",
	scenario: "意象生成",
	emotion: "孤独",
 },
 {
	name: "黄昏与成长",
	type: "现代诗",
	scenario: "散文片段",
	emotion: "怀旧",
 },
 {
	name: "雨夜里的自我和解",
	type: "现代诗",
	scenario: "短篇创作",
	emotion: "治愈",
 },
 {
	name: "春日漫游",
	type: "古典诗",
	scenario: "五言绝句",
	emotion: "温柔",
 },
];

const creationStyleLists = [
 {
	name: "月光奏鸣",
	type: "古典词",
	scenario: "宋词风格",
	emotion: "宁静",
 },
 {
	name: "山海远行",
	type: "现代诗",
	scenario: "自由体",
	emotion: "激昂",
 },
 {
	name: "旧日来信",
	type: "散文",
	scenario: "抒情片段",
	emotion: "怀旧",
 },
 {
	name: "星火微光",
	type: "短篇",
	scenario: "极简主义",
	emotion: "治愈",
 },
];

const profileLists = [
 {
	imgPath: "/images/profile1.png",
 },
 {
	imgPath: "/images/profile2.png",
 },
 {
	imgPath: "/images/profile3.png",
 },
 {
	imgPath: "/images/profile4.png",
 },
];

const featureLists = [
 "多 Agent 协作调度",
 "文本情感多维分析",
 "古典与现代诗词检索",
 "艺术风格智能匹配",
];

const goodLists = [
 "自然语言意图理解",
 "关键词与意象提取",
 "音乐情绪氛围推荐",
 "文本润色与修辞优化",
];

const storeInfo = {
 heading: "关于 MusAgent",
 address: "基于多智能体协作的文学与艺术灵感生成平台",
 contact: {
	phone: "",
	email: "lsq1783198384@icloud.com",
 },
};

const openingHours = [
 { day: "意图识别", time: "IntentAgent" },
 { day: "情感分析", time: "EmotionAgent" },
 { day: "关键词提取", time: "KeywordAgent" },
 { day: "文本生成", time: "WriterAgent" },
];

const socials = [
 {
	name: "GitHub",
	url: "https://github.com/liusiqi05/Musagent",
 },
];

const creationShowcases = [
 {
	id: 1,
	name: "现代诗",
	image: "/images/drink1.png",
	title: "自由与韵律的交织",
	description:
	 "现代诗打破格律束缚，以自由的形式承载最深的情感。从意象到隐喻，每一行都是心灵的回响。",
 },
 {
	id: 2,
	name: "古典诗词",
	image: "/images/drink2.png",
	title: "千年文脉的凝练之美",
	description:
	 "从唐诗的雄浑到宋词的婉约，古典诗词以极简的文字构建无限的意境。对仗、押韵、典故——字字珠玑。",
 },
 {
	id: 3,
	name: "散文片段",
	image: "/images/drink3.png",
	title: "日常中的诗意栖居",
	description:
	 "散文是灵魂的散步——不拘形式，不设边界。在寻常事物中发现不寻常的美，于平淡中见真淳。",
 },
 {
	id: 4,
	name: "创作润色",
	image: "/images/drink4.png",
	title: "让每个词语找到最佳位置",
	description:
	 "多 Agent 协作分析你的文本——从情感基调到修辞手法，从意象密度到节奏韵律，精雕细琢每一个表达。",
 },
];

export {
 navLinks,
 inspirationTopicLists,
 creationStyleLists,
 profileLists,
 featureLists,
 goodLists,
 openingHours,
 storeInfo,
 socials,
 creationShowcases,
};
