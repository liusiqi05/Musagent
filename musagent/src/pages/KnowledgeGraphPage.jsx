import { useEffect, useMemo, useState } from 'react';

import { useGSAP } from '@gsap/react';

import gsap from 'gsap';

import PageHeader from '../components/PageHeader.jsx';
import ForceGraphView from '../components/ForceGraphView.jsx';

import {
  fetchKnowledgeGraph, fetchFeedbackStats, fetchReModelStatus, trainReModel, exportReSamples,
} from '../nlp/api.js';

import {
  verticalLabel, entityTypeLabel, relationLabel, ENTITY_TYPE_COLORS, ENTITY_TYPE_LABELS,
} from '../constants/labels.js';

const TYPE_FILTERS = [
  { key: 'all', label: '全部' },
  ...Object.entries(ENTITY_TYPE_LABELS).map(([key, label]) => ({ key, label })),
];

const KnowledgeGraphPage = () => {
  const [tab, setTab] = useState('browse');
  const [graph, setGraph] = useState(null);
  const [stats, setStats] = useState(null);
  const [entity, setEntity] = useState('');
  const [typeFilter, setTypeFilter] = useState('all');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [reModel, setReModel] = useState(null);
  const [trainStatus, setTrainStatus] = useState('');

  const loadGraph = async (searchEntity = '') => {
    setLoading(true);
    setError('');
    try {
      const [g, s, re] = await Promise.all([
        fetchKnowledgeGraph(60, searchEntity),
        fetchFeedbackStats(),
        tab === 'admin' ? fetchReModelStatus() : Promise.resolve(null),
      ]);
      setGraph(g);
      setStats(s);
      if (re) setReModel(re);
    } catch (err) {
      setError(err.message || '加载失败');
    }
    setLoading(false);
  };

  useEffect(() => {
    loadGraph();
  }, [tab]);

  useGSAP(() => {
    gsap.from('.kg-dashboard', { y: 16, opacity: 0, duration: 0.5, ease: 'power2.out' });
  }, [graph]);

  const handleExportSamples = async () => {
    setTrainStatus('正在导出训练样本…');
    try {
      const result = await exportReSamples(1200);
      setTrainStatus(`已导出 ${result.total} 条（正 ${result.positive} / 负 ${result.negative}）`);
    } catch (err) {
      setTrainStatus(`导出失败：${err.message}`);
    }
  };

  const handleTrainRE = async () => {
    setTrainStatus('BERT-RE 微调训练中，请耐心等待…');
    try {
      const result = await trainReModel({ epochs: 2, limit: 800, maxTrainSamples: 200 });
      if (result.success) {
        setTrainStatus(`训练完成 · 准确率约 ${(result.accuracy_estimate * 100).toFixed(1)}%`);
        setReModel(await fetchReModelStatus());
      } else {
        setTrainStatus(`训练失败：${result.error || '未知错误'}`);
      }
    } catch (err) {
      setTrainStatus(`训练失败：${err.message}`);
    }
  };

  const handleSearch = (e) => {
    e.preventDefault();
    loadGraph(entity.trim());
  };

  const domainLabel = graph?.verticalLabel || verticalLabel(graph?.vertical);

  const filteredNodes = useMemo(() => {
    const nodes = graph?.nodes || [];
    if (typeFilter === 'all') return nodes;
    return nodes.filter((n) => (n.type || 'unknown') === typeFilter);
  }, [graph, typeFilter]);

  const typeCounts = useMemo(() => {
    const counts = { all: (graph?.nodes || []).length };
    for (const n of graph?.nodes || []) {
      const t = n.type || 'unknown';
      counts[t] = (counts[t] || 0) + 1;
    }
    return counts;
  }, [graph]);

  const filteredEdges = useMemo(() => {
    const edges = graph?.edges || [];
    if (typeFilter === 'all') return edges;
    const ids = new Set(filteredNodes.map((n) => n.id));
    return edges.filter((e) => ids.has(e.head) || ids.has(e.tail));
  }, [graph, typeFilter, filteredNodes]);

  return (
    <section className="page-kg page-manuscript min-h-screen pb-16 pt-28 md:pt-32">
      <div className="container mx-auto px-4 max-w-6xl">
        <PageHeader
          badge="关系图谱"
          title="文学知识关系网络"
          description="作品、作者、意象与情感之间的关联 — 悬停节点查看关系，点击可聚焦搜索"
        />

        <div className="kg-tab-bar mb-5">
          <button type="button" className={`kg-tab ${tab === 'browse' ? 'is-active' : ''}`} onClick={() => setTab('browse')}>
            浏览图谱
          </button>
          <button type="button" className={`kg-tab ${tab === 'admin' ? 'is-active' : ''}`} onClick={() => setTab('admin')}>
            系统管理
          </button>
        </div>

        {tab === 'browse' && (
          <>
            <p className="info-banner mb-5 font-cjk text-sm">
              图谱展示<strong className="text-yellow font-normal">文本语义关系</strong>：意象共现、唤起情感、主题呼应等。
              「作者 / 体裁」仅作辅助，默认不超过两成。
            </p>

            <form onSubmit={handleSearch} className="kg-toolbar mb-5">
              <input
                type="text"
                value={entity}
                onChange={(e) => setEntity(e.target.value)}
                placeholder="搜索实体：李白、月亮、校园爱情…"
                className="kg-toolbar-input font-cjk"
              />
              <button type="submit" className="kg-toolbar-btn is-primary">查询</button>
              <button type="button" onClick={() => { setEntity(''); setTypeFilter('all'); loadGraph(''); }} className="kg-toolbar-btn">重置</button>
            </form>

            {loading && (
              <div className="kg-loading font-cjk">正在加载图谱…</div>
            )}
            {error && <p className="text-red-400 font-cjk mb-4">{error}</p>}

            {graph && !loading && (
              <div className="kg-dashboard">
                <div className="kg-inline-stats">
                  <span className="kg-stat-pill"><b>{graph.entityCount || 0}</b> 实体</span>
                  <span className="kg-stat-pill"><b>{graph.relationCount || 0}</b> 关系</span>
                  <span className="kg-stat-pill is-muted">{domainLabel}</span>
                  <span className="kg-stat-pill is-muted">
                    好评 {stats?.overall?.avg ?? '-'} · {stats?.overall?.c ?? 0} 条
                  </span>
                </div>

                <div className="kg-split-layout">
                  <div className="kg-graph-pane panel-card">
                    <div className="kg-pane-head">
                      <h3 className="font-cjk">关系网络</h3>
                      <p className="font-cjk">拖拽节点 · 点击查看详情</p>
                    </div>
                    <ForceGraphView
                      nodes={graph.nodes}
                      edges={graph.edges}
                      width={640}
                      height={360}
                      highlightId={entity.trim()}
                      onNodeClick={(id) => { setEntity(id); loadGraph(id); }}
                      className="kg-force-canvas"
                    />
                  </div>

                  <div className="kg-side-pane">
                    <div className="kg-side-block panel-card">
                      <h3 className="font-cjk text-sm mb-2">实体</h3>
                      <div className="kg-type-filter">
                        {TYPE_FILTERS.map((f) => (
                          <button
                            key={f.key}
                            type="button"
                            className={`kg-type-pill ${typeFilter === f.key ? 'is-active' : ''}`}
                            onClick={() => setTypeFilter(f.key)}
                          >
                            {f.label}
                            {typeCounts[f.key] != null && ` (${typeCounts[f.key]})`}
                          </button>
                        ))}
                      </div>
                      <div className="kg-node-scroll">
                        {filteredNodes.map((node) => (
                          <button
                            key={node.id}
                            type="button"
                            onClick={() => { setEntity(node.id); loadGraph(node.id); }}
                            className="kg-node-chip"
                            style={{ borderColor: ENTITY_TYPE_COLORS[node.type] || ENTITY_TYPE_COLORS.unknown }}
                            title={node.id}
                          >
                            <span className="kg-node-type" style={{ color: ENTITY_TYPE_COLORS[node.type] || ENTITY_TYPE_COLORS.unknown }}>
                              {node.typeLabel || entityTypeLabel(node.type)}
                            </span>
                            <span className="kg-node-name">{node.id}</span>
                          </button>
                        ))}
                        {!filteredNodes.length && (
                          <p className="text-xs font-cjk py-4 text-center" style={{ color: 'var(--text-muted)' }}>
                            暂无实体
                          </p>
                        )}
                      </div>
                    </div>

                    <div className="kg-side-block panel-card">
                      <h3 className="font-cjk text-sm mb-2">关系 ({filteredEdges.length})</h3>
                      <div className="kg-edge-scroll">
                        {filteredEdges.map((edge, i) => (
                          <div key={i} className="kg-edge-row">
                            <span className="kg-edge-head" title={edge.head}>{edge.head}</span>
                            <span className="kg-edge-rel">{relationLabel(edge.relation)}</span>
                            <span className="kg-edge-tail" title={edge.tail}>{edge.tail}</span>
                          </div>
                        ))}
                        {!filteredEdges.length && (
                          <p className="text-xs font-cjk py-4 text-center" style={{ color: 'var(--text-muted)' }}>暂无关系</p>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </>
        )}

        {tab === 'admin' && (
          <div className="kg-card panel-card max-w-2xl">
            <h3 className="text-lg mb-2 font-cjk">BERT 关系抽取 · 系统管理</h3>
            <p className="text-xs mb-4 font-cjk" style={{ color: 'var(--text-muted)' }}>
              面向开发者：导出训练样本、微调 RE 模型。
            </p>
            <p className="text-[10px] mb-4 font-cjk" style={{ color: 'var(--text-secondary)' }}>
              基座：{reModel?.baseModel || 'hfl/chinese-bert-wwm-ext'}
              {reModel?.available ? ' · 已训练' : ' · 未训练'}
              {reModel?.accuracy_estimate != null && ` · 准确率约 ${(reModel.accuracy_estimate * 100).toFixed(1)}%`}
            </p>
            <div className="flex gap-2 flex-wrap">
              <button type="button" onClick={handleExportSamples} className="kg-btn-outline px-4 py-2 rounded-xl text-xs">导出训练样本</button>
              <button type="button" onClick={handleTrainRE} className="px-4 py-2 rounded-xl text-xs bg-yellow text-black font-medium">开始微调</button>
            </div>
            {trainStatus && <p className="text-[10px] mt-3 font-cjk" style={{ color: 'var(--text-secondary)' }}>{trainStatus}</p>}
          </div>
        )}
      </div>
    </section>
  );
};

export default KnowledgeGraphPage;
