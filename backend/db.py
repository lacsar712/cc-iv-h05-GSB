import os
import psycopg
from psycopg.rows import dict_row

DSN = os.environ.get("DATABASE_URL", "postgresql://app:app@localhost:54402/pvivscan")


def connect():
    return psycopg.connect(DSN, row_factory=dict_row)


# 纯数字形态（含小数/科学计数法），与 Python float() 接受的写法对齐
_NUMERIC_RE = r"^[+-]?([0-9]+\.?[0-9]*|\.[0-9]+)([eE][+-]?[0-9]+)?$"

# 删除“写到一半列义反了”的残片：
# 组串格被写成纯数字，或数字格（填充因子）越界（不在 0~1）。
CLEAN_SWAPPED = f"""
DELETE FROM iv_scans
WHERE btrim(string_code) ~ '{_NUMERIC_RE}'
   OR fill_factor <= 0
   OR fill_factor > 1;
"""


def clean_swapped(conn) -> int:
    """清掉组串格/填充因子格串列的残行，返回删除条数。"""
    return conn.execute(CLEAN_SWAPPED).rowcount


SCHEMA = """
CREATE TABLE IF NOT EXISTS iv_scans (
    id serial PRIMARY KEY,
    string_code text NOT NULL,
    voc_v double precision NOT NULL,
    isc_a double precision NOT NULL,
    fill_factor double precision NOT NULL,
    status text NOT NULL DEFAULT 'pending',
    verdict text,
    reason text,
    created_by text NOT NULL,
    created_at timestamptz NOT NULL,
    processed_at timestamptz
);
CREATE OR REPLACE FUNCTION notify_iv_scan() RETURNS trigger AS $$
BEGIN
  PERFORM pg_notify('iv_scan_new', NEW.id::text);
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;
DROP TRIGGER IF EXISTS trg_iv_scan_notify ON iv_scans;
CREATE TRIGGER trg_iv_scan_notify
AFTER INSERT ON iv_scans
FOR EACH ROW EXECUTE FUNCTION notify_iv_scan();
"""
