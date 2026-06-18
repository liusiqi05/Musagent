#!/usr/bin/env python3
"""
BERT 关系抽取微调 CLI

用法:
  python train_re.py                    # 从诗歌库导出样本并训练
  python train_re.py --export-only      # 仅导出 JSONL
  python train_re.py --samples data/re_training_samples.jsonl
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import nlp_engine
from re_model import export_dataset, train_relation_model, get_re_model_info


def _get_poems():
    return nlp_engine.get_poem_list()


def main():
    parser = argparse.ArgumentParser(description="MusAgent BERT-RE 微调")
    parser.add_argument("--export-only", action="store_true", help="仅导出训练样本")
    parser.add_argument("--samples", default="", help="已有 JSONL 样本路径")
    parser.add_argument("--limit", type=int, default=1500, help="诗歌采样上限")
    parser.add_argument("--epochs", type=int, default=2, help="训练轮数")
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--max-train", type=int, default=400, help="训练时实际使用的样本上限")
    args = parser.parse_args()

    poems = _get_poems()
    out = Path(__file__).resolve().parent / "data" / "re_training_samples.jsonl"

    if args.export_only:
        result = export_dataset(poems, str(out), limit=args.limit)
        print(f"导出完成: {result}")
        return

    samples_path = args.samples or str(out)
    if not args.samples:
        export_result = export_dataset(poems, str(out), limit=args.limit)
        print(f"样本导出: {export_result}")

    result = train_relation_model(
        samples_path=samples_path,
        epochs=args.epochs,
        batch_size=args.batch_size,
        max_samples=args.limit,
        max_train_samples=args.max_train,
    )
    print(f"训练结果: {result}")
    print(f"模型状态: {get_re_model_info()}")


if __name__ == "__main__":
    main()
