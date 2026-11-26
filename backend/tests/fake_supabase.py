"""A tiny in-memory stand-in for the Supabase client, to test the repositories without a database.

It understands what the repositories use: select with explicit columns, eq, in_, is_, order,
limit, insert, update and delete. It records every select so a test can check which columns a
query asked for. REUTILIZABLE: the tests of any repository can use it.
"""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

SERIAL_TABLES = {
    "studies",
    "budgets",
    "authorizations",
    "coupons",
    "payments",
    "study_state_history",
}
# The timestamp column the database fills in by itself when it is not sent.
TIMESTAMP_DEFAULTS = {
    "study_state_history": "changed_at",
    "payments": "paid_at",
    "budgets": "issued_at",
}
START = datetime(2026, 11, 26, 10, 0, tzinfo=UTC)


class FakeQuery:
    def __init__(self, db: "FakeSupabase", name: str):
        self.db, self.name = db, name
        self.mode = "select"
        self.columns: list[str] = []
        self.payload = None
        self.filters = []
        self.orders: list[tuple[str, bool]] = []
        self.max_rows: int | None = None

    def select(self, columns: str = "*"):
        self.mode = "select"
        self.columns = [c.strip() for c in columns.split(",")]
        self.db.selects.append((self.name, columns))
        return self

    def insert(self, payload):
        self.mode, self.payload = "insert", payload
        return self

    def update(self, payload):
        self.mode, self.payload = "update", payload
        return self

    def delete(self):
        self.mode = "delete"
        return self

    def eq(self, column, value):
        self.filters.append(lambda r: r.get(column) == value)
        return self

    def in_(self, column, values):
        self.filters.append(lambda r: r.get(column) in values)
        return self

    def is_(self, column, value):
        assert value == "null"
        self.filters.append(lambda r: r.get(column) is None)
        return self

    def order(self, column, desc=False):
        self.orders.append((column, desc))
        return self

    def limit(self, count):
        self.max_rows = count
        return self

    def execute(self):
        rows = self.db.tables.setdefault(self.name, [])
        if self.mode == "insert":
            items = self.payload if isinstance(self.payload, list) else [self.payload]
            created = [self.db.complete(self.name, dict(item)) for item in items]
            rows.extend(created)
            return SimpleNamespace(data=[dict(r) for r in created])
        matching = [r for r in rows if all(f(r) for f in self.filters)]
        if self.mode == "update":
            for row in matching:
                row.update(self.payload)
            return SimpleNamespace(data=[dict(r) for r in matching])
        if self.mode == "delete":
            for row in matching:
                rows.remove(row)
            return SimpleNamespace(data=[dict(r) for r in matching])
        for column, desc in reversed(self.orders):
            matching.sort(key=lambda r, c=column: (r.get(c) is None, r.get(c)), reverse=desc)
        if self.max_rows is not None:
            matching = matching[: self.max_rows]
        if self.columns == ["*"]:
            return SimpleNamespace(data=[dict(r) for r in matching])
        return SimpleNamespace(data=[{c: r.get(c) for c in self.columns} for r in matching])


class FakeSupabase:
    def __init__(self, **tables: list[dict]):
        self.selects: list[tuple[str, str]] = []
        self._ticks = 0
        self._serial: dict[str, int] = {}
        self.tables = {}
        for name, rows in tables.items():
            self.tables[name] = []
            for row in rows:
                self.tables[name].append(self.complete(name, dict(row)))

    def table(self, name: str) -> FakeQuery:
        return FakeQuery(self, name)

    def now(self) -> str:
        self._ticks += 1
        return (START + timedelta(seconds=self._ticks)).isoformat()

    def complete(self, name: str, row: dict) -> dict:
        """What the database adds to a new row: the serial id and the default timestamps."""
        if name in SERIAL_TABLES and "id" not in row:
            existing = [r["id"] for r in self.tables.get(name, [])]
            self._serial[name] = max(self._serial.get(name, 0), *existing, 0) + 1
            row["id"] = self._serial[name]
        row.setdefault("created_at", self.now())
        if name in TIMESTAMP_DEFAULTS:
            row.setdefault(TIMESTAMP_DEFAULTS[name], self.now())
        return row

    def rows(self, name: str) -> list[dict]:
        return self.tables.setdefault(name, [])

    def columns_requested(self, table: str) -> set[str]:
        """Every column any select on that table asked for."""
        return {c.strip() for name, cols in self.selects if name == table for c in cols.split(",")}
