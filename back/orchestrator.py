"""
NLP Pipeline 编排器 — 分阶段执行、耗时统计、模型元数据
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable

from ml_models import get_stack_info


@dataclass
class StageRecord:
    id: str
    name: str
    model: str
    durationMs: float
    status: str = "ok"
    detail: str = ""


@dataclass
class PipelineContext:
    request: Any
    data: dict = field(default_factory=dict)
    stages: list[StageRecord] = field(default_factory=list)
    on_stage: Callable[[StageRecord, int], None] | None = None

    def run(self, stage_id: str, name: str, model: str, fn: Callable[[], Any]) -> Any:
        t0 = time.perf_counter()
        status = "ok"
        detail = ""
        try:
            result = fn()
        except Exception as exc:
            status = "error"
            detail = str(exc)[:120]
            raise
        finally:
            ms = round((time.perf_counter() - t0) * 1000, 1)
            record = StageRecord(stage_id, name, model, ms, status, detail)
            self.stages.append(record)
            if self.on_stage:
                self.on_stage(record, len(self.stages))
        return result


def stages_to_dict(stages: list[StageRecord]) -> list[dict]:
    return [
        {
            "id": s.id,
            "name": s.name,
            "model": s.model,
            "durationMs": s.durationMs,
            "status": s.status,
            "detail": s.detail,
        }
        for s in stages
    ]
