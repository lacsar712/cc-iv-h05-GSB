import math

FF_MIN = 0.72


def judge(fill_factor: float) -> tuple[str, str]:
    if fill_factor >= FF_MIN:
        return "合格", f"填充因子 {fill_factor} 不低于 {FF_MIN}"
    return "衰减", f"填充因子 {fill_factor} 低于 {FF_MIN}"


def is_pure_number(text: str) -> bool:
    """组串格出现纯数字，是组串号与填充因子两列被写反的特征。"""
    try:
        float(text)
    except (TypeError, ValueError):
        return False
    return True


def validate_scan(code: str, voc: float, isc: float, ff: float) -> None:
    """入库前校验：组串格只许放组串号，数字格只许放合法数字。不合格抛 ValueError。"""
    if not code:
        raise ValueError("组串编号不能为空")
    if is_pure_number(code):
        raise ValueError("组串编号不能是纯数字")
    if not (math.isfinite(voc) and math.isfinite(isc)):
        raise ValueError("电压电流必须是有限数字")
    if not math.isfinite(ff) or not 0 < ff <= 1:
        raise ValueError("填充因子必须是 0 到 1 之间的数字")
