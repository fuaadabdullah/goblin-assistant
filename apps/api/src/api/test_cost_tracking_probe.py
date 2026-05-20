import os
import sqlite3
import sys
from types import SimpleNamespace


def test_cost_tracking_unknown(client, monkeypatch):
    # Ensure no env vars
    monkeypatch.delenv("COST_TRACKING_ENABLED", raising=False)
    monkeypatch.delenv("COST_DB_URL", raising=False)

    resp = client.get("/health/cost-tracking")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "unknown"


def test_cost_tracking_sqlite(client, tmp_path, monkeypatch):
    db_file = tmp_path / "costs.db"
    conn = sqlite3.connect(str(db_file))
    cur = conn.cursor()
    cur.execute("CREATE TABLE costs (amount REAL);")
    cur.execute("INSERT INTO costs (amount) VALUES (?)", (12.5,))
    conn.commit()
    conn.close()

    # Format COST_DB_URL so our probe resolves to absolute path
    monkeypatch.setenv("COST_DB_URL", f"sqlite://{str(db_file)}")

    resp = client.get("/health/cost-tracking")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert float(data["total_cost"]) == 12.5


def test_cost_tracking_postgres_success(client, monkeypatch):
    # Simulate psycopg with a fake connect that returns the expected row
    class FakeCursor:
        def execute(self, q):
            pass

        def fetchone(self):
            return (99.99,)

        def close(self):
            pass

    class FakeConn:
        def cursor(self):
            return FakeCursor()

        def close(self):
            pass

    class FakePsycopgModule(SimpleNamespace):
        @staticmethod
        def connect(dsn, connect_timeout=2):
            return FakeConn()

    monkeypatch.setitem(sys.modules, "psycopg", FakePsycopgModule())
    monkeypatch.setenv("COST_DB_URL", "postgresql://user:pass@localhost:5432/db")

    resp = client.get("/health/cost-tracking")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert float(data["total_cost"]) == 99.99
