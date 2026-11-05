"""Offline tests (no API key needed): chunking, long-term memory, MCP server round-trip."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import config, memory, rag, agent


def test_chunking():
    ch = rag.chunk(open(os.path.join(config.KNOWLEDGE_DIR, "03_grading_and_gpa.md")).read(), size=300)
    assert len(ch) >= 2 and all(c.strip() for c in ch)


def test_long_term_memory_persists(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "m.db"))
    assert memory.save("T1", "Interested in NLP")
    assert not memory.save("T1", "Interested in NLP")      # no duplicates
    assert memory.recall("T1") == ["Interested in NLP"]    # "new session" = fresh connection
    assert memory.recall("T2") == []


def test_five_documents():
    assert len([f for f in os.listdir(config.KNOWLEDGE_DIR) if f.endswith(".md")]) >= 5


def test_mcp_tools_registered_and_called():
    names = {t.name for t in agent.mcp_tools()}
    assert {"get_student_record", "check_prerequisites", "list_courses", "calculate_gpa_projection"} <= names
    r = json.loads(agent.run_async(agent._mcp_call("check_prerequisites", {"student_id": "S1002", "course_code": "AI301"})))
    assert r["eligible"] is False and set(r["missing_prerequisites"]) == {"MT201", "MT210"}
    ok = json.loads(agent.run_async(agent._mcp_call("check_prerequisites", {"student_id": "S1001", "course_code": "AI301"})))
    assert ok["eligible"] is True


def test_mcp_error_handling():
    assert agent.run_async(agent._mcp_call("get_student_record", {"student_id": "NOPE"})).startswith("ERROR")
