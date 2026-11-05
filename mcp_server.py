"""MCP server (FastMCP, stdio) exposing the university's student-records & catalog tools.
Run standalone: python mcp_server.py   (normally launched by the agent's MCP client)."""
import json
from mcp.server.fastmcp import FastMCP
import config

mcp = FastMCP("university-records")
DATA = json.load(open(config.CATALOG_PATH, encoding="utf-8"))
GRADE_PTS = {"A": 4.0, "A-": 3.67, "B+": 3.33, "B": 3.0, "B-": 2.67, "C+": 2.33, "C": 2.0, "D": 1.0, "F": 0.0}


def _student(sid):
    return DATA["students"].get(sid.upper())


@mcp.tool()
def get_student_record(student_id: str) -> str:
    """Get a student's synthetic record: program, semester, completed courses with grades, CGPA, credits."""
    s = _student(student_id)
    if not s:
        return f"ERROR: unknown student '{student_id}'."
    pts = sum(GRADE_PTS[g] * DATA["courses"][c]["credits"] for c, g in s["completed"].items())
    cr = sum(DATA["courses"][c]["credits"] for c in s["completed"])
    return json.dumps({**s, "credits_completed": cr, "cgpa": round(pts / cr, 2) if cr else None})


@mcp.tool()
def check_prerequisites(student_id: str, course_code: str) -> str:
    """Check whether a student meets the prerequisites of a course. Returns eligibility and missing courses."""
    s, c = _student(student_id), DATA["courses"].get(course_code.upper())
    if not s: return f"ERROR: unknown student '{student_id}'."
    if not c: return f"ERROR: unknown course '{course_code}'."
    if course_code.upper() in s["completed"]:
        return json.dumps({"course": course_code, "eligible": False, "reason": "already completed"})
    missing = [p for p in c["prereqs"] if p not in s["completed"]]
    return json.dumps({"course": course_code.upper(), "title": c["title"], "eligible": not missing,
                       "missing_prerequisites": missing})


@mcp.tool()
def list_courses(program: str = "") -> str:
    """List catalog courses (code, title, credits, prerequisites, offered semester). Optional program filter e.g. BSAI."""
    rows = [{"code": k, **v} for k, v in DATA["courses"].items()
            if not program or program.upper() in v["programs"]]
    return json.dumps(rows)


@mcp.tool()
def calculate_gpa_projection(student_id: str, planned_grades: str) -> str:
    """Project CGPA. planned_grades is a JSON object like {"AIDE3313": "A", "CS201": "B+"}."""
    s = _student(student_id)
    if not s: return f"ERROR: unknown student '{student_id}'."
    try:
        plan = json.loads(planned_grades)
        pts = sum(GRADE_PTS[g] * DATA["courses"][c]["credits"] for c, g in {**s["completed"], **plan}.items())
        cr = sum(DATA["courses"][c]["credits"] for c in {**s["completed"], **plan})
    except (KeyError, ValueError) as e:
        return f"ERROR: invalid input ({e})."
    return json.dumps({"projected_cgpa": round(pts / cr, 2), "total_credits": cr})


if __name__ == "__main__":
    mcp.run(transport="stdio")
