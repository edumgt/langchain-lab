from fastapi.testclient import TestClient
from tests.conftest import install_optional_langchain_stubs

install_optional_langchain_stubs()

from app.server.main import app  # noqa: E402
from app.server import feedback  # noqa: E402


client = TestClient(app)


def test_health_endpoint():
    res = client.get("/health")
    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is True
    assert body["service"] == "langchain-lab-api"
    assert "X-Process-Time-Ms" in res.headers


def test_tools_budget_split_endpoint():
    res = client.post(
        "/tools/budget-split",
        json={"total_krw": 10000000, "paid_ads_ratio": 0.5, "content_ratio": 0.3, "community_ratio": 0.1, "contingency_ratio": 0.1},
    )
    assert res.status_code == 200
    assert res.json()["total"] == 10000000


def test_feedback_validation_and_submission(tmp_path, monkeypatch):
    monkeypatch.setattr(feedback, "FEEDBACK_PATH", str(tmp_path / "feedback.json"))

    bad = client.post("/feedback", json={"q": "test", "mode": "rag", "rating": 99})
    assert bad.status_code == 422

    ok = client.post("/feedback", json={"q": "test", "mode": "rag", "rating": 1, "used_docs": ["a.md"]})
    assert ok.status_code == 200
    assert ok.json()["ok"] is True


def test_proposal_template_and_check():
    tpl = client.get("/artbiz/proposal/template")
    assert tpl.status_code == 200
    md = tpl.json()["template"]
    assert isinstance(md, str) and len(md) > 0

    chk = client.post("/artbiz/proposal/check", json={"markdown": md})
    assert chk.status_code == 200
    assert chk.json()["ok"] is True
