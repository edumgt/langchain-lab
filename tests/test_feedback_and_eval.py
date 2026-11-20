from app.server import eval as eval_mod
from app.server import feedback


def test_feedback_save_and_stats(tmp_path, monkeypatch):
    fb_file = tmp_path / "feedback.json"
    monkeypatch.setattr(feedback, "FEEDBACK_PATH", str(fb_file))

    entry1 = feedback.save_feedback("RAG 질문", "rag", 1, ["doc1.md"])
    entry2 = feedback.save_feedback("일반 채팅", "chat", -1, [])
    assert entry1["id"]
    assert entry2["id"]

    stats = feedback.get_stats()
    assert stats["total"] == 2
    assert stats["mode_stats"]["rag"]["up"] == 1
    assert stats["mode_stats"]["chat"]["down"] == 1


def test_eval_full_report(tmp_path, monkeypatch):
    fb_file = tmp_path / "feedback.json"
    monkeypatch.setattr(feedback, "FEEDBACK_PATH", str(fb_file))
    feedback.save_feedback("Q1", "rag", 1, ["a.md"])

    report = eval_mod.full_report(total_responses=2)
    assert isinstance(report, dict)
    assert len(report) > 0
