import pathlib
import re

import pytest

from rules import is_pure_number, judge, validate_scan


def test_validate_accepts_real_scans():
    # 甲串 0.78、乙串 0.61：组串格放组串号，数字格放数字
    validate_scan("阵列A-串03", 41.2, 9.1, 0.78)
    validate_scan("阵列B-串11", 38.0, 8.4, 0.61)


def test_validate_rejects_swapped_cells():
    # 组串格进了填充因子、数字格进了组串号残片：一律拒绝入库
    with pytest.raises(ValueError):
        validate_scan("0.78", 41.2, 9.1, 3.0)
    with pytest.raises(ValueError):
        validate_scan("0.61", 38.0, 8.4, 11.0)


def test_validate_rejects_bad_fill_factor():
    for bad in (0, -0.1, 1.2, float("nan"), float("inf")):
        with pytest.raises(ValueError):
            validate_scan("阵列A-串03", 41.2, 9.1, bad)


def test_validate_rejects_empty_or_numeric_code():
    for bad in ("", "0.78", "123"):
        with pytest.raises(ValueError):
            validate_scan(bad, 41.2, 9.1, 0.78)


def test_judge_threshold():
    assert judge(0.78)[0] == "合格"
    assert judge(0.61)[0] == "衰减"


def test_is_pure_number():
    assert is_pure_number("0.78")
    assert not is_pure_number("阵列A-串03")


def test_no_swap_trap_left_in_source():
    """首页、详情、排队三处的列义互换陷阱不得在源码里残留。"""
    root = pathlib.Path(__file__).resolve().parent.parent
    for path in root.glob("*.py"):
        assert "h05_" not in path.name, path
        src = path.read_text(encoding="utf-8")
        assert not re.search(
            r"code_ff_swap|h05_extra_trap|h05_list_trap|h05_render_trap", src
        ), path
