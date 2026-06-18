const API_BASE = 'http://localhost:8000/api';

function parseSseChunk(buffer) {
  const events = [];
  const parts = buffer.split('\n\n');
  const rest = parts.pop() || '';

  for (const part of parts) {
    if (!part.trim()) continue;
    let event = 'message';
    let data = '';
    for (const line of part.split('\n')) {
      if (line.startsWith('event: ')) event = line.slice(7).trim();
      else if (line.startsWith('data: ')) data = line.slice(6);
    }
    if (data) {
      try {
        events.push({ event, data: JSON.parse(data) });
      } catch {
        events.push({ event, data: { raw: data } });
      }
    }
  }

  return { events, rest };
}

/** SSE 流式 Pipeline — 实时阶段进度 + 最终结果 */
export async function consumePipelineStream(params, { onStage, signal } = {}) {
  const resp = await fetch(`${API_BASE}/pipeline/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ useLLM: true, ...params }),
    signal,
  });

  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(`Pipeline SSE ${resp.status}: ${text.slice(0, 120)}`);
  }

  const reader = resp.body?.getReader();
  if (!reader) throw new Error('浏览器不支持流式响应');

  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const { events, rest } = parseSseChunk(buffer);
    buffer = rest;

    for (const { event, data } of events) {
      if (event === 'stage') onStage?.(data);
      else if (event === 'complete') return data;
      else if (event === 'error') throw new Error(data.message || 'Pipeline 执行失败');
    }
  }

  throw new Error('Pipeline 流意外结束，未收到完整结果');
}

export default { consumePipelineStream };
