from __future__ import annotations

import json
import os
import uuid
from datetime import datetime
from typing import Optional

from app.core.settings import PROJECT_ROOT
FEEDBACK_PATH = os.getenv("FEEDBACK_PATH", str(PROJECT_ROOT / "storage" / "feedback.json"))


def _load() -> dict:
    os.makedirs(os.path.dirname(FEEDBACK_PATH), exist_ok=True)
    if not os.path.exists(FEEDBACK_PATH):
        return {"feedbacks": []}
    with open(FEEDBACK_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _save(data: dict) -> None:
    os.makedirs(os.path.dirname(FEEDBACK_PATH), exist_ok=True)
    with open(FEEDBACK_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def save_feedback(q: str, mode: str, rating: int, used_docs: list | None = None) -> dict:
    data = _load()
    entry = {
        "id": str(uuid.uuid4()),
        "timestamp": datetime.now().isoformat(),
        "q": q,
        "mode": mode,
        "rating": rating,  # 1 = 좋아요, -1 = 싫어요
        "used_docs": used_docs or [],
    }
    data["feedbacks"].append(entry)
    _save(data)
    return entry


def get_stats() -> dict:
    data = _load()
    feedbacks = data.get("feedbacks", [])

    mode_stats: dict[str, dict] = {}
    for fb in feedbacks:
        m = fb["mode"]
        if m not in mode_stats:
            mode_stats[m] = {"up": 0, "down": 0, "total": 0}
        if fb["rating"] == 1:
            mode_stats[m]["up"] += 1
        else:
            mode_stats[m]["down"] += 1
        mode_stats[m]["total"] += 1

    for m, s in mode_stats.items():
        s["score"] = round((s["up"] - s["down"]) / max(s["total"], 1), 2)

    recent = feedbacks[-5:][::-1]
    return {
        "total": len(feedbacks),
        "mode_stats": mode_stats,
        "recent": recent,
    }


def preferred_mode_for(q: str, min_samples: int = 2) -> Optional[str]:
    """비슷한 과거 질문의 피드백을 분석해 가장 좋은 평점을 받은 모드를 반환.
    데이터가 부족하면 None 반환 → 기본 라우팅 사용."""
    data = _load()
    feedbacks = data.get("feedbacks", [])
    if not feedbacks:
        return None

    q_words = set(q.lower().split())
    mode_scores: dict[str, list[int]] = {}

    for fb in feedbacks:
        fb_words = set(fb["q"].lower().split())
        overlap = len(q_words & fb_words)
        if overlap >= 2:
            mode_scores.setdefault(fb["mode"], []).append(fb["rating"])

    best_mode: Optional[str] = None
    best_score = -999.0
    for mode, ratings in mode_scores.items():
        if len(ratings) < min_samples:
            continue
        avg = sum(ratings) / len(ratings)
        if avg > best_score:
            best_score = avg
            best_mode = mode

    return best_mode if best_score > 0 else None
