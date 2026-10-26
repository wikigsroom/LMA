"""Execute the SQL extracted from production Chats.java on a real host SQLite database.

This verifies schema/query ordering and durable bytes, not Android SQLiteOpenHelper.
"""
import json
from pathlib import Path
import re
import sqlite3
from evidence import fingerprint, current

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "build/sqlite-tests"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "results.json").unlink(missing_ok=True)
    inputs = fingerprint("app/src/main/java/com/lma/app/Chats.java", "tools/test_sqlite.py")
    source = (ROOT / "app/src/main/java/com/lma/app/Chats.java").read_text(encoding="utf-8")
    schema = re.findall(r'db\.execSQL\("([^"]+)"\)', source)
    queries = re.findall(r'rawQuery\("([^"]+)"', source)
    assert len(schema) == 3 and len(queries) == 4
    file = OUT / "host.sqlite"
    file.unlink(missing_ok=True)
    checks = []
    with sqlite3.connect(file) as db:
        for sql in schema: db.execute(sql)
        checks.append("Production schema and index compile in real SQLite")
        db.execute("INSERT INTO sessions VALUES(?,?,?,?)", ("normal", "Test", "m01", 1))
        hostile = "x' OR 1=1--"
        db.execute("INSERT INTO sessions VALUES(?,?,?,?)", (hostile, "Other", "m01", 2))
        for i in range(120):
            db.execute("INSERT INTO messages VALUES(?,?,?,?,?,?,?,?,?,?)", (str(i), "normal", "user" if i % 2 == 0 else "assistant", "text-" + str(i), "", "generating" if i == 119 else "done", "", 1, 0, 0))
        db.execute("INSERT INTO messages VALUES(?,?,?,?,?,?,?,?,?,?)", ("foreign", hostile, "user", "foreign", "", "done", "", 1, 0, 0))
        history = next(sql for sql in queries if "LIMIT 32" in sql)
        rows = db.execute(history, ("normal",)).fetchall()
        assert [r[1] for r in rows] == ["text-" + str(i) for i in range(88, 120)]
        checks.append("History selects newest 32 rows in chronological rowid order even with identical timestamps")
        snapshot = next(sql for sql in queries if "LIMIT 80" in sql)
        cursor = db.execute(snapshot, ("normal",)); names = [c[0] for c in cursor.description]; rows = cursor.fetchall()
        assert len(rows) == 80 and [r[names.index("content")] for r in rows] == ["text-" + str(i) for i in range(40, 120)]
        checks.append("Visible transcript selects newest 80 rows with stable order")
        assert len(db.execute(snapshot, (hostile,)).fetchall()) == 1
        checks.append("Bound session parameters isolate transcripts with SQL-like identifiers")
        db.execute("UPDATE messages SET status=?,error=? WHERE status=?", ("interrupted", "restored", "generating"))
    with sqlite3.connect(file) as db:
        assert db.execute("SELECT status FROM messages WHERE id='119'").fetchone()[0] == "interrupted"
        assert db.execute("SELECT COUNT(*) FROM messages WHERE status='done'").fetchone()[0] == 120
    checks.append("Committed messages and interrupted status survive closing and reopening SQLite")
    current(inputs)
    record = {"passed": len(checks), "checks": checks, "sqlite_version": sqlite3.sqlite_version, "android_framework_tested": False, "input_fingerprint": inputs}
    (OUT / "results.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"passed": len(checks), "sqlite": sqlite3.sqlite_version, "android_framework_tested": False}))


if __name__ == "__main__": main()
