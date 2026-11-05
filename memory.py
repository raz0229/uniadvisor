"""Long-term memory: persistent per-student facts in SQLite (survives new sessions)."""
import sqlite3, os, datetime
import config


def _conn():
    os.makedirs(os.path.dirname(config.DB_PATH), exist_ok=True)
    c = sqlite3.connect(config.DB_PATH)
    c.execute("""CREATE TABLE IF NOT EXISTS memories(
        id INTEGER PRIMARY KEY AUTOINCREMENT, student_id TEXT, fact TEXT, created TEXT)""")
    return c


def save(student_id, fact):
    with _conn() as c:
        if c.execute("SELECT 1 FROM memories WHERE student_id=? AND fact=?", (student_id, fact)).fetchone():
            return False
        c.execute("INSERT INTO memories(student_id,fact,created) VALUES(?,?,?)",
                  (student_id, fact, datetime.datetime.now().isoformat(timespec="seconds")))
    return True


def recall(student_id):
    with _conn() as c:
        return [r[0] for r in c.execute(
            "SELECT fact FROM memories WHERE student_id=? ORDER BY id", (student_id,))]


def clear(student_id):
    with _conn() as c:
        c.execute("DELETE FROM memories WHERE student_id=?", (student_id,))
