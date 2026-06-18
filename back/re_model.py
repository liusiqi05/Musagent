"""
BERT 关系抽取 — 训练、推理、模型状态管理。
输入格式：text [SEP] head [SEP] tail → 关系类型分类
"""
from __future__ import annotations

import json
import logging
import os
import random
from pathlib import Path
from typing import Any

from config import BASE_DIR

logger = logging.getLogger("musagent.re")

RE_BASE_MODEL = os.getenv("RE_BASE_MODEL", "hfl/chinese-bert-wwm-ext")
RE_MODEL_DIR = Path(os.getenv("RE_MODEL_DIR", str(BASE_DIR / ".cache" / "re_model")))
RE_CONFIDENCE_THRESHOLD = float(os.getenv("RE_CONFIDENCE_THRESHOLD", "0.55"))

RELATION_LABELS = [
    "no_relation",
    "authored_by",
    "has_emotion",
    "contains_imagery",
    "belongs_to_type",
    "co_occurs_with",
    "inspired_by",
    "has_attribute",
    "located_in",
    "related_to",
    "metaphor_of",
]

_trainable_relations = {
    "authored_by", "has_emotion", "contains_imagery", "belongs_to_type",
    "co_occurs_with", "inspired_by",
}

_re_tokenizer = None
_re_model = None
_re_loaded = False


def get_re_model_info() -> dict:
    meta_path = RE_MODEL_DIR / "re_meta.json"
    meta = {}
    if meta_path.exists():
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
        except Exception:
            pass
    return {
        "baseModel": RE_BASE_MODEL,
        "modelDir": str(RE_MODEL_DIR),
        "loaded": _re_model is not None,
        "available": RE_MODEL_DIR.exists() and (RE_MODEL_DIR / "config.json").exists(),
        "labels": RELATION_LABELS,
        "threshold": RE_CONFIDENCE_THRESHOLD,
        **meta,
    }


def _encode_sample(text: str, head: str, tail: str) -> str:
    return f"{text[:200]} [SEP] {head[:32]} [SEP] {tail[:32]}"


def build_dataset_with_negatives(poems: list[dict], limit: int = 2000, neg_ratio: float = 0.4) -> list[dict]:
    """从诗歌元数据构建正负样本。"""
    from kg_engine import build_poem_relations

    positives: list[dict] = []
    texts_entities: list[tuple[str, list[str]]] = []

    poem_list = (poems or [])[:limit]
    if not poem_list:
        try:
            import nlp_engine
            poem_list = nlp_engine.get_poem_list()[:limit]
        except Exception:
            poem_list = []

    for poem in poem_list:
        text = f"{poem.get('title', '')} {poem.get('content', '')}"[:256]
        rels = build_poem_relations(poem)
        entities = set()
        for rel in rels:
            if rel["relation"] in _trainable_relations:
                positives.append({
                    "text": text,
                    "head": rel["head"],
                    "tail": rel["tail"],
                    "relation": rel["relation"],
                    "label": 1,
                })
                entities.add(rel["head"])
                entities.add(rel["tail"])
        if len(entities) >= 2:
            texts_entities.append((text, list(entities)))

    negatives: list[dict] = []
    target_neg = int(len(positives) * neg_ratio)
    attempts = 0
    while len(negatives) < target_neg and attempts < target_neg * 10:
        attempts += 1
        if not texts_entities:
            break
        text, ents = random.choice(texts_entities)
        if len(ents) < 2:
            continue
        h, t = random.sample(ents, 2)
        key = (text[:80], h, t)
        if any(p["text"][:80] == key[0] and p["head"] == h and p["tail"] == t for p in positives):
            continue
        negatives.append({"text": text, "head": h, "tail": t, "relation": "no_relation", "label": 0})

    return positives + negatives


def export_dataset(poems: list[dict], output_path: str, limit: int = 2000) -> dict:
    samples = build_dataset_with_negatives(poems, limit=limit)
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for row in samples:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    pos = sum(1 for s in samples if s["label"] == 1)
    return {
        "path": str(path),
        "total": len(samples),
        "positive": pos,
        "negative": len(samples) - pos,
        "relations": list({s["relation"] for s in samples if s["label"] == 1}),
    }


def train_relation_model(
    samples_path: str | None = None,
    poems: list[dict] | None = None,
    epochs: int = 2,
    batch_size: int = 16,
    max_samples: int = 1500,
    max_train_samples: int = 400,
    learning_rate: float = 2e-5,
) -> dict:
    """微调 BERT 关系分类器并保存到 RE_MODEL_DIR。"""
    try:
        import torch
        from torch.utils.data import Dataset
        from transformers import AutoModelForSequenceClassification, AutoTokenizer, Trainer, TrainingArguments
    except ImportError as exc:
        return {"success": False, "error": f"缺少依赖: {exc}"}

    if samples_path and Path(samples_path).exists():
        samples = []
        with open(samples_path, "r", encoding="utf-8") as f:
            for line in f:
                samples.append(json.loads(line))
    elif poems:
        samples = build_dataset_with_negatives(poems, limit=max_samples)
    else:
        return {"success": False, "error": "需要 samples_path 或 poems"}

    if len(samples) < 20:
        return {"success": False, "error": f"样本不足: {len(samples)}"}

    if len(samples) > max_train_samples:
        random.seed(42)
        samples = random.sample(samples, max_train_samples)

    label2id = {label: i for i, label in enumerate(RELATION_LABELS)}
    id2label = {i: label for label, i in label2id.items()}

    texts = [_encode_sample(s["text"], s["head"], s["tail"]) for s in samples]
    labels = [label2id.get(s["relation"], 0) for s in samples]

    tokenizer = AutoTokenizer.from_pretrained(RE_BASE_MODEL)
    encodings = tokenizer(texts, truncation=True, padding=True, max_length=256)

    class REDataset(Dataset):
        def __len__(self):
            return len(labels)

        def __getitem__(self, idx):
            item = {k: torch.tensor(v[idx]) for k, v in encodings.items()}
            item["labels"] = torch.tensor(labels[idx])
            return item

    model = AutoModelForSequenceClassification.from_pretrained(
        RE_BASE_MODEL,
        num_labels=len(RELATION_LABELS),
        id2label=id2label,
        label2id=label2id,
    )

    RE_MODEL_DIR.mkdir(parents=True, exist_ok=True)
    args = TrainingArguments(
        output_dir=str(RE_MODEL_DIR / "checkpoints"),
        num_train_epochs=epochs,
        per_device_train_batch_size=batch_size,
        learning_rate=learning_rate,
        logging_steps=50,
        save_strategy="no",
        report_to=[],
        use_cpu=not torch.cuda.is_available(),
    )

    trainer = Trainer(model=model, args=args, train_dataset=REDataset())
    trainer.train()

    model.save_pretrained(RE_MODEL_DIR)
    tokenizer.save_pretrained(RE_MODEL_DIR)

    meta = {
        "samples": len(samples),
        "epochs": epochs,
        "baseModel": RE_BASE_MODEL,
        "maxTrainSamples": max_train_samples,
        "accuracy_estimate": round(_quick_eval(model, tokenizer, samples[: min(200, len(samples))]), 3),
    }
    with open(RE_MODEL_DIR / "re_meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    global _re_model, _re_tokenizer, _re_loaded
    _re_model = model
    _re_tokenizer = tokenizer
    _re_loaded = True

    logger.info("RE model trained: %s samples, saved to %s", len(samples), RE_MODEL_DIR)
    return {"success": True, "modelDir": str(RE_MODEL_DIR), **meta}


def _quick_eval(model, tokenizer, samples: list[dict]) -> float:
    import torch
    label2id = {label: i for i, label in enumerate(RELATION_LABELS)}
    correct = 0
    model.eval()
    with torch.no_grad():
        for s in samples:
            text = _encode_sample(s["text"], s["head"], s["tail"])
            inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=256)
            logits = model(**inputs).logits
            pred = int(logits.argmax(dim=-1).item())
            if pred == label2id.get(s["relation"], 0):
                correct += 1
    return correct / max(len(samples), 1)


def _load_re_model():
    global _re_model, _re_tokenizer, _re_loaded
    if _re_loaded:
        return _re_model, _re_tokenizer
    if not (RE_MODEL_DIR / "config.json").exists():
        _re_loaded = True
        return None, None
    try:
        from transformers import AutoModelForSequenceClassification, AutoTokenizer
        _re_tokenizer = AutoTokenizer.from_pretrained(RE_MODEL_DIR)
        _re_model = AutoModelForSequenceClassification.from_pretrained(RE_MODEL_DIR)
        _re_model.eval()
        _re_loaded = True
        logger.info("Loaded RE model from %s", RE_MODEL_DIR)
        return _re_model, _re_tokenizer
    except Exception as exc:
        logger.warning("RE model load failed: %s", exc)
        _re_loaded = True
        return None, None


def predict_relation(text: str, head: str, tail: str) -> dict | None:
    model, tokenizer = _load_re_model()
    if model is None or tokenizer is None:
        return None
    try:
        import torch
        encoded = _encode_sample(text, head, tail)
        inputs = tokenizer(encoded, return_tensors="pt", truncation=True, max_length=256)
        with torch.no_grad():
            logits = model(**inputs).logits
            probs = torch.softmax(logits, dim=-1)[0]
            pred_id = int(probs.argmax().item())
            confidence = float(probs[pred_id].item())
        relation = RELATION_LABELS[pred_id] if pred_id < len(RELATION_LABELS) else "no_relation"
        return {
            "head": head,
            "tail": tail,
            "relation": relation,
            "confidence": round(confidence, 3),
            "source": "bert-re",
        }
    except Exception as exc:
        logger.warning("RE predict failed: %s", exc)
        return None


def extract_relations_bert(text: str, entities: dict | None = None, max_pairs: int = 20) -> list[dict]:
    """用微调 BERT-RE 对实体对预测关系。"""
    model, _ = _load_re_model()
    if model is None:
        return []

    flat: list[tuple[str, str]] = []
    ent_map = entities.get("entities") if isinstance(entities, dict) and entities.get("entities") else entities
    if isinstance(ent_map, dict):
        for etype, words in ent_map.items():
            if isinstance(words, list):
                for w in words:
                    if w and len(w) >= 2:
                        flat.append((w, etype))

    if len(flat) < 2:
        return []

    relations = []
    pair_count = 0
    for i, (h, ht) in enumerate(flat):
        for j, (t, tt) in enumerate(flat):
            if i >= j or pair_count >= max_pairs:
                continue
            pair_count += 1
            pred = predict_relation(text, h, t)
            if not pred:
                continue
            if pred["relation"] == "no_relation" or pred["confidence"] < RE_CONFIDENCE_THRESHOLD:
                continue
            relations.append({
                **pred,
                "metadata": {"headType": ht, "tailType": tt},
            })
    return relations
