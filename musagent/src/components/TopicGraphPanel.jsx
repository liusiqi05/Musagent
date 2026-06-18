import { Link } from 'react-router-dom';

import ForceGraphView from './ForceGraphView.jsx';
import { ROUTES } from '../config/routes.js';
import { relationLabel, verticalLabel } from '../constants/labels.js';

/** 灵感生成页 — 主题关系解释层（紧凑双栏） */
const TopicGraphPanel = ({ graph, topic = '' }) => {
  if (!graph || (!graph.nodes?.length && !graph.edges?.length)) {
    return null;
  }

  const domain = graph.verticalLabel || verticalLabel(graph.vertical);
  const highlightId = graph.topic || topic;

  return (
    <div className="topic-graph-panel panel-card">
      <div className="topic-graph-head">
        <h3 className="text-xs font-medium font-cjk" style={{ color: 'var(--text-muted)' }}>
          创作关联
        </h3>
        <Link to={ROUTES.knowledgeGraph.path} className="text-[10px] text-yellow hover:underline">
          完整图谱 →
        </Link>
      </div>

      <div className="topic-graph-split">
        <ForceGraphView
          nodes={graph.nodes}
          edges={graph.edges}
          width={280}
          height={200}
          highlightId={highlightId}
          compact
          className="topic-force-graph"
        />
        <div className="topic-graph-edges">
          {(graph.edges || []).slice(0, 6).map((edge, i) => (
            <div key={i} className="kg-edge-row text-[10px]">
              <span className="kg-edge-head truncate">{edge.head}</span>
              <span className="kg-edge-rel">{relationLabel(edge.relation)}</span>
              <span className="kg-edge-tail truncate">{edge.tail}</span>
            </div>
          ))}
        </div>
      </div>

      <p className="topic-graph-foot font-cjk">
        {graph.nodes?.length || 0} 个关联 · {domain}
      </p>
    </div>
  );
};

export default TopicGraphPanel;
