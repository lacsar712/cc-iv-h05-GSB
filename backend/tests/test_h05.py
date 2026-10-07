"""H05 回归：组串格只放组串号、数字格只放数字，入库/首页/排队三处都不得串列。

用内存假连接顶替 db.connect，因此不依赖真实 PostgreSQL。
"""
import importlib
import re
from datetime import datetime, timezone

import pytest

_NUMERIC_RE = re.compile(r"^[+-]?([0-9]+\.?[0-9]*|\.[0-9]+)([eE][+-]?[0-9]+)?$")


def _is_swapped(code, ff):
    return bool(_NUMERIC_RE.match(str(code).strip())) or ff <= 0 or ff > 1


class Result:
    def __init__(self, rows, rowcount=0):
        self._rows = rows
        self.rowcount = rowcount

    def fetchone(self):
        return self._rows[0] if self._rows else None

    def fetchall(self):
        return self._rows


class FakeConn:
    def __init__(self):
        self.rows = []
        self._next_id = 1

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def commit(self):
        pass

    def execute(self, sql, params=None):
        s = sql.strip()
        if s.startswith(("CREATE", "DROP")):
            return Result([])
        if s.startswith("SELECT COUNT"):
            return Result([{"n": len(self.rows)}])
        if s.startswith("DELETE"):  # CLEAN_SWAPPED
            kept = [r for r in self.rows if not _is_swapped(r["string_code"], r["fill_factor"])]
            removed = len(self.rows) - len(kept)
            self.rows = kept
            return Result([], rowcount=removed)
        if s.startswith("INSERT"):
            params = params or ()
            now = datetime.now(timezone.utc)
            if len(params) == 8:  # seed：code,voc,isc,ff,verdict,reason,now,now
                code, voc, isc, ff, verdict, reason, created_at, processed_at = params
                row = dict(id=self._next_id, string_code=code, voc_v=voc, isc_a=isc,
                           fill_factor=ff, status="done", verdict=verdict, reason=reason,
                           created_by="scanner", created_at=created_at,
                           processed_at=processed_at)
            else:  # 提交：code,voc,isc,ff,user,now
                code, voc, isc, ff, username, created_at = params
                row = dict(id=self._next_id, string_code=code, voc_v=voc, isc_a=isc,
                           fill_factor=ff, status="pending", verdict=None, reason=None,
                           created_by=username, created_at=created_at, processed_at=None)
            self._next_id += 1
            self.rows.append(row)
            return Result([row])
        if s.startswith("SELECT id, string_code"):
            return Result(list(reversed(self.rows)))
        raise AssertionError(f"未模拟的 SQL: {s[:40]}")


@pytest.fixture
def api_client(monkeypatch):
    import db
    fake = FakeConn()
    monkeypatch.setattr(db, "connect", lambda: fake)
    import api
    importlib.reload(api)
    from litestar.testing import TestClient
    with TestClient(app=api.app) as client:
        yield client, fake


def _token(client, username, password):
    res = client.post("/api/auth/login", json={"username": username, "password": password})
    assert res.status_code in (200, 201)
    return res.json()["access_token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_seed_two_strings_not_swapped(api_client):
    """甲串 0.78 合格、乙串 0.61 衰减：编号与 FF 各就各位，结论不反。"""
    client, fake = api_client
    token = _token(client, "scanner", "scan123456")
    rows = client.get("/api/logs", headers=_auth(token)).json()
    assert len(rows) == 2
    first, second = rows  # id DESC
    assert first["string_code"] == "阵列B-串11"
    assert first["fill_factor"] == 0.61
    assert first["verdict"] == "衰减"
    assert second["string_code"] == "阵列A-串03"
    assert second["fill_factor"] == 0.78
    assert second["verdict"] == "合格"
    # 没有任何残片：组串格不是数字，FF 格不是编号抠出来的 3.0/11.0
    assert all(not _NUMERIC_RE.match(str(r["string_code"])) for r in rows)
    assert {r["fill_factor"] for r in rows} == {0.78, 0.61}


def test_submit_does_not_swap_cells(api_client):
    client, _ = api_client
    token = _token(client, "scanner", "scan123456")
    res = client.post("/api/logs", headers=_auth(token), json={
        "string_code": "阵列C-串05", "voc_v": 40.1, "isc_a": 8.9, "fill_factor": 0.77,
    })
    assert res.status_code == 201, res.text
    saved = res.json()
    assert saved["string_code"] == "阵列C-串05"
    assert saved["fill_factor"] == 0.77

    rows = client.get("/api/logs", headers=_auth(token)).json()
    mine = next(r for r in rows if r["string_code"] == "阵列C-串05")
    assert mine["fill_factor"] == 0.77  # 首页列表两列也不互换


def test_string_cell_rejects_number(api_client):
    """组串格只许放组串号：0.78、0.61 这种纯数字不得进组串格。"""
    client, fake = api_client
    token = _token(client, "scanner", "scan123456")
    for bad in ("0.78", "0.61", "3", ".5"):
        res = client.post("/api/logs", headers=_auth(token), json={
            "string_code": bad, "voc_v": 40.0, "isc_a": 9.0, "fill_factor": 0.75,
        })
        assert res.status_code == 400, bad
    # 被拒的一条都不许落库
    assert all(r["string_code"] not in ("0.78", "0.61", "3", ".5") for r in fake.rows)


def test_numeric_cells_reject_non_number_and_range(api_client):
    client, _ = api_client
    token = _token(client, "scanner", "scan123456")
    base = {"string_code": "阵列C-串05", "voc_v": 40.0, "isc_a": 9.0, "fill_factor": 0.75}
    for patch in (
        {"fill_factor": "高"},
        {"voc_v": "NaN-string"},
        {"fill_factor": 1.5},
        {"fill_factor": 0},
    ):
        payload = dict(base, **patch)
        res = client.post("/api/logs", headers=_auth(token), json=payload)
        assert res.status_code == 400, patch


def test_watcher_remains_read_only(api_client):
    """观察员继续只读：能看列表，不能提交。"""
    client, _ = api_client
    token = _token(client, "watcher", "watch123456")
    assert client.get("/api/logs", headers=_auth(token)).status_code == 200
    res = client.post("/api/logs", headers=_auth(token), json={
        "string_code": "阵列C-串05", "voc_v": 40.0, "isc_a": 9.0, "fill_factor": 0.75,
    })
    assert res.status_code == 403


def test_swapped_fragments_would_be_cleaned():
    """清洗判定：组串格为纯数字或 FF 越界即残片；0.78/0.61 正规行保留。"""
    assert _is_swapped("0.78", 3.0) is True
    assert _is_swapped("0.61", 11.0) is True
    assert _is_swapped("阵列A-串03", 0.78) is False
    assert _is_swapped("阵列B-串11", 0.61) is False
