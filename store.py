"""SQLite persistence. Every state change and its audit event commit together."""
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


class Conflict(Exception):
    pass


class Missing(Exception):
    pass


def now():
    return datetime.now(timezone.utc).isoformat()


class Store:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript("""
            CREATE TABLE IF NOT EXISTS tickets (
                id TEXT PRIMARY KEY, subject TEXT NOT NULL, body TEXT NOT NULL,
                status TEXT NOT NULL, revision INTEGER NOT NULL,
                analysis TEXT, reply TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT, ticket_id TEXT NOT NULL,
                action TEXT NOT NULL, details TEXT NOT NULL, created_at TEXT NOT NULL,
                FOREIGN KEY(ticket_id) REFERENCES tickets(id)
            );
            CREATE TABLE IF NOT EXISTS outbox (
                id TEXT PRIMARY KEY, ticket_id TEXT UNIQUE NOT NULL, reply TEXT NOT NULL,
                created_at TEXT NOT NULL, FOREIGN KEY(ticket_id) REFERENCES tickets(id)
            );
            """)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        try:
            with db:
                yield db
        finally:
            db.close()

    @staticmethod
    def decode(row):
        result = dict(row)
        result["analysis"] = json.loads(result["analysis"]) if result["analysis"] else None
        return result

    @staticmethod
    def event(db, ticket_id, action, details):
        db.execute("INSERT INTO events(ticket_id,action,details,created_at) VALUES (?,?,?,?)",
                   (ticket_id, action, json.dumps(details), now()))

    def create(self, subject, body):
        ticket_id, timestamp = str(uuid4()), now()
        with self.connect() as db:
            db.execute("INSERT INTO tickets VALUES (?,?,?,'new',1,NULL,NULL,?,?)",
                       (ticket_id, subject, body, timestamp, timestamp))
            self.event(db, ticket_id, "created", {"revision": 1})
        return self.get(ticket_id)

    def get(self, ticket_id):
        with self.connect() as db:
            row = db.execute("SELECT * FROM tickets WHERE id=?", (ticket_id,)).fetchone()
            if row is None:
                raise Missing()
            result = self.decode(row)
            result["events"] = [
                {**dict(e), "details": json.loads(e["details"])}
                for e in db.execute("SELECT * FROM events WHERE ticket_id=? ORDER BY id", (ticket_id,))
            ]
            outbox = db.execute("SELECT * FROM outbox WHERE ticket_id=?", (ticket_id,)).fetchone()
            result["outbox"] = dict(outbox) if outbox else None
            return result

    def list(self):
        with self.connect() as db:
            return [dict(r) for r in db.execute(
                "SELECT id,subject,status,revision,created_at FROM tickets ORDER BY created_at DESC LIMIT 200")]

    def transition(self, ticket_id, revision, allowed, status, action, *,
                   analysis=None, reply=None, note=None, deliver=False):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM tickets WHERE id=?", (ticket_id,)).fetchone()
            if row is None:
                raise Missing()
            if row["revision"] != revision or row["status"] not in allowed:
                raise Conflict("Ticket changed or this action is not allowed. Refresh the ticket.")
            next_reply = reply if reply is not None else row["reply"]
            if deliver:
                if not next_reply:
                    raise Conflict("An approved reply is required.")
                db.execute("INSERT INTO outbox VALUES (?,?,?,?)",
                           (str(uuid4()), ticket_id, next_reply, now()))
            db.execute("UPDATE tickets SET status=?,revision=revision+1,analysis=?,reply=?,updated_at=? WHERE id=?",
                       (status, json.dumps(analysis) if analysis is not None else row["analysis"],
                        next_reply, now(), ticket_id))
            self.event(db, ticket_id, action, {
                "from": row["status"], "to": status, "revision": revision + 1,
                **({"note": note} if note else {}),
                **({"approved_reply": next_reply} if action == "approved" else {}),
                **({"analysis": analysis} if analysis is not None else {}),
            })
        return self.get(ticket_id)
