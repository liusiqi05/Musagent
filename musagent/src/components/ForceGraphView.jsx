import { useEffect, useMemo, useRef, useState } from 'react';

import { ENTITY_TYPE_COLORS, relationLabel } from '../constants/labels.js';

function buildSimNodes(nodes, edges, width, height, highlightId = '') {
  const ids = new Set();
  for (const n of nodes || []) ids.add(n.id);
  for (const e of edges || []) {
    ids.add(e.head);
    ids.add(e.tail);
  }

  const nodeMap = Object.fromEntries((nodes || []).map((n) => [n.id, n]));
  const simNodes = [...ids].map((id, i) => {
    const meta = nodeMap[id] || { id, type: 'unknown', weight: 1 };
    const angle = (2 * Math.PI * i) / Math.max(ids.size, 1);
    const r = Math.min(width, height) * 0.28;
    return {
      id,
      type: meta.type || 'unknown',
      weight: meta.weight || 1,
      x: width / 2 + r * Math.cos(angle),
      y: height / 2 + r * Math.sin(angle),
      vx: 0,
      vy: 0,
      pinned: id === highlightId,
    };
  });

  const simEdges = (edges || []).map((e) => ({
    head: e.head,
    tail: e.tail,
    relation: e.relation,
    source: e.source,
  }));

  return { simNodes, simEdges };
}

function tickSimulation(nodes, edges, width, height) {
  const centerX = width / 2;
  const centerY = height / 2;
  const alpha = 0.35;

  for (let i = 0; i < nodes.length; i += 1) {
    for (let j = i + 1; j < nodes.length; j += 1) {
      const a = nodes[i];
      const b = nodes[j];
      let dx = b.x - a.x;
      let dy = b.y - a.y;
      let dist = Math.hypot(dx, dy) || 1;
      const repulse = (9000 / (dist * dist)) * alpha;
      dx = (dx / dist) * repulse;
      dy = (dy / dist) * repulse;
      if (!a.pinned) { a.vx -= dx; a.vy -= dy; }
      if (!b.pinned) { b.vx += dx; b.vy += dy; }
    }
  }

  for (const e of edges) {
    const a = nodes.find((n) => n.id === e.head);
    const b = nodes.find((n) => n.id === e.tail);
    if (!a || !b) continue;
    let dx = b.x - a.x;
    let dy = b.y - a.y;
    const dist = Math.hypot(dx, dy) || 1;
    const spring = (dist - 72) * 0.045 * alpha;
    dx = (dx / dist) * spring;
    dy = (dy / dist) * spring;
    if (!a.pinned) { a.vx += dx; a.vy += dy; }
    if (!b.pinned) { b.vx -= dx; b.vy -= dy; }
  }

  for (const n of nodes) {
    if (n.pinned) continue;
    n.vx += (centerX - n.x) * 0.002 * alpha;
    n.vy += (centerY - n.y) * 0.002 * alpha;
    n.vx *= 0.82;
    n.vy *= 0.82;
    n.x += n.vx;
    n.y += n.vy;
    n.x = Math.max(24, Math.min(width - 24, n.x));
    n.y = Math.max(24, Math.min(height - 24, n.y));
  }
}

/**
 * 轻量力导向图 — 用于 KG 全站页与灵感子图
 */
const ForceGraphView = ({
  nodes = [],
  edges = [],
  width = 640,
  height = 420,
  highlightId = '',
  compact = false,
  onNodeClick,
  className = '',
}) => {
  const svgRef = useRef(null);
  const [positions, setPositions] = useState([]);
  const [hoverId, setHoverId] = useState('');
  const [selectedId, setSelectedId] = useState('');
  const dragRef = useRef(null);

  const { simNodes, simEdges } = useMemo(
    () => buildSimNodes(nodes, edges, width, height, highlightId),
    [nodes, edges, width, height, highlightId],
  );

  useEffect(() => {
    if (!simNodes.length) {
      setPositions([]);
      return undefined;
    }

    const working = simNodes.map((n) => ({ ...n }));
    let frame = 0;
    const maxFrames = compact ? 90 : 160;

    const animate = () => {
      tickSimulation(working, simEdges, width, height);
      frame += 1;
      if (frame % 2 === 0 || frame >= maxFrames) {
        setPositions(working.map((n) => ({ id: n.id, type: n.type, x: n.x, y: n.y, weight: n.weight })));
      }
      if (frame < maxFrames) {
        requestAnimationFrame(animate);
      }
    };

    requestAnimationFrame(animate);
    return undefined;
  }, [simNodes, simEdges, width, height, compact]);

  const posMap = useMemo(
    () => Object.fromEntries(positions.map((n) => [n.id, n])),
    [positions],
  );

  const handlePointerDown = (id, e) => {
    e.preventDefault();
    dragRef.current = { id, startX: e.clientX, startY: e.clientY };
  };

  const handlePointerMove = (e) => {
    if (!dragRef.current || !svgRef.current) return;
    const rect = svgRef.current.getBoundingClientRect();
    const scaleX = width / rect.width;
    const scaleY = height / rect.height;
    const dx = (e.clientX - dragRef.current.startX) * scaleX;
    const dy = (e.clientY - dragRef.current.startY) * scaleY;
    dragRef.current.startX = e.clientX;
    dragRef.current.startY = e.clientY;
    setPositions((prev) => prev.map((n) => (
      n.id === dragRef.current.id ? { ...n, x: n.x + dx, y: n.y + dy } : n
    )));
  };

  const handlePointerUp = () => {
    dragRef.current = null;
  };

  if (!simNodes.length) {
    return (
      <p className="text-sm font-cjk py-8 text-center" style={{ color: 'var(--text-muted)' }}>
        暂无节点可展示
      </p>
    );
  }

  const activeId = hoverId || selectedId || highlightId;
  const connected = new Set();
  if (activeId) {
    for (const e of simEdges) {
      if (e.head === activeId) connected.add(e.tail);
      if (e.tail === activeId) connected.add(e.head);
    }
  }

  return (
    <div
      className={`force-graph-wrap ${className}`}
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerUp}
      onPointerLeave={handlePointerUp}
    >
      <svg
        ref={svgRef}
        viewBox={`0 0 ${width} ${height}`}
        preserveAspectRatio="xMidYMid meet"
        className="force-graph-svg"
        role="img"
        aria-label="力导向关系图"
      >
        {simEdges.map((edge, i) => {
          const from = posMap[edge.head];
          const to = posMap[edge.tail];
          if (!from || !to) return null;
          const lit = activeId && (edge.head === activeId || edge.tail === activeId);
          return (
            <line
              key={`${edge.head}-${edge.tail}-${i}`}
              x1={from.x}
              y1={from.y}
              x2={to.x}
              y2={to.y}
              className={`force-graph-edge ${lit ? 'is-lit' : ''}`}
            />
          );
        })}

        {positions.map((node) => {
          const color = ENTITY_TYPE_COLORS[node.type] || ENTITY_TYPE_COLORS.unknown;
          const isTopic = node.id === highlightId;
          const r = isTopic ? 12 : Math.min(10, 5 + Math.log2((node.weight || 1) + 1));
          const dimmed = activeId && activeId !== node.id && !connected.has(node.id);
          const label = node.id.length > (compact ? 5 : 8)
            ? `${node.id.slice(0, compact ? 4 : 7)}…`
            : node.id;

          return (
            <g
              key={node.id}
              className="force-graph-node"
              style={{ opacity: dimmed ? 0.35 : 1 }}
              onPointerDown={(e) => handlePointerDown(node.id, e)}
              onPointerEnter={() => setHoverId(node.id)}
              onPointerLeave={() => setHoverId('')}
              onClick={() => {
                setSelectedId(node.id);
                onNodeClick?.(node.id);
              }}
            >
              <circle cx={node.x} cy={node.y} r={r + 4} fill="transparent" />
              <circle
                cx={node.x}
                cy={node.y}
                r={r}
                fill={color}
                fillOpacity={isTopic ? 1 : 0.85}
                stroke={isTopic ? '#e7d393' : 'transparent'}
                strokeWidth={2}
              />
              {!compact && (
                <text x={node.x} y={node.y + r + 12} textAnchor="middle" className="force-graph-label">
                  {label}
                </text>
              )}
            </g>
          );
        })}
      </svg>

      {!compact && activeId && (
        <div className="force-graph-tooltip font-cjk">
          <p className="font-medium text-yellow">{activeId}</p>
          <ul className="mt-1 space-y-0.5">
            {simEdges
              .filter((e) => e.head === activeId || e.tail === activeId)
              .slice(0, 4)
              .map((e, i) => (
                <li key={i} className="text-[10px]" style={{ color: 'var(--text-secondary)' }}>
                  {e.head === activeId ? '→' : '←'} {relationLabel(e.relation)}{' '}
                  {e.head === activeId ? e.tail : e.head}
                </li>
              ))}
          </ul>
        </div>
      )}
    </div>
  );
};

export default ForceGraphView;
