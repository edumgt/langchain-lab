from __future__ import annotations
import os, sqlite3, json, time, uuid
from typing import Any

from app.core.settings import PROJECT_ROOT
DB_PATH = os.getenv("ARTBIZ_DB", str(PROJECT_ROOT / "storage" / "artbiz_actions.sqlite"))

def _conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    c = sqlite3.connect(DB_PATH)
    c.execute("""CREATE TABLE IF NOT EXISTS actions(
        id TEXT PRIMARY KEY,
        created_at REAL,
        status TEXT,
        payload TEXT
    )""")
    return c

def create_action(payload: dict) -> dict:
    aid = str(uuid.uuid4())
    row = (aid, time.time(), "pending", json.dumps(payload, ensure_ascii=False))
    c = _conn()
    c.execute("INSERT INTO actions(id, created_at, status, payload) VALUES (?,?,?,?)", row)
    c.commit()
    c.close()
    return {"id": aid, "status": "pending", "payload": payload}

def get_action(action_id: str) -> dict | None:
    c = _conn()
    cur = c.execute("SELECT id, created_at, status, payload FROM actions WHERE id=?", (action_id,))
    r = cur.fetchone()
    c.close()
    if not r:
        return None
    return {"id": r[0], "created_at": r[1], "status": r[2], "payload": json.loads(r[3])}

def update_status(action_id: str, status: str) -> dict | None:
    c = _conn()
    c.execute("UPDATE actions SET status=? WHERE id=?", (status, action_id))
    c.commit()
    c.close()
    return get_action(action_id)
