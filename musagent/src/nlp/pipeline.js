// ========== MusAgent Pipeline — 后端计算 ==========
// 所有 NLP 在后端完成，前端只调 API
import { checkBackend, remotePipeline } from './api.js';
import { consumePipelineStream } from '../utils/pipelineStream.js';

export async function runPipeline(params, { onStage, signal } = {}) {
  const ok = await checkBackend();
  if (!ok) throw new Error('后端未启动，请运行: cd back && python -m uvicorn main:app --port 8000');

  if (onStage) {
    return consumePipelineStream(params, { onStage, signal });
  }
  return remotePipeline({ useLLM: true, ...params });
}

export default { runPipeline };
