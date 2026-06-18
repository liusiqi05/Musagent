# -*- coding: utf-8 -*-
"""生成大作业报告插图（PNG）"""
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np

OUT_DIR = Path(__file__).resolve().parent / "figures"
OUT_DIR.mkdir(exist_ok=True)

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

COLORS = {
    "blue": "#1E40AF",
    "light_blue": "#DBEAFE",
    "green": "#059669",
    "light_green": "#D1FAE5",
    "amber": "#D97706",
    "light_amber": "#FEF3C7",
    "purple": "#7C3AED",
    "light_purple": "#EDE9FE",
    "gray": "#64748B",
    "dark": "#1E293B",
    "red": "#DC2626",
    "light_red": "#FEE2E2",
    "cyan": "#06B6D4",
    "light_cyan": "#CFFAFE",
}


def save(fig, name):
    path = OUT_DIR / name
    fig.savefig(path, dpi=250, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  {path.name}")


def box(ax, x, y, w, h, text, fc, ec="#334155", fs=9, bold=False, shadow=False):
    b = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.08",
                       facecolor=fc, edgecolor=ec, linewidth=1.2)
    ax.add_patch(b)
    if shadow:
        shadow_b = FancyBboxPatch((x + 0.03, y - 0.03), w, h, boxstyle="round,pad=0.02,rounding_size=0.08",
                                  facecolor="#E2E8F0", edgecolor="none", linewidth=0)
        ax.add_patch(shadow_b)
        ax.add_patch(b)
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs,
            color=COLORS["dark"], fontweight="bold" if bold else "normal", wrap=True)


def arrow(ax, x1, y1, x2, y2, color="#475569", lw=1.5, style="->"):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle=style, color=color, lw=lw, shrinkA=3, shrinkB=3))


def fig1_architecture():
    fig, ax = plt.subplots(figsize=(11, 7.5), dpi=120)
    ax.set_xlim(0, 11)
    ax.set_ylim(-0.5, 10)
    ax.axis("off")
    ax.set_title("图3-1  MusAgent 系统总体架构", fontsize=14, fontweight="bold", pad=20)

    layers = [
        (8.5, "表现层", "React + Vite\n灵感生成 / 知识库 / 润色 / 文摘 / 校错 / 评测", COLORS["light_blue"], COLORS["blue"]),
        (6.7, "接入层", "FastAPI REST\n/api/pipeline  /api/retrieve  /api/evaluate", COLORS["light_cyan"], COLORS["cyan"]),
        (4.9, "编排层", "PipelineContext\n阶段调度 · 耗时统计 · 异常降级", COLORS["light_amber"], COLORS["amber"]),
        (2.7, "语义引擎层", "分词 · NER · 情感 · 摘要 · 混合检索 · 可解释分析 · RAG", COLORS["light_purple"], COLORS["purple"]),
        (0.6, "数据与模型层", "5320首诗歌 JSON · BM25索引 · BGE向量 · 预训练模型", "#F1F5F9", COLORS["gray"]),
    ]
    
    layer_titles = ["Presentation\nLayer", "API\nGateway", "Orchestration\nLayer", "Semantic\nEngine", "Data &\nModel Layer"]
    
    for i, (y, title, desc, fc, ec) in enumerate(layers):
        box(ax, 0.8, y, 9.2, 1.3, f"【{layer_titles[i]}】\n{title}\n{desc}", fc, ec, fs=8.5, shadow=True)

    for i, y in enumerate([7.8, 6.0, 3.95, 2.0]):
        arrow(ax, 5.4, y, 5.4, y - 0.65, color=COLORS["gray"], lw=1.8)
        if i < 3:
            ax.text(5.5, y - 0.35, "REST/gRPC", fontsize=7, color=COLORS["gray"])
    
    ax.text(0.5, -0.3, "注：系统采用前后端分离架构，语义引擎层包含 12 个功能模块、14 类 NLP 技术", 
            fontsize=8, color=COLORS["gray"], wrap=True)
    save(fig, "fig1_system_architecture.png")


def fig2_pipeline():
    fig, ax = plt.subplots(figsize=(12, 8), dpi=120)
    ax.set_xlim(-0.5, 12)
    ax.set_ylim(-0.5, 10)
    ax.axis("off")
    ax.set_title("图4-1  NLP Pipeline 完整数据流（13阶段）", fontsize=14, fontweight="bold", pad=18)

    step_groups = [
        [("用户主题\nquery", 0.5, 8.6), ("Jieba\n分词", 2.2, 8.6), ("BERT-NER\n+意象词", 3.9, 8.6), 
         ("查询\n扩展", 5.6, 8.6), ("TF-IDF\n关键词", 7.3, 8.6), ("TextRank\n摘要", 9.0, 8.6)],
        [("BM25\n稀疏召回", 0.5, 5.8), ("BGE\n稠密召回", 2.8, 5.8), ("分数\n融合", 5.1, 5.8), 
         ("Cross-Encoder\n精排", 7.4, 5.8), ("Top-K\n候选", 9.7, 5.8)],
        [("融合\n情感分析", 1.2, 3.0), ("可解释\n语义分析", 3.8, 3.0), ("RAG\n结构化抽取", 6.4, 3.0), 
         ("DeepSeek\n/模板生成", 9.0, 3.0)],
        [("生成文本 + 化用标注", 4.0, 0.8)],
    ]
    
    colors = [COLORS["light_blue"], COLORS["light_green"], COLORS["light_amber"], 
              COLORS["light_purple"], COLORS["light_cyan"]]
    
    group_labels = ["预处理阶段", "检索阶段", "分析生成阶段", "输出阶段"]
    group_y = [9.8, 7.0, 4.2, 2.0]
    
    for i, (steps, label, y) in enumerate(zip(step_groups, group_labels, group_y)):
        ax.text(0.3, y, label, fontsize=9, fontweight="bold", color=COLORS["gray"])
        for j, (text, x, sy) in enumerate(steps):
            box(ax, x, sy, 1.5, 0.95, text, colors[i], fs=7.5)
    
    for i in range(5):
        arrow(ax, 1.75 + i * 1.7, 9.05, 1.95 + i * 1.7, 9.05, color=COLORS["blue"])
    arrow(ax, 5.6, 8.6, 1.25, 6.75, color=COLORS["gray"], lw=1.5)
    
    for i in range(4):
        arrow(ax, 2.05 + i * 2.3, 6.25, 2.25 + i * 2.3, 6.25, color=COLORS["green"])
    arrow(ax, 10.45, 5.8, 1.95, 3.95, color=COLORS["gray"], lw=1.5)
    
    for i in range(3):
        arrow(ax, 2.45 + i * 2.6, 3.45, 2.65 + i * 2.6, 3.45, color=COLORS["amber"])
    arrow(ax, 9.75, 3.0, 5.25, 1.75, color=COLORS["purple"], lw=1.5)

    legend_patches = [
        mpatches.Patch(color=COLORS["light_blue"], label="预处理"),
        mpatches.Patch(color=COLORS["light_green"], label="稀疏检索"),
        mpatches.Patch(color=COLORS["light_amber"], label="稠密检索"),
        mpatches.Patch(color=COLORS["light_purple"], label="精排/分析"),
        mpatches.Patch(color=COLORS["light_cyan"], label="生成"),
    ]
    ax.legend(handles=legend_patches, loc="upper right", bbox_to_anchor=(1.02, 0.95), fontsize=8)
    save(fig, "fig2_pipeline_flow.png")


def fig3_retrieval():
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 7)
    ax.axis("off")
    ax.set_title("图4-2  三级混合检索链路", fontsize=14, fontweight="bold", pad=14)

    box(ax, 0.5, 5.5, 2.2, 1.0, "Query\n(主题 + 扩展词)", COLORS["light_blue"], COLORS["blue"], bold=True)
    box(ax, 3.5, 5.8, 2.4, 0.8, "BM25 稀疏召回\nrecall_n=20", COLORS["light_green"], COLORS["green"])
    box(ax, 3.5, 4.5, 2.4, 0.8, "BGE 稠密召回\nbge-small-zh-v1.5", COLORS["light_amber"], COLORS["amber"])
    box(ax, 7.0, 5.15, 2.3, 1.0, "Min-Max 归一化\n+ 加权融合\nα=0.55", "#F1F5F9", COLORS["gray"])
    box(ax, 3.8, 2.5, 2.8, 1.0, "Cross-Encoder 精排\nbge-reranker-base", COLORS["light_purple"], COLORS["purple"], bold=True)
    box(ax, 3.8, 0.8, 2.8, 1.0, "Top-5 + rerankScore\n+ matchedTerms", "#FEE2E2", "#DC2626")

    arrow(ax, 2.7, 6.0, 3.5, 6.2)
    arrow(ax, 2.7, 6.0, 3.5, 4.9)
    arrow(ax, 5.9, 6.2, 7.0, 5.65)
    arrow(ax, 5.9, 4.9, 7.0, 5.65)
    arrow(ax, 8.15, 5.15, 5.2, 3.5)
    arrow(ax, 5.2, 2.5, 5.2, 1.8)

    ax.text(0.5, 0.3, "公式:  s_h = α·norm(BM25) + (1-α)·norm(cos_sim)  →  rerank(query, doc) → Top-K",
            fontsize=9, color=COLORS["gray"])
    save(fig, "fig3_hybrid_retrieval.png")


def fig4_emotion():
    fig, ax = plt.subplots(figsize=(9, 5.5))
    ax.set_xlim(0, 9)
    ax.set_ylim(0, 6)
    ax.axis("off")
    ax.set_title("图4-3  融合情感分析模型", fontsize=14, fontweight="bold", pad=14)

    box(ax, 0.5, 3.5, 2.0, 1.2, "输入文本\n+ 检索上下文", COLORS["light_blue"], COLORS["blue"])
    box(ax, 3.2, 4.5, 2.2, 1.0, "词典通道\n诗歌情感词表\n(6类)", COLORS["light_green"], COLORS["green"])
    box(ax, 3.2, 2.5, 2.2, 1.0, "RoBERTa 通道\nuer/roberta-\nfinetuned-jd", COLORS["light_amber"], COLORS["amber"])
    box(ax, 6.0, 3.3, 2.5, 1.4, "加权融合\nscore = 0.5·dict\n+ 0.5·roberta", COLORS["light_purple"], COLORS["purple"], bold=True)
    box(ax, 3.5, 0.5, 2.5, 1.0, "六维向量\n喜悦/悲伤/平静\n孤独/怀旧/激昂", "#FEE2E2", "#DC2626")

    arrow(ax, 2.5, 4.1, 3.2, 5.0)
    arrow(ax, 2.5, 3.9, 3.2, 3.0)
    arrow(ax, 5.4, 5.0, 6.0, 4.3)
    arrow(ax, 5.4, 3.0, 6.0, 3.9)
    arrow(ax, 7.25, 3.3, 4.75, 1.5)
    save(fig, "fig4_emotion_fusion.png")


def fig5_rag():
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 7)
    ax.axis("off")
    ax.set_title("图4-4  RAG 知识增强与化用标注流程", fontsize=14, fontweight="bold", pad=14)

    box(ax, 0.3, 5.2, 1.8, 1.0, "Top-3\n检索诗", COLORS["light_blue"], COLORS["blue"])
    box(ax, 2.5, 5.5, 1.8, 0.7, "分词", "#F1F5F9", COLORS["gray"], fs=8)
    box(ax, 2.5, 4.5, 1.8, 0.7, "关键词", "#F1F5F9", COLORS["gray"], fs=8)
    box(ax, 2.5, 3.5, 1.8, 0.7, "情感", "#F1F5F9", COLORS["gray"], fs=8)
    box(ax, 4.8, 4.2, 2.4, 1.6, "RAG 上下文\n· semanticSummary\n· adaptablePhrase\n· excerpt", COLORS["light_amber"], COLORS["amber"])
    box(ax, 7.8, 4.5, 1.8, 1.0, "LLM /\n模板", COLORS["light_purple"], COLORS["purple"], bold=True)
    box(ax, 3.5, 1.0, 3.5, 1.2, "生成诗歌 + citations\n「—— 化用自《标题》·作者：借鉴意象…」", "#FEE2E2", "#DC2626")

    arrow(ax, 2.1, 5.7, 2.5, 5.85)
    arrow(ax, 4.3, 4.9, 4.8, 5.0)
    arrow(ax, 7.2, 5.0, 7.8, 5.0)
    arrow(ax, 8.7, 4.5, 5.25, 2.2)
    save(fig, "fig5_rag_citation.png")


def fig6_explain():
    fig, ax = plt.subplots(figsize=(10, 5.5))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 6)
    ax.axis("off")
    ax.set_title("图4-5  可解释语义分析机制", fontsize=14, fontweight="bold", pad=14)

    box(ax, 0.4, 4.0, 2.0, 1.2, "用户主题\n+ 关键词\n+ 实体", COLORS["light_blue"], COLORS["blue"])
    box(ax, 3.0, 4.3, 1.8, 0.7, "BM25\n命中词", COLORS["light_green"], COLORS["green"], fs=8)
    box(ax, 3.0, 3.3, 1.8, 0.7, "意象\n重叠", COLORS["light_amber"], COLORS["amber"], fs=8)
    box(ax, 3.0, 2.3, 1.8, 0.7, "情感\n对比", COLORS["light_purple"], COLORS["purple"], fs=8)
    box(ax, 5.5, 3.2, 2.0, 1.4, "reasonTags\n+ summary\n+ adaptablePhrase", "#F1F5F9", COLORS["gray"])
    box(ax, 8.0, 3.5, 1.8, 1.0, "semantic\nInsight", "#FEE2E2", "#DC2626", bold=True)

    arrow(ax, 2.4, 4.6, 3.0, 4.65)
    arrow(ax, 2.4, 4.4, 3.0, 3.65)
    arrow(ax, 2.4, 4.2, 3.0, 2.65)
    arrow(ax, 4.8, 3.9, 5.5, 3.9)
    arrow(ax, 7.5, 3.9, 8.0, 4.0)
    save(fig, "fig6_explainability.png")


def fig7_ablation():
    topics = ["校园爱情", "地铁隐喻", "雨夜和解", "黄昏落叶", "春节乡愁", "咖啡馆"]
    bm25_scores = [4, 3, 3, 2, 4, 3]
    hybrid_scores = [5, 5, 5, 5, 5, 5]
    overlap = [4, 3, 3, 2, 4, 3]
    
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.5), dpi=120)
    x = np.arange(len(topics))
    w = 0.35
    
    axes[0].bar(x - w / 2, bm25_scores, w, label="BM25-only", 
                color=COLORS["light_green"], edgecolor=COLORS["green"], linewidth=1.2)
    axes[0].bar(x + w / 2, hybrid_scores, w, label="Hybrid (BM25+BGE+CE)", 
                color=COLORS["light_blue"], edgecolor=COLORS["blue"], linewidth=1.2)
    axes[0].set_xticks(x)
    axes[0].set_xticklabels(topics, fontsize=9, rotation=12)
    axes[0].set_ylabel("Top-5 召回数", fontsize=10)
    axes[0].set_title("(a) BM25-only 与 Hybrid 召回量对比", fontsize=11, fontweight="bold")
    axes[0].legend(fontsize=9, loc="upper right")
    axes[0].set_ylim(0, 6)
    axes[0].grid(axis="y", alpha=0.3, linestyle="--")
    axes[0].set_axisbelow(True)
    
    for i, (bm25, hybrid) in enumerate(zip(bm25_scores, hybrid_scores)):
        axes[0].text(i - w / 2, bm25 + 0.15, str(bm25), ha="center", fontsize=9, fontweight="bold", color=COLORS["green"])
        axes[0].text(i + w / 2, hybrid + 0.15, str(hybrid), ha="center", fontsize=9, fontweight="bold", color=COLORS["blue"])
    
    bars = axes[1].bar(topics, overlap, color=COLORS["light_amber"], edgecolor=COLORS["amber"], linewidth=1.2)
    axes[1].set_ylabel("Top-5 候选重叠数", fontsize=10)
    axes[1].set_title("(b) BM25 与 Hybrid 候选重叠分析", fontsize=11, fontweight="bold")
    axes[1].set_ylim(0, 6)
    axes[1].grid(axis="y", alpha=0.3, linestyle="--")
    axes[1].set_axisbelow(True)
    axes[1].set_xticklabels(topics, fontsize=9, rotation=12)
    
    for i, v in enumerate(overlap):
        axes[1].text(i, v + 0.15, str(v), ha="center", fontsize=9, fontweight="bold", color=COLORS["amber"])
        if v <= 3:
            bars[i].set_hatch("///")
    
    avg_overlap = sum(overlap) / len(overlap)
    axes[1].axhline(y=avg_overlap, color=COLORS["red"], linestyle="--", linewidth=1.5, 
                    label=f"平均重叠 {avg_overlap:.1f}")
    axes[1].legend(fontsize=9)
    
    axes[1].text(-0.3, 5.5, "阴影区域表示重叠率较低", fontsize=8, color=COLORS["gray"])
    
    fig.suptitle("图5-1  检索 Ablation 实验结果", fontsize=13, fontweight="bold", y=1.03)
    fig.tight_layout(pad=2.0)
    save(fig, "fig7_ablation_chart.png")


def fig8_er():
    """知识库 E-R 概念图（简化）"""
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.set_xlim(0, 8)
    ax.set_ylim(0, 5)
    ax.axis("off")
    ax.set_title("图3-2  知识库文档概念模型", fontsize=14, fontweight="bold", pad=14)

    box(ax, 2.5, 2.0, 3, 2.2, "", "#FFF", COLORS["blue"], fs=9)
    fields = ["PoemDocument", "— type: 现代诗|古典诗", "— title, author", "— content", "— words[], word_counts", "— embedding[512]"]
    for i, f in enumerate(fields):
        ax.text(2.7, 3.85 - i * 0.32, f, fontsize=9, color=COLORS["dark"], fontweight="bold" if i == 0 else "normal")

    box(ax, 0.5, 0.5, 2.2, 1.0, "BM25 倒排索引\n(df, tf, idf)", COLORS["light_green"], COLORS["green"], fs=8)
    box(ax, 5.3, 0.5, 2.2, 1.0, "BGE 向量索引\n(.npy 缓存)", COLORS["light_amber"], COLORS["amber"], fs=8)
    arrow(ax, 3.2, 2.0, 1.6, 1.5)
    arrow(ax, 4.8, 2.0, 6.4, 1.5)
    save(fig, "fig8_data_model.png")


def fig9_semantic_kg():
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 7)
    ax.axis("off")
    ax.set_title("图4-6  文学垂直知识图谱：语义关系抽取与展示", fontsize=14, fontweight="bold", pad=14)

    box(ax, 0.4, 5.2, 2.2, 1.2, "诗歌正文\n5320 首语料", COLORS["light_blue"], COLORS["blue"])
    box(ax, 3.0, 5.5, 2.0, 0.8, "Jieba 分词\n+ 意象词典", COLORS["light_green"], COLORS["green"], fs=8)
    box(ax, 3.0, 4.3, 2.0, 0.8, "词典情感\n(批量建图)", COLORS["light_amber"], COLORS["amber"], fs=8)
    box(ax, 5.5, 4.8, 2.4, 1.4, "诗内关系\nimagery_co_occurs\nevokes_emotion\ncontains_imagery", COLORS["light_purple"], COLORS["purple"], fs=8)
    box(ax, 5.5, 2.8, 2.4, 1.4, "跨诗统计\nemotion_resonance\ntheme_echo", "#FEE2E2", "#DC2626", fs=8)
    box(ax, 8.2, 4.0, 1.5, 2.0, "SQLite\nentities\nentity_relations", "#F1F5F9", COLORS["gray"], fs=8)
    box(ax, 2.5, 0.8, 5.0, 1.4, "展示层：sort_edges_by_literary_value + filter_edges(max_meta≤20%)\nD3 力导向图 · 关系类型均衡采样", COLORS["light_blue"], COLORS["blue"], fs=8)

    arrow(ax, 2.6, 5.8, 3.0, 5.9)
    arrow(ax, 2.6, 5.8, 3.0, 4.7)
    arrow(ax, 5.0, 5.9, 5.5, 5.5)
    arrow(ax, 5.0, 4.7, 5.5, 3.5)
    arrow(ax, 7.9, 5.5, 8.2, 5.0)
    arrow(ax, 7.9, 3.5, 8.2, 4.5)
    arrow(ax, 6.7, 2.8, 5.0, 2.2)
    save(fig, "fig9_semantic_kg.png")


def main():
    print("Generating figures...")
    fig1_architecture()
    fig2_pipeline()
    fig3_retrieval()
    fig4_emotion()
    fig5_rag()
    fig6_explain()
    fig7_ablation()
    fig8_er()
    fig9_semantic_kg()
    print("Done.")


if __name__ == "__main__":
    main()
