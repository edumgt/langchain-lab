from __future__ import annotations
import os, json, time
from typing import Any, Dict, List

from app.core.settings import PROJECT_ROOT
QUEUE_PATH = os.getenv("INDEX_QUEUE", str(PROJECT_ROOT / "storage" / "index_queue.jsonl"))

def enqueue(job: dict) -> dict:
    os.makedirs(os.path.dirname(QUEUE_PATH), exist_ok=True)
    job = {**job, "ts": time.time()}
    with open(QUEUE_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(job, ensure_ascii=False) + "\n")
    return job

def read_jobs(max_jobs: int = 50) -> list[dict]:
    if not os.path.exists(QUEUE_PATH):
        return []
    jobs = []
    with open(QUEUE_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                jobs.append(json.loads(line))
            except Exception:
                continue
    return jobs[:max_jobs]

def clear_queue():
    if os.path.exists(QUEUE_PATH):
        os.remove(QUEUE_PATH)
